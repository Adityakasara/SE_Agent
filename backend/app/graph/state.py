from typing import Any, Dict, List, Optional, TypedDict


class AgentState(TypedDict):
    """LangGraph state schema representing the full lifecycle of an engineering task."""

    # Task identity and inputs
    task_id: str
    task_description: str
    repo_name: str
    repo_path: str
    sandbox_path: Optional[str]

    # Task classification & flow control
    task_type: Optional[str]  # e.g., "bug_fix", "feature", "refactor", "test_gen", "docs"
    current_step: str
    next_agent: str
    confidence: float
    retry_count: int
    max_retries: int
    status: str  # "IN_PROGRESS", "AWAITING_APPROVAL", "COMPLETED", "FAILED", "STOPPED_LOW_CONFIDENCE"
    error_message: Optional[str]

    # Agent data deliverables
    repository_info: Optional[Dict[str, Any]]
    relevant_files: List[str]
    code_snippets: Dict[str, str]
    bug_analysis: Optional[Dict[str, Any]]
    solution_plan: Optional[Dict[str, Any]]
    code_changes: Optional[Dict[str, Any]]
    test_results: Optional[Dict[str, Any]]
    verification_result: Optional[Dict[str, Any]]
    safety_check: Optional[Dict[str, Any]]

    # Human-in-the-loop flags
    human_approved: Optional[bool]
    human_feedback: Optional[str]

    # Trace history & log of agent actions
    history: List[Dict[str, Any]]
