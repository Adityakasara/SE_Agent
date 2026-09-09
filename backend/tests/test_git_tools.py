from app.tools.git_tools import GitTools
from app.tools.code_tools import CodeTools


def test_create_isolated_sandbox_and_diff(demo_repo_path, temp_sandbox_path):
    # 1. Create sandbox
    sandbox_dest = temp_sandbox_path / "sandbox_demo"
    res = GitTools.create_isolated_sandbox(
        demo_repo_path, sandbox_dest, branch_name="fix/missing-email-check"
    )
    assert res.success is True
    assert res.data["branch"] == "fix/missing-email-check"

    # 2. Status initially clean
    status_res = GitTools.get_git_status(sandbox_dest)
    assert status_res.success is True
    assert status_res.data["is_dirty"] is False

    # 3. Modify a file in sandbox
    edit_res = CodeTools.create_file(
        sandbox_dest,
        "app/routes/users.py",
        "# Modified file content\nprint('patched')",
        overwrite=True,
    )
    assert edit_res.success is True

    # 4. Check git diff
    diff_res = GitTools.get_git_diff(sandbox_dest)
    assert diff_res.success is True
    assert diff_res.data["has_changes"] is True
    assert "app/routes/users.py" in diff_res.data["files_changed"]
    assert "patched" in diff_res.data["diff_text"]
