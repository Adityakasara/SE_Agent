#!/usr/bin/env python3
import json
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.graph.state import AgentState
from app.graph.workflow import create_agent_workflow


def run_phase2_demo():
    print("=" * 70)
    print("AI Software Engineering Agent - Phase 2: LangGraph Supervisor Demo")
    print("=" * 70)

    repo_path = str(
        Path(__file__).resolve().parent.parent.parent
        / "workspace"
        / "repositories"
        / "demo_fastapi_app"
    )

    task_desc = "Fix the /users API returning HTTP 500 when email is missing."
    print(f"\n[Task Received]: '{task_desc}'")
    print(f"[Target Repository]: {repo_path}")

    # Build the StateGraph workflow
    workflow = create_agent_workflow()

    initial_state = AgentState(
        task_id="task_phase2_001",
        task_description=task_desc,
        repo_name="demo_fastapi_app",
        repo_path=repo_path,
        sandbox_path=None,
        task_type=None,  # Supervisor will auto-classify
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

    print("\n--- Executing Dynamic LangGraph State Graph Workflow ---")
    final_state = workflow.invoke(initial_state)

    print("\n[Workflow Execution Completed]")
    print(f"  - Final Status: {final_state['status']}")
    print(f"  - Task Category: {final_state['task_type']}")
    print(f"  - Identified Target Files: {final_state['relevant_files']}")
    print(f"  - Bug Diagnosis: {final_state['bug_analysis']['root_cause']}")
    print(f"  - Solution Plan: {final_state['solution_plan']['solution_summary']}")
    print(f"  - Safety Classification: {final_state['safety_check']['action_classification']}")
    print(f"  - Verification Status: Tests Passed={final_state['verification_result']['tests_passed']}, Recommendation={final_state['verification_result']['recommendation']}")

    print("\n--- Agent Trace History ---")
    for idx, event in enumerate(final_state["history"], 1):
        print(f"{idx:2d}. [{event['agent'].upper()}] Step: {event['step']} -> {event['message']}")

    print("\n" + "=" * 70)
    print("Phase 2 LangGraph Supervisor Execution Successful!")
    print("=" * 70)


if __name__ == "__main__":
    run_phase2_demo()
