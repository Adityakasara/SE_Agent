from app.tools.code_tools import CodeTools


def test_create_and_edit_file(temp_sandbox_path):
    # Create file
    create_res = CodeTools.create_file(
        temp_sandbox_path, "test_file.py", "def add(a, b):\n    return a + b\n"
    )
    assert create_res.success is True

    # Search pattern
    search_res = CodeTools.search_code_regex(temp_sandbox_path, "def add")
    assert search_res.success is True
    assert search_res.data["total_matches"] == 1
    assert search_res.data["matches"][0]["file"] == "test_file.py"

    # AST symbol extraction
    ast_res = CodeTools.extract_python_ast_symbols(temp_sandbox_path, "test_file.py")
    assert ast_res.success is True
    funcs = [f["name"] for f in ast_res.data["functions"]]
    assert "add" in funcs

    # Edit file
    edit_res = CodeTools.edit_file(
        temp_sandbox_path, "test_file.py", "def add(a, b, c=0):\n    return a + b + c\n"
    )
    assert edit_res.success is True


def test_ast_syntax_error(temp_sandbox_path):
    CodeTools.create_file(
        temp_sandbox_path, "broken.py", "def broken_syntax(:\n", overwrite=True
    )
    ast_res = CodeTools.extract_python_ast_symbols(temp_sandbox_path, "broken.py")
    assert ast_res.success is False
    assert "syntax error" in ast_res.error.lower()
