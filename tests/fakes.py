from typing import Callable

from pydantic import BaseModel

from agent.llm import LLMError, LLMResult


class FakeLLM:
    def __init__(self, responder: Callable[[str, str, type], BaseModel]):
        self.responder = responder
        self.calls: list[tuple[str, str, type]] = []

    def complete(self, system: str, user: str, schema: type) -> LLMResult:
        self.calls.append((system, user, schema))
        return LLMResult(self.responder(system, user, schema), cached=False)


class FailingLLM:
    def __init__(self):
        self.calls = 0

    def complete(self, system: str, user: str, schema: type) -> LLMResult:
        self.calls += 1
        raise LLMError("model unavailable")
