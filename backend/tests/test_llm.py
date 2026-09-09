from app.config.settings import Settings
from app.llm import LLMClient, get_llm


def test_mock_llm_client():
    settings = Settings(LLM_PROVIDER="mock")
    client = LLMClient(settings=settings)
    res = client.generate("Please analyze the repository.")
    assert res.content is not None
    assert len(res.content) > 0
    assert "mock" in res.model.lower() or "gpt" in res.model.lower()


def test_get_llm_factory_mock():
    settings = Settings(LLM_PROVIDER="mock", LLM_MODEL="mock-ai")
    model = get_llm(settings=settings)
    assert model is not None
