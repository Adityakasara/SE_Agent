from pathlib import Path
from app.tools.security import SecurityGuard


def test_validate_path_allowed(demo_repo_path):
    res = SecurityGuard.validate_path(demo_repo_path, "app/main.py")
    assert res.is_safe is True
    assert res.sanitized_path is not None
    assert "app/main.py" in res.sanitized_path


def test_validate_path_traversal_blocked(demo_repo_path):
    # Attempting to escape the root
    res = SecurityGuard.validate_path(demo_repo_path, "../../etc/passwd")
    assert res.is_safe is False
    assert "escapes root" in res.reason.lower() or "traversal" in res.reason.lower()


def test_validate_sensitive_file_blocked(demo_repo_path):
    # Attempting to access .env or .git credentials
    res = SecurityGuard.validate_path(demo_repo_path, ".env")
    assert res.is_safe is False
    assert "sensitive" in res.reason.lower()
