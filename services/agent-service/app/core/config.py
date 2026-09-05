"""Agent service configuration."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Application Settings
    APP_NAME: str = "AI Financial Advisor — Agent Service"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    
    # ─── LLM Configuration ──────────────────────────────────────────────────
    
    # Groq API (for complex tasks like analysis and planning)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-70b-versatile"
    
    
    # Ollama (for simple tasks, running locally in Docker)
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"
    

    # ─── Internal Microservices ─────────────────────────────────────────────
    # Used by tools to fetch data from other services
    RAG_SERVICE_URL: str = "http://rag-service:8003"
    MARKET_DATA_SERVICE_URL: str = "http://market-data-service:8004"
    AUTH_SERVICE_URL: str = "http://auth-service:8001"


    # ─── Memory: Redis (Short-term context) ─────────────────────────────────
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "redis_secret"
    REDIS_DB: int = 2  # DB 2 for agent short-term memory (DB 0 is Auth, DB 1 is Market Data cache)

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


    # ─── Memory: ChromaDB (Long-term semantic memory) ───────────────────────
    CHROMA_HOST: str = "chromadb"
    CHROMA_PORT: int = 8000
    
    @property
    def CHROMA_URL(self) -> str:
        return f"http://{self.CHROMA_HOST}:{self.CHROMA_PORT}"



@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()