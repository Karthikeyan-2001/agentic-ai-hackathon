from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from agent.llm import CachedClient, LLMError, LLMResult, OllamaClient
from tests.fakes import FailingLLM, FakeLLM


class Answer(BaseModel):
    value: int


class OtherAnswer(BaseModel):
    text: str


class StubOllama:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return SimpleNamespace(message=SimpleNamespace(content=reply))


class MemoryStore:
    def __init__(self):
        self.items = {}

    def get(self, key):
        return self.items.get(key)

    def set(self, key, value):
        self.items[key] = value


def test_sends_required_settings():
    stub = StubOllama('{"value": 1}')
    result = OllamaClient(client=stub).complete("sys", "usr", Answer)
    call = stub.calls[0]
    assert result.value == Answer(value=1) and result.cached is False
    assert call["model"] == "qwen3.5:9b"
    assert call["think"] is False
    assert call["keep_alive"] == -1
    assert call["format"] == Answer.model_json_schema()
    assert call["options"] == {"temperature": 0, "num_ctx": 8192}
    assert "value" in call["messages"][0]["content"] and call["messages"][0]["role"] == "system"
    assert call["messages"][1] == {"role": "user", "content": "usr"}


def test_think_can_be_turned_on():
    stub = StubOllama('{"value": 1}')
    OllamaClient(think=True, client=stub).complete("sys", "usr", Answer)
    assert stub.calls[0]["think"] is True


def test_recovers_on_second_attempt():
    stub = StubOllama("not json", '{"value": 2}')
    assert OllamaClient(client=stub).complete("s", "u", Answer).value.value == 2
    assert len(stub.calls) == 2


def test_retries_twice_then_raises_llm_error():
    stub = StubOllama("bad", "bad", "bad", "unused")
    with pytest.raises(LLMError):
        OllamaClient(client=stub).complete("s", "u", Answer)
    assert len(stub.calls) == 3


def test_connection_error_raises_llm_error():
    with pytest.raises(LLMError):
        OllamaClient(client=StubOllama(ConnectionError("down"))).complete("s", "u", Answer)


def test_response_error_raises_llm_error():
    with pytest.raises(LLMError):
        OllamaClient(client=StubOllama(RuntimeError("model missing"))).complete("s", "u", Answer)


def test_second_call_is_cached_and_skips_inner():
    inner = FakeLLM(lambda s, u, schema: Answer(value=7))
    client = CachedClient(inner, MemoryStore(), "m")
    assert client.complete("s", "u", Answer).cached is False
    second = client.complete("s", "u", Answer)
    assert second.cached is True and second.value == Answer(value=7)
    assert len(inner.calls) == 1


def test_key_changes_with_model_prompt_and_schema():
    store = MemoryStore()
    inner = FakeLLM(lambda s, u, schema: Answer(value=1) if schema is Answer else OtherAnswer(text="x"))
    CachedClient(inner, store, "m").complete("s", "u", Answer)
    CachedClient(inner, store, "other").complete("s", "u", Answer)
    CachedClient(inner, store, "m").complete("s2", "u", Answer)
    CachedClient(inner, store, "m").complete("s", "u2", Answer)
    CachedClient(inner, store, "m").complete("s", "u", OtherAnswer)
    assert len(store.items) == 5


def test_failures_are_not_cached():
    store = MemoryStore()
    with pytest.raises(LLMError):
        CachedClient(FailingLLM(), store, "m").complete("s", "u", Answer)
    assert store.items == {}


def test_llm_result_holds_value():
    assert LLMResult(1, cached=True).value == 1
