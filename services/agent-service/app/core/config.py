"""Agent service configuration."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

import os
from dotenv import load_dotenv

load_dotenv()   

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Application Settings
    APP_NAME: str = "AI Financial Advisor — Agent Service"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    
    # ─── LLM Configuration ──────────────────────────────────────────────────
    
    # Groq API (for complex tasks like analysis and planning)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL")
    
    
    # Ollama (for simple tasks, running locally in Docker)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL")
    

    # ─── Internal Microservices ─────────────────────────────────────────────
    # Used by tools to fetch data from other services
    RAG_SERVICE_URL: str = os.getenv("RAG_SERVICE_URL")
    MARKET_DATA_SERVICE_URL: str = os.getenv("MARKET_DATA_SERVICE_URL")
    AUTH_SERVICE_URL: str = os.getenv("AUTH_SERVICE_URL")


    # ─── Memory: Redis (Short-term context) ─────────────────────────────────
    REDIS_HOST: str = os.getenv("REDIS_HOST")
    REDIS_PORT: int = os.getenv("REDIS_PORT")
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD")
    REDIS_DB: int = os.getenv("REDIS_DB")  # DB 2 for agent short-term memory (DB 0 is Auth, DB 1 is Market Data cache)

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


    # ─── Memory: ChromaDB (Long-term semantic memory) ───────────────────────
    CHROMA_HOST: str = os.getenv("CHROMA_HOST")
    CHROMA_PORT: int = os.getenv("CHROMA_PORT")
    
    @property
    def CHROMA_URL(self) -> str:
        return f"http://{self.CHROMA_HOST}:{self.CHROMA_PORT}"



@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()