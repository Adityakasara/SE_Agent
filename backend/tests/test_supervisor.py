import pytest
from app.agents.supervisor import SupervisorAgent
from app.graph.state import AgentState


@pytest.fixture
def supervisor():
    return SupervisorAgent()


@pytest.fixture
def base_state():
    return AgentState(
        task_id="test_task_1",
        task_description="Fix the /users API returning HTTP 500 when email is missing.",
        repo_name="demo_fastapi_app",
        repo_path="./workspace/repositories/demo_fastapi_app",
        sandbox_path=None,
        task_type=None,
        current_step="init",
        next_agent="",
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


def test_classify_task_type(supervisor):
    assert supervisor.classify_task_type("Fix 500 server error in auth") == "bug_fix"
    assert supervisor.classify_task_type("Add pytest coverage for users") == "test_gen"
    assert supervisor.classify_task_type("Refactor database models") == "refactor"
    assert supervisor.classify_task_type("Update README documentation") == "docs"
    assert supervisor.classify_task_type("Add new /analytics endpoint") == "feature"


def test_routing_to_repository_agent_first(supervisor, base_state):
    updated = supervisor.plan_next_step(base_state)
    assert updated["next_agent"] == "repository_agent"
    assert updated["current_step"] == "repository_understanding"


def test_routing_to_code_search_when_repo_known(supervisor, base_state):
    base_state["repository_info"] = {"repo_name": "demo_fastapi_app"}
    updated = supervisor.plan_next_step(base_state)
    assert updated["next_agent"] == "code_search_agent"


def test_confidence_threshold_stop(supervisor, base_state):
    base_state["confidence"] = 0.30  # Below 0.5 threshold
    updated = supervisor.plan_next_step(base_state)
    assert updated["status"] == "STOPPED_LOW_CONFIDENCE"
    assert updated["next_agent"] == "end"
    assert "low confidence" in updated["error_message"].lower()


def test_self_correction_retry_trigger(supervisor, base_state):
    base_state["repository_info"] = {"repo_name": "demo_fastapi_app"}
    base_state["relevant_files"] = ["app/routes/users.py"]
    base_state["bug_analysis"] = {"root_cause": "none check"}
    base_state["solution_plan"] = {"steps": ["fix"]}
    base_state["safety_check"] = {"is_safe": True}
    base_state["code_changes"] = {"diff": "+ fix"}
    # Simulated test failure
    base_state["test_results"] = {"tests_passed": False}
    base_state["retry_count"] = 0

    updated = supervisor.plan_next_step(base_state)
    assert updated["retry_count"] == 1
    assert updated["next_agent"] == "solution_agent"
    assert updated["solution_plan"] is None  # Reset for re-planning


def test_max_retries_escalation(supervisor, base_state):
    base_state["repository_info"] = {"repo_name": "demo_fastapi_app"}
    base_state["relevant_files"] = ["app/routes/users.py"]
    base_state["bug_analysis"] = {"root_cause": "none check"}
    base_state["solution_plan"] = {"steps": ["fix"]}
    base_state["safety_check"] = {"is_safe": True}
    base_state["code_changes"] = {"diff": "+ fix"}
    base_state["test_results"] = {"tests_passed": False}
    base_state["retry_count"] = 3
    base_state["max_retries"] = 3

    updated = supervisor.plan_next_step(base_state)
    assert updated["status"] == "FAILED"
    assert updated["next_agent"] == "end"
    assert "max retries" in updated["error_message"].lower()
