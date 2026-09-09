import os
from pathlib import Path
from typing import List, Optional
from ..models.schemas import SecurityCheckResult

BLOCKED_PATTERNS = [
    ".git/config",
    ".git/credentials",
    ".ssh",
    ".env",
    "id_rsa",
    "credentials.json",
    "secrets.yaml",
    "secrets.json",
    "/etc/passwd",
    "/etc/shadow",
]

BLOCKED_DIRECTORIES = [
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    "venv",
    ".venv",
]


class SecurityGuard:
    """Enforces strict path isolation and restricts access to sensitive files."""

    @staticmethod
    def validate_path(base_dir: Path, target_path: str) -> SecurityCheckResult:
        """
        Ensures target_path resolves strictly within base_dir and does not access sensitive files.
        """
        try:
            base_dir_resolved = base_dir.resolve()
            
            # Normalize target path
            # Remove leading slashes if treated as relative
            clean_target = target_path.strip().lstrip("/")
            
            candidate_path = (base_dir / clean_target).resolve()
            
            # Check for path traversal (must be a descendant or base itself)
            try:
                candidate_path.relative_to(base_dir_resolved)
            except ValueError:
                return SecurityCheckResult(
                    is_safe=False,
                    reason=f"Path traversal blocked: target path '{target_path}' escapes root '{base_dir_resolved}'"
                )

            # Check for sensitive files
            rel_str = str(candidate_path.relative_to(base_dir_resolved))
            for blocked in BLOCKED_PATTERNS:
                if blocked in rel_str or rel_str.endswith(blocked):
                    return SecurityCheckResult(
                        is_safe=False,
                        reason=f"Access blocked to sensitive pattern: {blocked}"
                    )

            return SecurityCheckResult(
                is_safe=True,
                sanitized_path=str(candidate_path)
            )
        except Exception as e:
            return SecurityCheckResult(
                is_safe=False,
                reason=f"Security validation error: {str(e)}"
            )
