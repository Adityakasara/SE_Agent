from functools import lru_cache
import os
from pathlib import Path
from typing import Literal, Optional
from pydantic import Field
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:  # Fallback if pydantic_settings not installed yet
    from pydantic import BaseModel as BaseSettings
    SettingsConfigDict = dict


class Settings(BaseSettings):
    """Application Settings and Environment Configuration."""
    
    # LLM Settings
    LLM_PROVIDER: Literal["openai", "anthropic", "google", "ollama", "mock"] = Field(
        default="openai", description="Default LLM provider"
    )
    LLM_MODEL: str = Field(default="gpt-4o", description="Model name to use")
    LLM_TEMPERATURE: float = Field(default=0.0, description="Model sampling temperature")
    
    # API Keys
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None)
    GOOGLE_API_KEY: Optional[str] = Field(default=None)
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")
    
    # Paths & Workspaces
    PROJECT_ROOT: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent.parent)
    WORKSPACE_ROOT: str = Field(default="./workspace")
    REPOSITORIES_DIR: str = Field(default="./workspace/repositories")
    SANDBOX_DIR: str = Field(default="./workspace/sandboxes")
    KNOWLEDGE_BASE_DIR: str = Field(default="./knowledge_base")
    
    # LangSmith
    LANGCHAIN_TRACING_V2: bool = Field(default=False)
    LANGCHAIN_ENDPOINT: str = Field(default="https://api.smith.langchain.com")
    LANGCHAIN_API_KEY: Optional[str] = Field(default=None)
    LANGCHAIN_PROJECT: str = Field(default="ai-software-engineering-agent")
    
    # Security & Tool Limits
    COMMAND_TIMEOUT_SECONDS: int = Field(default=60)
    MAX_SEARCH_RESULTS: int = Field(default=50)
    MAX_FILE_READ_LINES: int = Field(default=1000)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    ) if "SettingsConfigDict" in globals() and isinstance(SettingsConfigDict, type) else {}

    def get_repo_path(self, repo_name_or_path: str) -> Path:
        """Resolve a repository path safely."""
        candidate = Path(repo_name_or_path)
        if candidate.is_absolute() and candidate.exists():
            return candidate
        # Try relative to REPOSITORIES_DIR
        repo_dir = Path(self.REPOSITORIES_DIR)
        if not repo_dir.is_absolute():
            repo_dir = self.PROJECT_ROOT / repo_dir
        return (repo_dir / repo_name_or_path).resolve()

    def get_sandbox_path(self, task_id: str) -> Path:
        """Resolve an isolated sandbox workspace path."""
        sandbox_dir = Path(self.SANDBOX_DIR)
        if not sandbox_dir.is_absolute():
            sandbox_dir = self.PROJECT_ROOT / sandbox_dir
        sandbox_dir.mkdir(parents=True, exist_ok=True)
        return (sandbox_dir / task_id).resolve()


@lru_cache()
def get_settings() -> Settings:
    return Settings()
