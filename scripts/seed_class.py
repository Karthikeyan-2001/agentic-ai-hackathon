import json
import random
from datetime import datetime, timedelta
from typing import Callable

from sqlmodel import Session, delete, select

from agent.content import Content
from agent.loop import apply_answer, new_snapshot
from api import store
from api.models import AnswerRow, ConceptStateRow, MisconceptionStateRow, QuestionBaseline, QuestionState, Student
from engine.elo import expected, starting_elo
from engine.types import Diagnosis, Option, Question

STUDENT_COUNT = 30
HISTORY_DAYS = 14
PICK_MISCONCEPTION = 0.8
# These weights make the class show clear shared gaps. The rest share what's left equally.
FOCUSED_WEIGHTS = {"current_consumed": 0.35, "parallel_resistance_adds": 0.25}


def answers_for_student(rng: random.Random, pool_size: int) -> int:
    return min(rng.randint(12, 15), pool_size)


def _hidden_misconceptions(rng: random.Random, content: Content) -> list[str]:
    ids = sorted(content.misconceptions)
    others = [m for m in ids if m not in FOCUSED_WEIGHTS]
    remaining = 1 - sum(FOCUSED_WEIGHTS.values())
    weights = [FOCUSED_WEIGHTS.get(m, remaining / len(others)) for m in ids]
    count = rng.choice([0, 1, 1, 2])
    chosen: list[str] = []
    while len(chosen) < count:
        pick = rng.choices(ids, weights)[0]
        if pick not in chosen:
            chosen.append(pick)
    return chosen


def _pick_answer(
    rng: random.Random, question: Question, hidden: list[str], ability: float, difficulty: float
) -> tuple[Option, Diagnosis]:
    correct = next(o for o in question.options if o.is_correct)
    wrong = [o for o in question.options if not o.is_correct]
    for option in wrong:
        matches = [m for m in hidden if m in option.misconception_ids]
        if matches and rng.random() < PICK_MISCONCEPTION:
            return option, Diagnosis(
                error_type="misconception", misconception_id=matches[0], evidence_quote="simulated", confidence=1.0
            )
    if rng.random() < expected(ability, difficulty):
        return correct, Diagnosis(error_type="none", confidence=1.0)
    return rng.choice(wrong), Diagnosis(error_type="gap", confidence=1.0)


def _clear_simulated(session: Session, content: Content) -> None:
    student_ids = session.exec(select(Student.id).where(Student.is_simulated == True)).all()  # noqa: E712
    for student_id in student_ids:
        session.exec(delete(AnswerRow).where(AnswerRow.student_id == student_id))
        session.exec(delete(ConceptStateRow).where(ConceptStateRow.student_id == student_id))
        session.exec(delete(MisconceptionStateRow).where(MisconceptionStateRow.student_id == student_id))
        session.exec(delete(Student).where(Student.id == student_id))
    for row in session.exec(select(QuestionState)).all():
        question = content.questions.get(row.question_id)
        if question is not None:
            row.difficulty_elo = starting_elo(question.difficulty_prior)
            row.attempts = 0
            session.add(row)


def seed_class(session_factory: Callable[[], Session], content: Content, now: datetime, seed: int = 42) -> int:
    rng = random.Random(seed)
    question_ids = sorted(content.questions)
    difficulty_elo = {q.id: starting_elo(q.difficulty_prior) for q in content.questions.values()}
    with session_factory() as session:
        _clear_simulated(session, content)
        session.commit()
        for number in range(1, STUDENT_COUNT + 1):
            student_id = f"S{number:02d}"
            session.add(Student(id=student_id, name=f"Student {number:02d}", is_simulated=True, diagnostic_complete=True))
            hidden = _hidden_misconceptions(rng, content)
            count = answers_for_student(rng, len(question_ids))
            chosen = rng.sample(question_ids, count)
            times = sorted(now - timedelta(days=rng.uniform(0, HISTORY_DAYS)) for _ in chosen)
            snapshot = new_snapshot(content, diagnostic_complete=True)
            snapshot.difficulty_elo = difficulty_elo
            session.flush()
            for question_id, moment in zip(chosen, times):
                question = content.questions[question_id]
                option, diagnosis = _pick_answer(
                    rng, question, hidden, snapshot.ability_elo, difficulty_elo[question_id]
                )
                applied = apply_answer(snapshot, question, option.id, diagnosis, "sure", moment, content)
                snapshot = applied.snapshot
                difficulty_elo = snapshot.difficulty_elo
                store.save_applied(
                    session,
                    student_id,
                    question,
                    option.id,
                    "(simulated answer)",
                    "sure",
                    diagnosis.model_dump_json(),
                    [],
                    applied,
                    moment,
                )
                session.flush()
        session.exec(delete(QuestionBaseline))
        for row in session.exec(select(QuestionState)).all():
            session.add(
                QuestionBaseline(question_id=row.question_id, difficulty_elo=row.difficulty_elo, attempts=row.attempts)
            )
        session.commit()
    return STUDENT_COUNT


def main() -> None:
    from api.main import create_app

    app = create_app()
    with app.state.session_factory() as session:
        now = store.current_time(session)
    count = seed_class(app.state.session_factory, app.state.content, now)
    print(json.dumps({"seeded_students": count}))


if __name__ == "__main__":
    main()
