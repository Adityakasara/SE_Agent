from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FileInfo(BaseModel):
    """Metadata about a single file in the repository."""
    path: str = Field(description="Relative path of the file from repo root")
    size_bytes: int = Field(description="Size of the file in bytes")
    is_dir: bool = Field(default=False, description="Whether this node is a directory")
    extension: str = Field(default="", description="File extension")
    line_count: Optional[int] = Field(default=None, description="Number of lines in the file")


class RepositoryMetadata(BaseModel):
    """Structured information summarizing the repository structure and technology."""
    repo_name: str
    repo_path: str
    primary_language: str
    languages: Dict[str, int] = Field(default_factory=dict, description="Language breakdown by file count")
    frameworks: List[str] = Field(default_factory=list, description="Detected frameworks or libraries")
    entry_points: List[str] = Field(default_factory=list, description="Potential entry points (main.py, app.py, etc.)")
    config_files: List[str] = Field(default_factory=list, description="Config files (pyproject.toml, requirements.txt, etc.)")
    test_framework: Optional[str] = Field(default=None, description="Detected test runner (e.g. pytest, unittest)")
    total_files: int = 0
    total_directories: int = 0
    readme_snippet: Optional[str] = None


class GitDiffResult(BaseModel):
    """Result of comparing working branch with baseline."""
    has_changes: bool
    files_changed: List[str] = Field(default_factory=list)
    diff_text: str = ""
    insertions: int = 0
    deletions: int = 0


class ToolResult(BaseModel):
    """Unified response format for all tool executions."""
    success: bool
    tool_name: str
    data: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class SecurityCheckResult(BaseModel):
    """Result of path or command safety inspection."""
    is_safe: bool
    reason: Optional[str] = None
    sanitized_path: Optional[str] = None


class LLMMessage(BaseModel):
    role: str
    content: str


class LLMResponse(BaseModel):
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
