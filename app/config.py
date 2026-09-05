"""Application configuration loaded from environment variables / .env file."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = REPO_ROOT / "models"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    model_path: Path = MODELS_DIR / "CS_model.keras"
    tokenizer_path: Path = MODELS_DIR / "tokenizer.pkl"
    max_len: int = 50
    enable_keyword_filter: bool = False
    cs_keywords: list[str] = [
        "cyber", "hack", "breach", "malware", "phishing", "ransomware",
        "infrastructure", "ddos", "security", "data", "attack", "vulnerability",
        "privacy", "leak", "spyware", "exploit", "threat", "database",
    ]
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    page_load_timeout: int = 30
    page_wait_timeout: int = 10
    redis_url: str = "redis://localhost:6379/0"
    redis_result_url: str = "redis://localhost:6379/1"
    ws_idle_timeout: int = 30
    cache_enabled: bool = True
    cache_ttl_seconds: int = 420
    redis_health_check_interval: int = 25
    redis_socket_timeout: int = 10
    redis_socket_connect_timeout: int = 5
    redis_socket_keepalive: bool = True


settings = Settings()
