from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config.settings import get_settings
from .graph.state import AgentState
from .graph.workflow import create_agent_workflow
from .tools.git_tools import GitTools
from .tools.repository_tools import RepositoryTools
from .utils.logging import logger

app = FastAPI(
    title="AI Software Engineering Agent API",
    description="Autonomous Agentic AI for repository analysis, bug fixing, test verification, and safe PR generation.",
    version="1.0.0",
)

# Enable CORS for React/Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings = get_settings()
workflow_app = create_agent_workflow()

# In-memory Task store (can easily be replaced with SQLite/PostgreSQL)
tasks_db: Dict[str, Dict[str, Any]] = {}


# --- Request/Response Models ---
class CreateTaskRequest(BaseModel):
    repository_name: str = Field(..., description="Target repository name or path")
    task_description: str = Field(..., description="Natural language problem statement or bug report")


class ApproveTaskRequest(BaseModel):
    feedback: Optional[str] = Field(default=None, description="Optional feedback or notes")


class RejectTaskRequest(BaseModel):
    reason: str = Field(..., description="Reason for rejection or requested changes")


@app.get("/")
def root():
    return {
        "service": "AI Software Engineering Agent",
        "status": "online",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "tasks": "/tasks",
            "repositories": "/repositories",
        },
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "provider": settings.LLM_PROVIDER, "model": settings.LLM_MODEL}


@app.get("/repositories")
def list_available_repositories():
    """List all cloned or available repositories in workspace/repositories."""
    repos_dir = Path(settings.REPOSITORIES_DIR)
    if not repos_dir.is_absolute():
        repos_dir = settings.PROJECT_ROOT / repos_dir
    
    if not repos_dir.exists():
        return {"repositories": []}

    repo_list = []
    for item in repos_dir.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            meta = RepositoryTools.get_repository_metadata(item)
            repo_list.append(meta.model_dump())

    return {"repositories": repo_list}


@app.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(req: CreateTaskRequest):
    """Submit an engineering task to the Supervisor Agent."""
    repo_path = settings.get_repo_path(req.repository_name)
    if not repo_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{req.repository_name}' not found at {repo_path}",
        )

    task_id = f"task_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{len(tasks_db)+1:03d}"

    initial_state = AgentState(
        task_id=task_id,
        task_description=req.task_description,
        repo_name=repo_path.name,
        repo_path=str(repo_path),
        sandbox_path=None,
        task_type=None,
        current_step="init",
        next_agent="supervisor",
        confidence=0.95,
        retry_count=0,
        max_retries=3,
        status="IN_PROGRESS",
        error_message=None,
        repository_info=None,
        relevant_files=[],
        code_snippets={},
        bug_analysis=None,
        solution_plan=None,
        code_changes=None,
        test_results=None,
        verification_result=None,
        safety_check=None,
        human_approved=None,
        human_feedback=None,
        history=[],
    )

    # Run LangGraph Agent workflow
    logger.info(f"Starting agent execution for task: {task_id}")
    final_state = workflow_app.invoke(initial_state)
    tasks_db[task_id] = final_state

    return {
        "task_id": task_id,
        "status": final_state.get("status"),
        "task_type": final_state.get("task_type"),
        "current_step": final_state.get("current_step"),
        "confidence": final_state.get("confidence"),
        "summary": final_state.get("solution_plan", {}).get("solution_summary") if final_state.get("solution_plan") else None,
    }


@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    """Get full state and details for a task."""
    if task_id not in tasks_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return tasks_db[task_id]


@app.get("/tasks/{task_id}/status")
def get_task_status(task_id: str):
    """Get quick status and progress summary."""
    if task_id not in tasks_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    state = tasks_db[task_id]
    return {
        "task_id": task_id,
        "status": state.get("status"),
        "current_step": state.get("current_step"),
        "confidence": state.get("confidence"),
        "retry_count": state.get("retry_count"),
        "error_message": state.get("error_message"),
    }


@app.get("/tasks/{task_id}/agents")
def get_task_agent_trace(task_id: str):
    """Get chronological agent execution trace."""
    if task_id not in tasks_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return {"task_id": task_id, "trace": tasks_db[task_id].get("history", [])}


@app.get("/tasks/{task_id}/diff")
def get_task_diff(task_id: str):
    """Get unified code diff generated by the Coding Agent."""
    if task_id not in tasks_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    code_changes = tasks_db[task_id].get("code_changes") or {}
    return {
        "task_id": task_id,
        "files_changed": code_changes.get("files_changed", []),
        "diff": code_changes.get("diff", ""),
    }


@app.get("/tasks/{task_id}/tests")
def get_task_tests(task_id: str):
    """Get test execution and verification report."""
    if task_id not in tasks_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return {
        "task_id": task_id,
        "test_results": tasks_db[task_id].get("test_results"),
        "verification_result": tasks_db[task_id].get("verification_result"),
    }


@app.post("/tasks/{task_id}/approve")
def approve_task(task_id: str, req: ApproveTaskRequest):
    """Human-in-the-loop: Approve proposed patch and finalize PR."""
    if task_id not in tasks_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    
    state = tasks_db[task_id]
    state["human_approved"] = True
    state["human_feedback"] = req.feedback
    
    # Resume workflow to complete
    final_state = workflow_app.invoke(state)
    tasks_db[task_id] = final_state
    
    return {
        "task_id": task_id,
        "status": final_state.get("status"),
        "message": "Task approved and finalized successfully.",
    }


@app.post("/tasks/{task_id}/reject")
def reject_task(task_id: str, req: RejectTaskRequest):
    """Human-in-the-loop: Reject proposed patch and trigger supervisor re-planning."""
    if task_id not in tasks_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    
    state = tasks_db[task_id]
    state["human_approved"] = False
    state["human_feedback"] = req.reason
    
    # Resume workflow to re-plan with user feedback
    final_state = workflow_app.invoke(state)
    tasks_db[task_id] = final_state
    
    return {
        "task_id": task_id,
        "status": final_state.get("status"),
        "message": f"Task rejected with feedback: '{req.reason}'. Re-planning initiated.",
    }
