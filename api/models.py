from pydantic import NaiveDatetime
from sqlmodel import Field, SQLModel


class Student(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    is_simulated: bool = False
    ability_elo: float = 1500.0
    pinned_question_id: str | None = None
    diagnostic_complete: bool = False
    served_question_id: str | None = None
    served_rule: int | None = None
    served_reason: str | None = None
    served_hypotheses_json: str | None = None


class ConceptStateRow(SQLModel, table=True):
    student_id: str = Field(primary_key=True)
    concept_id: str = Field(primary_key=True)
    mastery: float
    stability_days: float
    last_practiced_at: NaiveDatetime | None = None


class MisconceptionStateRow(SQLModel, table=True):
    student_id: str = Field(primary_key=True)
    misconception_id: str = Field(primary_key=True)
    probability: float
    status: str
    stability_days: float
    resolved_at: NaiveDatetime | None = None
    was_active: bool = False


class AnswerRow(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    student_id: str = Field(index=True)
    question_id: str
    option_id: str
    reasoning: str
    confidence_tap: str
    diagnosis_json: str
    trace_json: str
    created_at: NaiveDatetime


class QuestionState(SQLModel, table=True):
    question_id: str = Field(primary_key=True)
    difficulty_elo: float
    attempts: int = 0


class GeneratedQuestionRow(SQLModel, table=True):
    id: str = Field(primary_key=True)
    question_json: str


class LlmCache(SQLModel, table=True):
    key: str = Field(primary_key=True)
    response_json: str
    created_at: NaiveDatetime


class AppClock(SQLModel, table=True):
    id: int = Field(default=1, primary_key=True)
    offset_days: int = 0
