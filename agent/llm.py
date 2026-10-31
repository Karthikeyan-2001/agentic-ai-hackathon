import hashlib
import json
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

import ollama
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

DEFAULT_MODEL = "qwen3.5:9b"
TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 3


class LLMError(Exception):
    pass


@dataclass
class LLMResult(Generic[T]):
    value: T
    cached: bool


class LLMClient(Protocol):
    def complete(self, system: str, user: str, schema: type[T]) -> LLMResult[T]: ...


class CacheStore(Protocol):
    def get(self, key: str) -> str | None: ...

    def set(self, key: str, value: str) -> None: ...


class OllamaClient:
    def __init__(self, model: str = DEFAULT_MODEL, think: bool = False, client=None):
        self.model = model
        self.think = think
        self.client = client or ollama.Client(timeout=TIMEOUT_SECONDS)

    def complete(self, system: str, user: str, schema: type[T]) -> LLMResult[T]:
        schema_json = schema.model_json_schema()
        messages = [
            {"role": "system", "content": f"{system}\n\nReply with JSON matching this schema:\n{json.dumps(schema_json)}"},
            {"role": "user", "content": user},
        ]
        last_error: Exception | None = None
        for _ in range(MAX_ATTEMPTS):
            try:
                response = self.client.chat(
                    model=self.model,
                    messages=messages,
                    format=schema_json,
                    options={"temperature": 0, "num_ctx": 8192},
                    think=self.think,
                    keep_alive=-1,
                )
            except Exception as error:
                raise LLMError(f"Ollama call failed: {error}") from error
            try:
                return LLMResult(schema.model_validate_json(response.message.content), cached=False)
            except ValidationError as error:
                last_error = error
        raise LLMError(f"Invalid reply after {MAX_ATTEMPTS} attempts: {last_error}")


class CachedClient:
    def __init__(self, inner: LLMClient, store: CacheStore, model_name: str):
        self.inner = inner
        self.store = store
        self.model_name = model_name

    def _key(self, system: str, user: str, schema: type[BaseModel]) -> str:
        parts = [self.model_name, system, user, json.dumps(schema.model_json_schema(), sort_keys=True)]
        return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()

    def complete(self, system: str, user: str, schema: type[T]) -> LLMResult[T]:
        key = self._key(system, user, schema)
        stored = self.store.get(key)
        if stored is not None:
            try:
                return LLMResult(schema.model_validate_json(stored), cached=True)
            except ValidationError:
                pass
        result = self.inner.complete(system, user, schema)
        self.store.set(key, result.value.model_dump_json())
        return result
