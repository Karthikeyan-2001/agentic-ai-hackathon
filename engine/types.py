from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ErrorType = Literal["none", "misconception", "slip", "gap", "unclear"]
ConfidenceTap = Literal["sure", "not_sure"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Concept(StrictModel):
    id: str
    name: str
    chapter: str
    description: str
    prerequisites: list[str] = []


class Misconception(StrictModel):
    id: str
    concept_id: str
    description: str
    example_wordings: list[str] = []


class Option(StrictModel):
    id: str
    text: str
    is_correct: bool
    misconception_ids: list[str] = []


class Question(StrictModel):
    id: str
    concept_id: str
    stem: str
    options: list[Option]
    difficulty_prior: int = Field(ge=1, le=5)
    source: Literal["seed", "generated"]


class Diagnosis(StrictModel):
    error_type: ErrorType
    misconception_id: str | None = None
    first_wrong_step: str | None = None
    evidence_quote: str | None = None
    confidence: float = Field(ge=0, le=1)


@dataclass
class ConceptState:
    concept_id: str
    mastery: float = 0.3
    stability_days: float = 2.0
    last_practiced_at: datetime | None = None


@dataclass
class MisconceptionState:
    misconception_id: str
    probability: float = 0.05
    status: str = "inactive"
    stability_days: float = 3.0
    resolved_at: datetime | None = None
    was_active: bool = False
