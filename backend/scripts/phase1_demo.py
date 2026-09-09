#!/usr/bin/env python3
import json
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config.settings import get_settings
from app.llm import LLMClient
from app.tools.code_tools import CodeTools
from app.tools.git_tools import GitTools
from app.tools.repository_tools import RepositoryTools
from app.utils.logging import logger


def run_phase1_demo():
    print("=" * 60)
    print("AI Software Engineering Agent - Phase 1 Demonstration")
    print("=" * 60)

    settings = get_settings()
    repo_path = Path(__file__).resolve().parent.parent.parent / "workspace" / "repositories" / "demo_fastapi_app"

    print(f"\n[1] Analyzing Repository: {repo_path.name}")
    meta = RepositoryTools.get_repository_metadata(repo_path)
    print(f"  - Primary Language: {meta.primary_language}")
    print(f"  - Frameworks: {meta.frameworks}")
    print(f"  - Total Files: {meta.total_files}")
    print(f"  - Entry Points: {meta.entry_points}")
    print(f"  - Config Files: {meta.config_files}")

    print("\n[2] Repository Structure Tree:")
    tree_res = RepositoryTools.get_repository_structure(repo_path)
    print(tree_res.data["tree_string"])

    print("\n[3] Reading Code File with Line Numbers (app/routes/users.py):")
    read_res = RepositoryTools.read_file(repo_path, "app/routes/users.py", start_line=1, max_lines=25)
    print(read_res.data["content"])

    print("\n[4] AST Code Inspection on app/routes/users.py:")
    ast_res = CodeTools.extract_python_ast_symbols(repo_path, "app/routes/users.py")
    print(f"  - Extracted Functions: {[f['name'] for f in ast_res.data['functions']]}")
    print(f"  - Extracted Imports: {ast_res.data['imports']}")

    print("\n[5] Creating Isolated Git Sandbox for Safe Modification:")
    sandbox_path = settings.get_sandbox_path("phase1_demo_task")
    sandbox_res = GitTools.create_isolated_sandbox(repo_path, sandbox_path, branch_name="fix/missing-email-validation")
    print(f"  - Sandbox Created At: {sandbox_res.data['sandbox_path']}")
    print(f"  - Working Branch: {sandbox_res.data['branch']}")

    print("\n[6] Applying Fix to Isolated Sandbox:")
    # Replace buggy code with safe null-check
    fix_code = '''from typing import List
from fastapi import APIRouter, HTTPException, status
from ..models.user import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])

fake_db = [
    {"id": 1, "username": "alice", "email": "alice@example.com", "role": "admin"},
    {"id": 2, "username": "bob", "email": "bob@example.com", "role": "developer"},
]


@router.get("", response_model=List[UserResponse])
def get_users():
    return fake_db


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate):
    # Fixed: Safely validate and sanitize email
    if not user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required"
        )
    normalized_email = user.email.lower()

    # Check for duplicate email
    for existing in fake_db:
        if existing["email"].lower() == normalized_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    new_user = {
        "id": len(fake_db) + 1,
        "username": user.username,
        "email": normalized_email,
        "role": user.role,
    }
    fake_db.append(new_user)
    return new_user
'''
    CodeTools.edit_file(sandbox_path, "app/routes/users.py", fix_code)
    print("  - File edited successfully.")

    print("\n[7] Generating Git Diff from Isolated Sandbox:")
    diff_res = GitTools.get_git_diff(sandbox_path)
    print(diff_res.data["diff_text"])

    print("\n[8] LLM Client Interaction (Planning prompt):")
    llm = LLMClient(settings)
    prompt = f"Summarize the root cause and proposed fix for repository {meta.repo_name}."
    llm_res = llm.generate(prompt=prompt, system_prompt="You are a senior software engineering AI.")
    print(f"  - Model: {llm_res.model}")
    print(f"  - Response: {llm_res.content}")

    print("\n" + "=" * 60)
    print("Phase 1 Demonstration Completed Successfully!")
    print("=" * 60)


if __name__ == "__main__":
    run_phase1_demo()
