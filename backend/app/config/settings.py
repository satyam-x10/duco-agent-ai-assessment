from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    ENV: str = "development"
    PROJECT_NAME: str = "DuCO-Agent"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Security and Auth
    API_AUTH_KEY: str = "duco-agent-secure-key-2026"
    AUTH_ENABLED: bool = False  # Set to True for production authentication
    
    # Storage Configuration
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
    UPLOAD_DIR: str = "uploads"
    STORAGE_TYPE: str = "local"  # 'local' or 'gcs'
    
    # CORS Origins configuration, can be a list or a comma-separated string
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000"
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        return v


settings = Settings()
