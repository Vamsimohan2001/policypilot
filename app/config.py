from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Policy Bot"
    environment: str = "development"

    # --- security -------------------------------------------------
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    login_max_attempts: int = 5
    login_lockout_minutes: int = 15
    rate_limit_login_per_minute: int = 10
    rate_limit_chat_per_minute: int = 30

    # --- storage --------------------------------------------------
    database_url: str | None = None
    chroma_dir: Path | None = None
    policies_dir: Path | None = None
    collection_name: str = "policies"

    # --- llm / embeddings ----------------------------------------
    llm_enabled: bool = True
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_backend: str = "auto"  # auto | openai | local

    # --- retrieval (rag) ------------------------------------------
    rag_top_k: int = 6
    # chunks with cosine distance above this cutoff are treated as irrelevant,
    # so a question that the documents do not cover gets an out-of-scope reply
    rag_max_distance: float = 0.72

    # --- bootstrapping --------------------------------------------
    seed_on_startup: bool = True
    auto_ingest_on_startup: bool = True

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url and self.database_url.strip():
            return self.database_url.strip()
        return f"sqlite:///{(self.base_dir / 'data' / 'policybot.db').as_posix()}"

    @property
    def base_dir(self) -> Path:
        return BASE_DIR

    @property
    def chroma_path(self) -> Path:
        return self.chroma_dir or (BASE_DIR / "data" / "chroma")

    @property
    def policies_path(self) -> Path:
        return self.policies_dir or (BASE_DIR / "policies")

    @property
    def llm_active(self) -> bool:
        return self.llm_enabled and bool(self.openai_api_key.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
