from app.tools.repository_tools import RepositoryTools


def test_list_files(demo_repo_path):
    res = RepositoryTools.list_files(demo_repo_path, recursive=True)
    assert res.success is True
    files = res.data
    assert len(files) > 0
    paths = [f["path"] for f in files]
    assert "app/main.py" in paths
    assert "app/routes/users.py" in paths
    assert "README.md" in paths


def test_read_file(demo_repo_path):
    res = RepositoryTools.read_file(demo_repo_path, "app/routes/users.py")
    assert res.success is True
    assert "fake_db" in res.data["content"]
    assert res.data["start_line"] == 1
    assert res.data["total_lines"] > 0


def test_read_file_nonexistent(demo_repo_path):
    res = RepositoryTools.read_file(demo_repo_path, "does_not_exist.py")
    assert res.success is False
    assert "not found" in res.error.lower()


def test_get_repository_structure(demo_repo_path):
    res = RepositoryTools.get_repository_structure(demo_repo_path)
    assert res.success is True
    assert "demo_fastapi_app" in res.data["tree_string"]
    assert "main.py" in res.data["tree_string"]


def test_detect_language(demo_repo_path):
    res = RepositoryTools.detect_language(demo_repo_path)
    assert res.success is True
    assert res.data["primary_language"] == "Python"


def test_detect_framework(demo_repo_path):
    res = RepositoryTools.detect_framework(demo_repo_path)
    assert res.success is True
    assert "FastAPI" in res.data["frameworks"]


def test_get_repository_metadata(demo_repo_path):
    meta = RepositoryTools.get_repository_metadata(demo_repo_path)
    assert meta.repo_name == "demo_fastapi_app"
    assert meta.primary_language == "Python"
    assert "FastAPI" in meta.frameworks
    assert any("main.py" in ep for ep in meta.entry_points)
    assert meta.total_files >= 5
