"""
Smart LLM routing for the agent service.
Strategy:
  Step 1 → Ollama classifies the query intent (cheap, fast, local)
  Step 2 → Route based on intent:
              SIMPLE  → Ollama handles the full response (free)
              COMPLEX → Groq handles the full response (powerful)
"""
import structlog
from langchain_community.chat_models import ChatOllama
from langchain_groq import ChatGroq
from langchain_core.language_models.chat_models import BaseChatModel

from app.core.config import settings
from app.agents.financial_advisor.prompts import ROUTING_PROMPT_TEMPLATE, router_output_parser


logger = structlog.get_logger(__name__)

# ─── Initialize LLMs ────────────────────────────────────────────────────────
# 1. Local LLM (Ollama) - Fast, free, runs on your machine
# Good for: greetings, simple calculations, basic entity extraction

try:
    logger.info("Initializing local LLM (Ollama)")
    local_llm = ChatOllama(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_MODEL,
        temperature=0.1,  # Low temperature for more deterministic outputs
    )

except Exception as e:
    logger.warning(f"Failed to initialize local LLM (Ollama): {e}")
    local_llm = None


# 2. Cloud LLM (Groq) - Extremely powerful, fast API
# Good for: complex financial reasoning, tool calling, multi-step plans

try:
    logger.info("Initializing cloud LLM (Groq)")
    if settings.GROQ_API_KEY:
        cloud_llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model_name=settings.GROQ_MODEL,
            temperature=0.1,
        )

    else:
        logger.warning("GROQ_API_KEY not set, skipping Groq initialization")
        cloud_llm = None

except Exception as e:
    logger.warning(f"Failed to initialize cloud LLM (Groq): {e}")
    cloud_llm = None




# ─── Intent Classifier ──────────────────────────────────────────────────────
async def classify_intent(query: str) -> str:
    """
    Uses the local Ollama model to classify the user's query intent.
    Sends a lightweight prompt to Ollama — very fast since the
    classification prompt is simple and response is a single word.
    Args:
        query: The raw user query
    Returns:
        "SIMPLE" or "COMPLEX"
    """
    # If Ollama is not available, default to COMPLEX (use Groq)
    if not local_llm:
        logger.warning("Ollama unavailable for classification. Defaulting to COMPLEX.")
        return "COMPLEX"
    try:
        chain = ROUTING_PROMPT_TEMPLATE | local_llm | router_output_parser
        response = await chain.ainvoke({"user_message": query})
        
        # Extract intent safely whether response is a dict or LangChain object
        content = response.get("intent", "") if isinstance(response, dict) else getattr(response, "content", str(response))
        intent = "SIMPLE" if isinstance(content, str) and "SIMPLE" in content.upper() else "COMPLEX"
        
        logger.info("Intent classified", query=query[:60], intent=intent)
        return intent
    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        return "COMPLEX"
    
# ─── LLM Router ─────────────────────────────────────────────────────────────
async def get_optimal_llm(query: str, force_cloud: bool = False) -> BaseChatModel:
    """
    Routes the query to the best LLM based on Ollama's intent classification.
    Flow:
      1. If force_cloud=True → always return Groq (for tool calling)
      2. Ask Ollama to classify the intent (SIMPLE or COMPLEX)
      3. SIMPLE  → return Ollama
      4. COMPLEX → return Groq
    Args:
        query:       Raw user query string
        force_cloud: Force Groq regardless of intent (use when tools are needed)
    Returns:
        A LangChain BaseChatModel (either local_llm or cloud_llm)
    Raises:
        RuntimeError: If neither LLM is initialized
    """
    if not local_llm and not cloud_llm:
        raise RuntimeError(
            "No LLMs available! "
            "Check Ollama container is running and GROQ_API_KEY is set."
        )
    # If one LLM is missing, fallback to the available one
    if not local_llm or not cloud_llm:
        logger.warning("One LLM is unavailable. Using fallback for all queries.")
        return local_llm or cloud_llm
        
    # Tool-calling always needs the more capable cloud model
    if force_cloud:
        logger.debug("Forced cloud LLM (tool calling required)")
        return cloud_llm
    
    # Let Ollama decide the intent
    intent = await classify_intent(query)

    logger.info(f"Routing → {'LOCAL (Ollama)' if intent == 'SIMPLE' else 'CLOUD (Groq)'}", query=query[:60])
    return local_llm if intent == "SIMPLE" else cloud_llm