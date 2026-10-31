import json
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import update
from sqlmodel import Session, delete, select

from agent.content import Content
from agent.loop import AppliedAnswer, LearnerSnapshot
from api.models import (
    AnswerRow,
    AppClock,
    ConceptStateRow,
    GeneratedQuestionRow,
    LlmCache,
    MisconceptionStateRow,
    QuestionBaseline,
    QuestionState,
    Student,
)
from engine.elo import starting_elo
from engine.selection import Selection
from engine.types import ConceptState, MisconceptionState, Question

DEMO_QUESTION = "q_range_count"
DEMO_STUDENTS = [
    ("A", "Student A", DEMO_QUESTION, True),
    ("B", "Student B", DEMO_QUESTION, True),
    ("C", "Student C", DEMO_QUESTION, True),
    ("D", "Student D", None, False),
]
RECENT_LIMIT = 3


class SqlCacheStore:
    def __init__(self, session_factory: Callable[[], Session]):
        self.session_factory = session_factory

    def get(self, key: str) -> str | None:
        with self.session_factory() as session:
            row = session.get(LlmCache, key)
            return row.response_json if row else None

    def set(self, key: str, value: str) -> None:
        with self.session_factory() as session:
            session.merge(LlmCache(key=key, response_json=value, created_at=system_time()))
            session.commit()


def system_time() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def offset_days(session: Session) -> int:
    clock = session.get(AppClock, 1)
    return clock.offset_days if clock else 0


def current_time(session: Session) -> datetime:
    return system_time() + timedelta(days=offset_days(session))


def set_offset_days(session: Session, days: int) -> None:
    clock = session.get(AppClock, 1) or AppClock(id=1)
    clock.offset_days = days
    session.add(clock)


def initialise(session: Session, content: Content) -> None:
    """Create starting rows. Safe to repeat."""
    for row in session.exec(select(GeneratedQuestionRow)).all():
        question = Question.model_validate_json(row.question_json)
        content.questions.setdefault(question.id, question)
    for question in content.questions.values():
        if session.get(QuestionState, question.id) is None:
            session.add(QuestionState(question_id=question.id, difficulty_elo=starting_elo(question.difficulty_prior)))
    for student_id, name, pinned, complete in DEMO_STUDENTS:
        student = session.get(Student, student_id)
        if student is None:
            session.add(Student(id=student_id, name=name, pinned_question_id=pinned, diagnostic_complete=complete))
            continue
        # The questions can change between runs, and a student can't be left waiting on one that's gone.
        if student.pinned_question_id is not None and student.pinned_question_id not in content.questions:
            student.pinned_question_id = pinned
        if student.served_question_id is not None and student.served_question_id not in content.questions:
            clear_served(student)
        session.add(student)
    if session.get(AppClock, 1) is None:
        session.add(AppClock(id=1, offset_days=0))
    session.commit()


def reset_demo(session: Session, content: Content) -> None:
    for student_id, _, pinned, complete in DEMO_STUDENTS:
        session.exec(delete(AnswerRow).where(AnswerRow.student_id == student_id))
        session.exec(delete(ConceptStateRow).where(ConceptStateRow.student_id == student_id))
        session.exec(delete(MisconceptionStateRow).where(MisconceptionStateRow.student_id == student_id))
        student = session.get(Student, student_id)
        student.ability_elo = 1500.0
        student.pinned_question_id = pinned
        student.diagnostic_complete = complete
        clear_served(student)
        session.add(student)
    for row in session.exec(select(QuestionState)).all():
        baseline = session.get(QuestionBaseline, row.question_id)
        if baseline is not None:
            row.difficulty_elo = baseline.difficulty_elo
            row.attempts = baseline.attempts
        elif row.question_id in content.questions:
            row.difficulty_elo = starting_elo(content.questions[row.question_id].difficulty_prior)
            row.attempts = 0
        session.add(row)
    set_offset_days(session, 0)
    session.commit()


def clear_served(student: Student) -> None:
    student.served_question_id = None
    student.served_rule = None
    student.served_reason = None
    student.served_hypotheses_json = None


