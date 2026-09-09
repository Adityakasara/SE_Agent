from datetime import datetime
from typing import Any, Dict, List, Optional
import json

from ..config.settings import Settings, get_settings
from ..graph.state import AgentState
from ..llm import LLMClient
from ..utils.logging import logger

CONFIDENCE_THRESHOLD = 0.5


class SupervisorAgent:
    """
    Supervisor Agent responsible for:
    - Understanding task type
    - Dynamic agent selection & routing
    - Failure detection and re-planning trigger
    - Halting when confidence is low
    - Enforcing safety checkpoints
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.llm = LLMClient(self.settings)

    def classify_task_type(self, task_description: str) -> str:
        """Classify user task into standard engineering categories."""
        desc_lower = task_description.lower()
        if any(w in desc_lower for w in ["fix", "bug", "error", "500", "404", "exception", "broken", "issue"]):
            return "bug_fix"
        elif any(w in desc_lower for w in ["test", "coverage", "pytest", "unit test"]):
            return "test_gen"
        elif any(w in desc_lower for w in ["refactor", "clean", "optimize", "restructure"]):
            return "refactor"
        elif any(w in desc_lower for w in ["doc", "readme", "explain", "comment"]):
            return "docs"
        elif any(w in desc_lower for w in ["add", "create", "feature", "endpoint", "implement"]):
            return "feature"
        return "general"

    def plan_next_step(self, state: AgentState) -> AgentState:
        """
        Dynamically determine the next agent or terminal transition based on workflow progress.
        """
        task_desc = state.get("task_description", "")
        task_type = state.get("task_type") or self.classify_task_type(task_desc)
        state["task_type"] = task_type

        # Initialize history if missing
        if "history" not in state or state["history"] is None:
            state["history"] = []

        # Check confidence stop
        current_confidence = state.get("confidence", 1.0)
        if current_confidence < CONFIDENCE_THRESHOLD:
            logger.warning(f"Task {state.get('task_id')}: Confidence {current_confidence} is below threshold {CONFIDENCE_THRESHOLD}. Halting.")
            state["status"] = "STOPPED_LOW_CONFIDENCE"
            state["next_agent"] = "end"
            state["error_message"] = f"Execution stopped: Low confidence score ({current_confidence:.2f})"
            self._log_history(state, "supervisor", "Stopped workflow due to low confidence.")
            return state

        # 1. Step 1: Repository Understanding
        if not state.get("repository_info"):
            state["next_agent"] = "repository_agent"
            state["current_step"] = "repository_understanding"
            self._log_history(state, "supervisor", "Routing to Repository Agent to inspect codebase.")
            return state

        # 2. Step 2: Code Search
        if not state.get("relevant_files"):
            state["next_agent"] = "code_search_agent"
            state["current_step"] = "code_search"
            self._log_history(state, "supervisor", "Routing to Code Search Agent to identify target files.")
            return state

        # 3. Step 3: Bug Analysis
        if not state.get("bug_analysis") and task_type in ["bug_fix", "feature", "refactor"]:
            state["next_agent"] = "analysis_agent"
            state["current_step"] = "bug_analysis"
            self._log_history(state, "supervisor", "Routing to Analysis Agent to diagnose root cause.")
            return state

        # 4. Step 4: Solution Planning
        if not state.get("solution_plan"):
            state["next_agent"] = "solution_agent"
            state["current_step"] = "solution_planning"
            self._log_history(state, "supervisor", "Routing to Solution Agent to design patch.")
            return state

        # 5. Step 5: Safety Check before Code Modification
        if not state.get("safety_check"):
            state["next_agent"] = "safety_agent"
            state["current_step"] = "safety_pre_check"
            self._log_history(state, "supervisor", "Routing to Safety Agent for pre-modification validation.")
            return state

        # If safety check failed, stop or request approval
        safety = state.get("safety_check", {})
        if safety.get("is_safe") is False and not state.get("human_approved"):
            logger.warning(f"Safety check raised warnings: {safety.get('reason')}")

        # 6. Step 6: Code Modification
        if not state.get("code_changes"):
            state["next_agent"] = "coding_agent"
            state["current_step"] = "code_modification"
            self._log_history(state, "supervisor", "Routing to Coding Agent to apply patch in isolated sandbox.")
            return state

        # 7. Step 7: Test Execution & Verification
        if not state.get("test_results"):
            state["next_agent"] = "test_agent"
            state["current_step"] = "test_execution"
            self._log_history(state, "supervisor", "Routing to Test Agent to run regression tests.")
            return state

        # 8. Check test results - Self-Correction / Re-planning loop
        test_res = state.get("test_results", {})
        tests_passed = test_res.get("tests_passed", False)

        if not tests_passed:
            retries = state.get("retry_count", 0)
            max_retries = state.get("max_retries", 3)
            if retries < max_retries:
                state["retry_count"] = retries + 1
                logger.info(f"Test failure detected. Triggering re-planning attempt {state['retry_count']}/{max_retries}.")
                # Reset downstream artifacts to force re-planning with failure context
                state["solution_plan"] = None
                state["code_changes"] = None
                state["test_results"] = None
                state["next_agent"] = "solution_agent"
                state["current_step"] = "re_planning"
                self._log_history(state, "supervisor", f"Tests failed. Initiating re-planning attempt {state['retry_count']}.")
                return state
            else:
                logger.warning(f"Max retries ({max_retries}) exceeded. Escalating to human intervention.")
                state["status"] = "FAILED"
                state["next_agent"] = "end"
                state["error_message"] = f"Max retries ({max_retries}) exceeded: Failed to resolve issue after automatic attempts."
                self._log_history(state, "supervisor", "Max retries exceeded. Halting for human review.")
                return state

        # 9. Step 9: Verification Agent
        if not state.get("verification_result"):
            state["next_agent"] = "verification_agent"
            state["current_step"] = "verification"
            self._log_history(state, "supervisor", "Routing to Verification Agent for independent validation.")
            return state

        # 10. Step 10: Human Approval Check
        if state.get("human_approved") is None:
            state["status"] = "AWAITING_APPROVAL"
            state["next_agent"] = "human_approval"
            state["current_step"] = "awaiting_human_approval"
            self._log_history(state, "supervisor", "Solution verified. Awaiting human approval.")
            return state

        if state.get("human_approved") is False:
            feedback = state.get("human_feedback", "User requested changes.")
            logger.info(f"User rejected patch with feedback: {feedback}")
            # Reset solution for revision
            state["solution_plan"] = None
            state["code_changes"] = None
            state["test_results"] = None
            state["verification_result"] = None
            state["human_approved"] = None
            state["next_agent"] = "solution_agent"
            state["current_step"] = "addressing_feedback"
            self._log_history(state, "supervisor", f"User requested changes: {feedback}")
            return state

        # 11. Final Completion
        state["status"] = "COMPLETED"
        state["next_agent"] = "end"
        state["current_step"] = "completed"
        self._log_history(state, "supervisor", "Task approved and finalized successfully.")
        return state

    def _log_history(self, state: AgentState, agent_name: str, message: str):
        """Append an entry to the execution trace."""
        state["history"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "agent": agent_name,
            "step": state.get("current_step", ""),
            "message": message,
            "next_agent": state.get("next_agent", ""),
        })
