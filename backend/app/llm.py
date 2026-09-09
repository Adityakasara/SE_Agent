import os
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel

from .config.settings import Settings, get_settings
from .models.schemas import LLMMessage, LLMResponse
from .utils.logging import logger

try:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
    from langchain_core.language_models.chat_models import BaseChatModel
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    BaseChatModel = object


class MockChatModel:
    """Mock LLM client for local unit tests and offline demonstrations."""

    def __init__(self, model_name: str = "mock-model"):
        self.model_name = model_name

    def invoke(self, messages: Any) -> Any:
        # Generate an intelligent mock response for Phase 1 testing
        msg_str = str(messages)
        content = "Mock LLM Response: Analyzed repository structure and tools successfully."
        if "analyze" in msg_str.lower():
            content = (
                "Analysis complete: Identified target modules and potential missing validations. "
                "Prepared execution plan for next phase."
            )
        elif "json" in msg_str.lower():
            content = '{"status": "ok", "decision": "proceed", "confidence": 0.95}'

        class MockAIMessage:
            def __init__(self, content: str):
                self.content = content
        return MockAIMessage(content=content)


def get_llm(
    settings: Optional[Settings] = None,
    temperature: Optional[float] = None,
    model: Optional[str] = None,
) -> Any:
    """
    Factory to return the configured LangChain chat model or mock fallback.
    Supported providers: 'openai', 'anthropic', 'google', 'ollama', 'mock'.
    """
    settings = settings or get_settings()
    temp = temperature if temperature is not None else settings.LLM_TEMPERATURE
    model_name = model or settings.LLM_MODEL
    provider = settings.LLM_PROVIDER.lower()

    if provider == "mock" or not LANGCHAIN_AVAILABLE:
        logger.info(f"Using Mock LLM client (model: {model_name})")
        return MockChatModel(model_name=model_name)

    try:
        if provider == "openai":
            api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("OPENAI_API_KEY not set; falling back to Mock LLM")
                return MockChatModel(model_name=model_name)
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model=model_name, temperature=temp, api_key=api_key)

        elif provider == "anthropic":
            api_key = settings.ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                logger.warning("ANTHROPIC_API_KEY not set; falling back to Mock LLM")
                return MockChatModel(model_name=model_name)
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(model=model_name, temperature=temp, api_key=api_key)

        elif provider == "google":
            api_key = settings.GOOGLE_API_KEY or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                logger.warning("GOOGLE_API_KEY not set; falling back to Mock LLM")
                return MockChatModel(model_name=model_name)
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(model=model_name, temperature=temp, google_api_key=api_key)

        elif provider == "ollama":
            from langchain_community.chat_models import ChatOllama
            return ChatOllama(model=model_name, base_url=settings.OLLAMA_BASE_URL, temperature=temp)

        else:
            logger.warning(f"Unknown provider '{provider}', falling back to Mock LLM")
            return MockChatModel(model_name=model_name)

    except Exception as e:
        logger.error(f"Failed to initialize LLM provider '{provider}': {e}. Using mock fallback.")
        return MockChatModel(model_name=model_name)


class LLMClient:
    """High level wrapper for prompt execution and structured LLM interactions."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.model = get_llm(self.settings)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """Send prompt to LLM and return structured LLMResponse."""
        if LANGCHAIN_AVAILABLE and hasattr(self.model, "invoke"):
            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            messages.append(HumanMessage(content=prompt))
            response = self.model.invoke(messages)
            content = getattr(response, "content", str(response))
        else:
            mock_res = self.model.invoke(prompt)
            content = getattr(mock_res, "content", str(mock_res))

        return LLMResponse(
            content=content,
            model=getattr(self.model, "model_name", self.settings.LLM_MODEL),
        )