def load_snapshot(session: Session, student_id: str) -> LearnerSnapshot:
    student = session.get(Student, student_id)
    concept_rows = session.exec(select(ConceptStateRow).where(ConceptStateRow.student_id == student_id)).all()
    misconception_rows = session.exec(
        select(MisconceptionStateRow).where(MisconceptionStateRow.student_id == student_id)
    ).all()
    answers = session.exec(
        select(AnswerRow).where(AnswerRow.student_id == student_id).order_by(AnswerRow.id)
    ).all()
    question_rows = session.exec(select(QuestionState)).all()
    last_seen: dict[str, datetime] = {}
    for answer in answers:
        last_seen[answer.question_id] = answer.created_at
    return LearnerSnapshot(
        ability_elo=student.ability_elo,
        pinned_question_id=student.pinned_question_id,
        diagnostic_complete=student.diagnostic_complete,
        answer_count=len(answers),
        concept_states={
            row.concept_id: ConceptState(row.concept_id, row.mastery, row.stability_days, row.last_practiced_at)
            for row in concept_rows
        },
        misconception_states={
            row.misconception_id: MisconceptionState(
                row.misconception_id, row.probability, row.status, row.stability_days, row.resolved_at, row.was_active
            )
            for row in misconception_rows
        },
        difficulty_elo={row.question_id: row.difficulty_elo for row in question_rows},
        recent_question_ids=[answer.question_id for answer in answers[-RECENT_LIMIT:]],
        last_seen=last_seen,
    )


def save_applied(
    session: Session,
    student_id: str,
    question: Question,
    option_id: str,
    reasoning: str,
    confidence_tap: str,
    diagnosis_json: str,
    trace: list[dict],
    applied: AppliedAnswer,
    now: datetime,
) -> None:
    snapshot = applied.snapshot
    student = session.get(Student, student_id)
    student.ability_elo = snapshot.ability_elo
    student.pinned_question_id = snapshot.pinned_question_id
    student.diagnostic_complete = snapshot.diagnostic_complete
    session.add(student)
    for state in snapshot.concept_states.values():
        session.merge(
            ConceptStateRow(
                student_id=student_id,
                concept_id=state.concept_id,
                mastery=state.mastery,
                stability_days=state.stability_days,
                last_practiced_at=state.last_practiced_at,
            )
        )
    for state in snapshot.misconception_states.values():
        session.merge(
            MisconceptionStateRow(
                student_id=student_id,
                misconception_id=state.misconception_id,
                probability=state.probability,
                status=state.status,
                stability_days=state.stability_days,
                resolved_at=state.resolved_at,
                was_active=state.was_active,
            )
        )
    question_state = session.get(QuestionState, question.id) or QuestionState(
        question_id=question.id, difficulty_elo=starting_elo(question.difficulty_prior)
    )
    question_state.difficulty_elo = snapshot.difficulty_elo[question.id]
    question_state.attempts += 1
    session.add(question_state)
    session.add(
        AnswerRow(
            student_id=student_id,
            question_id=question.id,
            option_id=option_id,
            reasoning=reasoning,
            confidence_tap=confidence_tap,
            diagnosis_json=diagnosis_json,
            trace_json=json.dumps(trace, default=str),
            created_at=now,
        )
    )


def save_generated(session: Session, question: Question, content: Content) -> None:
    content.questions[question.id] = question
    session.merge(GeneratedQuestionRow(id=question.id, question_json=question.model_dump_json()))
    if session.get(QuestionState, question.id) is None:
        session.add(QuestionState(question_id=question.id, difficulty_elo=starting_elo(question.difficulty_prior)))


def store_served(session: Session, student_id: str, selection: Selection | None) -> None:
    student = session.get(Student, student_id)
    if selection is None or selection.question_id is None:
        clear_served(student)
    else:
        student.served_question_id = selection.question_id
        student.served_rule = selection.rule
        student.served_reason = selection.reason
        student.served_hypotheses_json = json.dumps([list(item) for item in selection.hypotheses])
    session.add(student)


def claim_served_question(session: Session, student_id: str, question_id: str) -> bool:
    """Take the served question atomically, so a double submit applies only once."""
    result = session.exec(
        update(Student)
        .where(Student.id == student_id, Student.served_question_id == question_id)
        .values(served_question_id=None)
    )
    session.commit()
    return result.rowcount == 1


def restore_served_question(session: Session, student_id: str, question_id: str) -> None:
    student = session.get(Student, student_id)
    student.served_question_id = question_id
    session.add(student)
    session.commit()
