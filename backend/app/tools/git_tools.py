import os
import shutil
import time
from pathlib import Path
from typing import List, Optional, Union

import git
from ..models.schemas import GitDiffResult, ToolResult
from ..utils.logging import logger
from .security import SecurityGuard


class GitTools:
    """Tools for managing isolated Git sandboxes, branches, diffs, and commits."""

    @staticmethod
    def get_repo(repo_path: Union[str, Path]) -> Optional[git.Repo]:
        """Load Git repository safely."""
        try:
            return git.Repo(repo_path)
        except (git.InvalidGitRepositoryError, git.NoSuchPathError) as e:
            logger.warning(f"Not a valid Git repository at {repo_path}: {e}")
            return None

    @staticmethod
    def create_isolated_sandbox(
        source_repo_path: Union[str, Path],
        sandbox_dest_path: Union[str, Path],
        branch_name: Optional[str] = None,
    ) -> ToolResult:
        """
        Creates an isolated copy of the repository in the sandbox directory to ensure
        the original repository is never modified directly.
        """
        start_time = time.time()
        src = Path(source_repo_path).resolve()
        dst = Path(sandbox_dest_path).resolve()

        if not src.exists():
            return ToolResult(
                success=False,
                tool_name="create_isolated_sandbox",
                error=f"Source repository path does not exist: {src}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        try:
            if dst.exists():
                shutil.rmtree(dst)
            dst.parent.mkdir(parents=True, exist_ok=True)

            # Copy repository to isolated sandbox (excluding pycache, etc.)
            def ignore_func(directory, contents):
                return {c for c in contents if c in [".pytest_cache", "__pycache__", "venv", ".venv"]}

            shutil.copytree(src, dst, ignore=ignore_func)

            # Check if dst is a git repo; if not, initialize git for diff tracking
            repo = GitTools.get_repo(dst)
            if repo is None:
                repo = git.Repo.init(dst)
                repo.git.add(A=True)
                repo.index.commit("Initial baseline commit")

            # Create and switch to working branch if requested
            if branch_name:
                current_branches = [b.name for b in repo.branches]
                if branch_name not in current_branches:
                    repo.git.checkout("-b", branch_name)
                else:
                    repo.git.checkout(branch_name)

            return ToolResult(
                success=True,
                tool_name="create_isolated_sandbox",
                data={
                    "sandbox_path": str(dst),
                    "branch": repo.active_branch.name,
                    "is_clean": not repo.is_dirty(untracked_files=True),
                },
                execution_time_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name="create_isolated_sandbox",
                error=f"Failed to create sandbox: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

    @staticmethod
    def get_git_diff(
        repo_path: Union[str, Path], base_ref: Optional[str] = None
    ) -> ToolResult:
        """
        Generate a unified Git diff showing all staged, unstaged, and untracked changes.
        """
        start_time = time.time()
        base_dir = Path(repo_path).resolve()
        repo = GitTools.get_repo(base_dir)

        if repo is None:
            return ToolResult(
                success=False,
                tool_name="get_git_diff",
                error=f"Path is not a git repository: {base_dir}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        try:
            # Track untracked files by staging or inspecting
            untracked = repo.untracked_files
            diff_text = ""

            if base_ref:
                diff_text = repo.git.diff(base_ref)
            else:
                # Diff against HEAD (both staged and unstaged)
                try:
                    diff_text = repo.git.diff("HEAD")
                except git.GitCommandError:
                    diff_text = repo.git.diff()

            # Include untracked files content in diff view if present
            untracked_diffs = []
            for ufile in untracked:
                fpath = base_dir / ufile
                if fpath.is_file() and fpath.stat().st_size < 100_000:
                    try:
                        content = fpath.read_text(encoding="utf-8", errors="replace")
                        formatted_u = f"--- /dev/null\n+++ b/{ufile}\n"
                        formatted_u += "\n".join(f"+{line}" for line in content.splitlines())
                        untracked_diffs.append(formatted_u)
                    except Exception:
                        pass

            if untracked_diffs:
                if diff_text:
                    diff_text += "\n\n"
                diff_text += "\n\n".join(untracked_diffs)

            # Changed files list
            changed_files = list(set([item.a_path for item in repo.index.diff(None)] + untracked))

            insertions = sum(1 for l in diff_text.splitlines() if l.startswith("+") and not l.startswith("+++"))
            deletions = sum(1 for l in diff_text.splitlines() if l.startswith("-") and not l.startswith("---"))

            diff_result = GitDiffResult(
                has_changes=bool(diff_text.strip()),
                files_changed=changed_files,
                diff_text=diff_text,
                insertions=insertions,
                deletions=deletions,
            )

            return ToolResult(
                success=True,
                tool_name="get_git_diff",
                data=diff_result.model_dump(),
                execution_time_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name="get_git_diff",
                error=f"Error generating git diff: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

    @staticmethod
    def get_git_status(repo_path: Union[str, Path]) -> ToolResult:
        """Inspect branch status, modified files, and untracked files."""
        start_time = time.time()
        base_dir = Path(repo_path).resolve()
        repo = GitTools.get_repo(base_dir)

        if repo is None:
            return ToolResult(
                success=False,
                tool_name="get_git_status",
                error=f"Path is not a git repository: {base_dir}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        try:
            modified = [item.a_path for item in repo.index.diff(None)]
            staged = [item.a_path for item in repo.index.diff("HEAD")] if repo.head.is_valid() else []
            untracked = repo.untracked_files

            return ToolResult(
                success=True,
                tool_name="get_git_status",
                data={
                    "branch": repo.active_branch.name,
                    "is_dirty": repo.is_dirty(untracked_files=True),
                    "modified": modified,
                    "staged": staged,
                    "untracked": untracked,
                },
                execution_time_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name="get_git_status",
                error=f"Error checking git status: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )
