import sys
from pathlib import Path
import pytest

# Ensure backend app is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

@pytest.fixture
def demo_repo_path():
    """Path to the fixture demo FastAPI repository."""
    return Path(__file__).resolve().parent.parent.parent / "workspace" / "repositories" / "demo_fastapi_app"

@pytest.fixture
def temp_sandbox_path(tmp_path):
    """Temporary isolated directory for sandbox tests."""
    sandbox = tmp_path / "sandbox_test"
    sandbox.mkdir()
    return sandbox
