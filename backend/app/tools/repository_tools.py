import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..models.schemas import FileInfo, RepositoryMetadata, ToolResult
from ..utils.logging import logger
from .security import BLOCKED_DIRECTORIES, SecurityGuard

EXTENSION_LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".cpp": "C++",
    ".c": "C",
    ".rb": "Ruby",
    ".php": "PHP",
    ".html": "HTML",
    ".css": "CSS",
    ".sql": "SQL",
    ".sh": "Shell",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".toml": "TOML",
    ".md": "Markdown",
}

FRAMEWORK_SIGNATURES = {
    "FastAPI": ["from fastapi import", "import fastapi", "FastAPI("],
    "Flask": ["from flask import", "import flask", "Flask("],
    "Django": ["django.core", "django.urls", "django.db", "manage.py"],
    "Express": ["express()", "require('express')", "from 'express'"],
    "React": ["from 'react'", "import React", "useState", "useEffect"],
    "Next.js": ["next/router", "next/image", "next/link", "next.config.js"],
    "Vue": ["from 'vue'", "createApp("],
    "Pytest": ["import pytest", "def test_", "@pytest.fixture"],
    "Unittest": ["import unittest", "unittest.TestCase"],
}


class RepositoryTools:
    """Tools for inspecting, scanning, and analyzing codebase structure."""

    @staticmethod
    def list_files(
        repo_path: Union[str, Path],
        recursive: bool = True,
        max_depth: int = 5,
        exclude_patterns: Optional[List[str]] = None,
    ) -> ToolResult:
        """List files in the repository with metadata."""
        start_time = time.time()
        base_dir = Path(repo_path).resolve()
        if not base_dir.exists() or not base_dir.is_dir():
            return ToolResult(
                success=False,
                tool_name="list_files",
                error=f"Repository path does not exist: {base_dir}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        excludes = set(BLOCKED_DIRECTORIES)
        if exclude_patterns:
            excludes.update(exclude_patterns)

        file_list: List[FileInfo] = []

        def scan(current_dir: Path, current_depth: int):
            if current_depth > max_depth:
                return
            try:
                for entry in os.scandir(current_dir):
                    if entry.name in excludes or entry.name.startswith("."):
                        continue
                    
                    entry_path = Path(entry.path)
                    sec_check = SecurityGuard.validate_path(base_dir, str(entry_path.relative_to(base_dir)))
                    if not sec_check.is_safe:
                        continue

                    if entry.is_dir(follow_symlinks=False):
                        file_list.append(
                            FileInfo(
                                path=str(entry_path.relative_to(base_dir)),
                                size_bytes=0,
                                is_dir=True,
                                extension="",
                            )
                        )
                        if recursive:
                            scan(entry_path, current_depth + 1)
                    elif entry.is_file(follow_symlinks=False):
                        ext = entry_path.suffix.lower()
                        size = entry.stat().st_size
                        # Count lines for text files < 1MB
                        lines = None
                        if size < 1_000_000 and ext in EXTENSION_LANGUAGE_MAP:
                            try:
                                with open(entry.path, "r", encoding="utf-8", errors="ignore") as f:
                                    lines = sum(1 for _ in f)
                            except Exception:
                                pass

                        file_list.append(
                            FileInfo(
                                path=str(entry_path.relative_to(base_dir)),
                                size_bytes=size,
                                is_dir=False,
                                extension=ext,
                                line_count=lines,
                            )
                        )
            except PermissionError as e:
                logger.warning(f"Permission denied while reading {current_dir}: {e}")

        scan(base_dir, current_depth=1)
        return ToolResult(
            success=True,
            tool_name="list_files",
            data=[f.model_dump() for f in file_list],
            execution_time_ms=(time.time() - start_time) * 1000,
        )

    @staticmethod
    def read_file(
        repo_path: Union[str, Path],
        relative_path: str,
        start_line: int = 1,
        max_lines: int = 500,
    ) -> ToolResult:
        """Safely read lines from a file within the repository."""
        start_time = time.time()
        base_dir = Path(repo_path).resolve()
        sec_check = SecurityGuard.validate_path(base_dir, relative_path)
        if not sec_check.is_safe:
            return ToolResult(
                success=False,
                tool_name="read_file",
                error=sec_check.reason,
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        target_file = Path(sec_check.sanitized_path)
        if not target_file.exists() or not target_file.is_file():
            return ToolResult(
                success=False,
                tool_name="read_file",
                error=f"File not found: {relative_path}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        try:
            with open(target_file, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()

            total_lines = len(all_lines)
            start_idx = max(0, start_line - 1)
            end_idx = min(total_lines, start_idx + max_lines)
            selected_lines = all_lines[start_idx:end_idx]

            # Format with line numbers for the LLM
            formatted_content = "".join(
                f"{i + start_idx + 1:4d} | {line}" for i, line in enumerate(selected_lines)
            )

            return ToolResult(
                success=True,
                tool_name="read_file",
                data={
                    "file_path": relative_path,
                    "total_lines": total_lines,
                    "start_line": start_line,
                    "returned_lines": len(selected_lines),
                    "is_truncated": end_idx < total_lines,
                    "content": formatted_content,
                    "raw_content": "".join(selected_lines),
                },
                execution_time_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name="read_file",
                error=f"Failed to read file: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

    @staticmethod
    def get_repository_structure(
        repo_path: Union[str, Path], max_depth: int = 3
    ) -> ToolResult:
        """Generate a visual ASCII tree and structured hierarchy of the repository."""
        start_time = time.time()
        base_dir = Path(repo_path).resolve()
        if not base_dir.exists():
            return ToolResult(
                success=False,
                tool_name="get_repository_structure",
                error=f"Directory does not exist: {base_dir}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        tree_lines = [f"{base_dir.name}/"]

        def build_tree(current_dir: Path, prefix: str = "", depth: int = 1):
            if depth > max_depth:
                return
            try:
                entries = sorted(
                    [
                        e for e in os.scandir(current_dir)
                        if e.name not in BLOCKED_DIRECTORIES and not e.name.startswith(".")
                    ],
                    key=lambda e: (not e.is_dir(), e.name.lower()),
                )
                total = len(entries)
                for index, entry in enumerate(entries):
                    is_last = index == total - 1
                    connector = "└── " if is_last else "├── "
                    child_prefix = "    " if is_last else "│   "
                    
                    if entry.is_dir():
                        tree_lines.append(f"{prefix}{connector}{entry.name}/")
                        build_tree(Path(entry.path), prefix + child_prefix, depth + 1)
                    else:
                        tree_lines.append(f"{prefix}{connector}{entry.name}")
            except PermissionError:
                pass

        build_tree(base_dir)
        return ToolResult(
            success=True,
            tool_name="get_repository_structure",
            data={
                "tree_string": "\n".join(tree_lines),
                "repo_name": base_dir.name,
            },
            execution_time_ms=(time.time() - start_time) * 1000,
        )

    @staticmethod
    def detect_language(repo_path: Union[str, Path]) -> ToolResult:
        """Scan file extensions to determine language distribution."""
        start_time = time.time()
        base_dir = Path(repo_path).resolve()
        lang_counts: Dict[str, int] = {}

        for root, dirs, files in os.walk(base_dir):
            dirs[:] = [d for d in dirs if d not in BLOCKED_DIRECTORIES and not d.startswith(".")]
            for f in files:
                ext = Path(f).suffix.lower()
                lang = EXTENSION_LANGUAGE_MAP.get(ext)
                if lang:
                    lang_counts[lang] = lang_counts.get(lang, 0) + 1

        primary = "Unknown"
        if lang_counts:
            primary = max(lang_counts.items(), key=lambda x: x[1])[0]

        return ToolResult(
            success=True,
            tool_name="detect_language",
            data={
                "primary_language": primary,
                "language_breakdown": lang_counts,
            },
            execution_time_ms=(time.time() - start_time) * 1000,
        )

    @staticmethod
    def detect_framework(repo_path: Union[str, Path]) -> ToolResult:
        """Identify frameworks and test runners by scanning configuration and source files."""
        start_time = time.time()
        base_dir = Path(repo_path).resolve()
        detected: List[str] = []
        test_framework = None

        # Check config files first
        config_files = ["requirements.txt", "pyproject.toml", "package.json", "go.mod", "Cargo.toml"]
        existing_configs = []
        for cf in config_files:
            cp = base_dir / cf
            if cp.exists():
                existing_configs.append(cf)
                try:
                    content = cp.read_text(encoding="utf-8", errors="ignore").lower()
                    if "fastapi" in content:
                        detected.append("FastAPI")
                    if "flask" in content:
                        detected.append("Flask")
                    if "django" in content:
                        detected.append("Django")
                    if "pytest" in content:
                        test_framework = "pytest"
                    if "react" in content:
                        detected.append("React")
                    if "next" in content:
                        detected.append("Next.js")
                except Exception:
                    pass

        # Scan top-level source files if not yet found
        for root, dirs, files in os.walk(base_dir):
            dirs[:] = [d for d in dirs if d not in BLOCKED_DIRECTORIES and not d.startswith(".")]
            for file in files:
                file_path = Path(root) / file
                ext = file_path.suffix.lower()
                if ext in [".py", ".js", ".ts", ".jsx", ".tsx"] and file_path.stat().st_size < 100_000:
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        for framework, signatures in FRAMEWORK_SIGNATURES.items():
                            if framework not in detected and any(sig in content for sig in signatures):
                                if "test" in framework.lower():
                                    test_framework = framework
                                else:
                                    detected.append(framework)
                    except Exception:
                        pass

        return ToolResult(
            success=True,
            tool_name="detect_framework",
            data={
                "frameworks": list(set(detected)),
                "test_framework": test_framework,
                "config_files": existing_configs,
            },
            execution_time_ms=(time.time() - start_time) * 1000,
        )

    @classmethod
    def get_repository_metadata(cls, repo_path: Union[str, Path]) -> RepositoryMetadata:
        """Assemble comprehensive repository metadata for downstream agents."""
        base_dir = Path(repo_path).resolve()
        lang_res = cls.detect_language(base_dir)
        framework_res = cls.detect_framework(base_dir)
        list_res = cls.list_files(base_dir, recursive=True)

        files = list_res.data if list_res.success else []
        file_paths = [f["path"] for f in files if not f["is_dir"]]
        dir_count = sum(1 for f in files if f["is_dir"])

        # Detect entry points
        entry_candidates = ["main.py", "app.py", "index.py", "server.py", "index.js", "app.js", "main.go"]
        entry_points = [p for p in file_paths if any(p.endswith(cand) for cand in entry_candidates)]

        # Readme snippet
        readme_snippet = None
        for cand in ["README.md", "readme.md", "README.rst", "README.txt"]:
            r_path = base_dir / cand
            if r_path.exists():
                try:
                    readme_snippet = r_path.read_text(encoding="utf-8", errors="ignore")[:1000]
                except Exception:
                    pass
                break

        return RepositoryMetadata(
            repo_name=base_dir.name,
            repo_path=str(base_dir),
            primary_language=lang_res.data.get("primary_language", "Unknown") if lang_res.success else "Unknown",
            languages=lang_res.data.get("language_breakdown", {}) if lang_res.success else {},
            frameworks=framework_res.data.get("frameworks", []) if framework_res.success else [],
            entry_points=entry_points,
            config_files=framework_res.data.get("config_files", []) if framework_res.success else [],
            test_framework=framework_res.data.get("test_framework") if framework_res.success else None,
            total_files=len(file_paths),
            total_directories=dir_count,
            readme_snippet=readme_snippet,
        )
