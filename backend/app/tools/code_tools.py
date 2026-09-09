import ast
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..models.schemas import ToolResult
from ..utils.logging import logger
from .security import SecurityGuard


class CodeTools:
    """Tools for safe file creation, editing, and code structural inspection."""

    @staticmethod
    def create_file(
        repo_path: Union[str, Path],
        relative_path: str,
        content: str,
        overwrite: bool = False,
    ) -> ToolResult:
        """Create a new file in the repository / sandbox."""
        start_time = time.time()
        base_dir = Path(repo_path).resolve()
        sec_check = SecurityGuard.validate_path(base_dir, relative_path)
        if not sec_check.is_safe:
            return ToolResult(
                success=False,
                tool_name="create_file",
                error=sec_check.reason,
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        target_file = Path(sec_check.sanitized_path)
        if target_file.exists() and not overwrite:
            return ToolResult(
                success=False,
                tool_name="create_file",
                error=f"File already exists: {relative_path}. Set overwrite=True if intended.",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        try:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(content, encoding="utf-8")
            return ToolResult(
                success=True,
                tool_name="create_file",
                data={
                    "file_path": relative_path,
                    "bytes_written": len(content.encode("utf-8")),
                    "lines": len(content.splitlines()),
                },
                execution_time_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name="create_file",
                error=f"Failed to create file: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

    @staticmethod
    def edit_file(
        repo_path: Union[str, Path],
        relative_path: str,
        new_content: str,
    ) -> ToolResult:
        """Edit/replace the full contents of an existing file."""
        start_time = time.time()
        base_dir = Path(repo_path).resolve()
        sec_check = SecurityGuard.validate_path(base_dir, relative_path)
        if not sec_check.is_safe:
            return ToolResult(
                success=False,
                tool_name="edit_file",
                error=sec_check.reason,
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        target_file = Path(sec_check.sanitized_path)
        if not target_file.exists():
            return ToolResult(
                success=False,
                tool_name="edit_file",
                error=f"File not found to edit: {relative_path}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        try:
            target_file.write_text(new_content, encoding="utf-8")
            return ToolResult(
                success=True,
                tool_name="edit_file",
                data={
                    "file_path": relative_path,
                    "bytes_written": len(new_content.encode("utf-8")),
                    "lines": len(new_content.splitlines()),
                },
                execution_time_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name="edit_file",
                error=f"Failed to edit file: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

    @staticmethod
    def search_code_regex(
        repo_path: Union[str, Path],
        pattern: str,
        file_extension: Optional[str] = None,
        max_matches: int = 50,
    ) -> ToolResult:
        """Search code files using regular expressions / text matches."""
        start_time = time.time()
        base_dir = Path(repo_path).resolve()
        matches = []
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return ToolResult(
                success=False,
                tool_name="search_code_regex",
                error=f"Invalid regex pattern: {e}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        for path in base_dir.rglob("*"):
            if not path.is_file() or path.stat().st_size > 500_000:
                continue
            if file_extension and path.suffix.lower() != file_extension.lower():
                continue
            
            # Security check
            rel_str = str(path.relative_to(base_dir))
            sec_check = SecurityGuard.validate_path(base_dir, rel_str)
            if not sec_check.is_safe:
                continue

            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_idx, line in enumerate(f, 1):
                        if regex.search(line):
                            matches.append({
                                "file": rel_str,
                                "line_number": line_idx,
                                "line_content": line.rstrip(),
                            })
                            if len(matches) >= max_matches:
                                break
            except Exception:
                pass
            if len(matches) >= max_matches:
                break

        return ToolResult(
            success=True,
            tool_name="search_code_regex",
            data={
                "matches": matches,
                "total_matches": len(matches),
                "capped": len(matches) >= max_matches,
            },
            execution_time_ms=(time.time() - start_time) * 1000,
        )

    @staticmethod
    def extract_python_ast_symbols(
        repo_path: Union[str, Path],
        relative_path: str,
    ) -> ToolResult:
        """Parse a Python file and extract functions, classes, and imports."""
        start_time = time.time()
        base_dir = Path(repo_path).resolve()
        sec_check = SecurityGuard.validate_path(base_dir, relative_path)
        if not sec_check.is_safe:
            return ToolResult(
                success=False,
                tool_name="extract_python_ast_symbols",
                error=sec_check.reason,
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        target_file = Path(sec_check.sanitized_path)
        if not target_file.exists() or not target_file.is_file():
            return ToolResult(
                success=False,
                tool_name="extract_python_ast_symbols",
                error=f"File not found: {relative_path}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        try:
            code = target_file.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(code)

            functions = []
            classes = []
            imports = []

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    functions.append({
                        "name": node.name,
                        "line": node.lineno,
                        "args": [a.arg for a in node.args.args],
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                    })
                elif isinstance(node, ast.ClassDef):
                    classes.append({
                        "name": node.name,
                        "line": node.lineno,
                        "bases": [getattr(b, "id", getattr(b, "attr", str(b))) for b in node.bases],
                    })
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    for alias in node.names:
                        imports.append(f"{mod}.{alias.name}" if mod else alias.name)

            return ToolResult(
                success=True,
                tool_name="extract_python_ast_symbols",
                data={
                    "file_path": relative_path,
                    "functions": functions,
                    "classes": classes,
                    "imports": imports,
                },
                execution_time_ms=(time.time() - start_time) * 1000,
            )
        except SyntaxError as e:
            return ToolResult(
                success=False,
                tool_name="extract_python_ast_symbols",
                error=f"Python syntax error in {relative_path}: {e}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name="extract_python_ast_symbols",
                error=f"AST parsing error: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )
