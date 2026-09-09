from pathlib import Path
from app.graph.state import AgentState
from app.graph.workflow import create_agent_workflow


def test_langgraph_workflow_execution():
    app = create_agent_workflow()
    repo_path = str(
        Path(__file__).resolve().parent.parent.parent
        / "workspace"
        / "repositories"
        / "demo_fastapi_app"
    )

    initial_state = AgentState(
        task_id="workflow_test_task",
        task_description="Fix the /users API returning HTTP 500 when email is missing.",
        repo_name="demo_fastapi_app",
        repo_path=repo_path,
        sandbox_path=None,
        task_type="bug_fix",
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

    final_state = app.invoke(initial_state)

    assert final_state["status"] == "AWAITING_APPROVAL"
    assert final_state["repository_info"] is not None
    assert len(final_state["relevant_files"]) > 0
    assert final_state["bug_analysis"] is not None
    assert final_state["solution_plan"] is not None
    assert final_state["safety_check"]["is_safe"] is True
    assert final_state["verification_result"]["tests_passed"] is True
    assert len(final_state["history"]) >= 8
