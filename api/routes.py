import json
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sqlmodel import select

from agent.loop import decide_next, process_answer
from agent.plan import draft_lesson_plan
from api import store
from api.models import QuestionState, Student
from engine.class_summary import StudentView, build_class_summary
from engine.scheduling import concept_recall, displayed_mastery, is_due, misconception_recall
from engine.selection import DEFAULT_MASTERY
from engine.types import ConceptState, MisconceptionState, Question

router = APIRouter(prefix="/api")


class AnswerRequest(BaseModel):
    question_id: str
    option_id: str
    reasoning: str = Field(max_length=2000)
    confidence_tap: Literal["sure", "not_sure"]


class ClockRequest(BaseModel):
    days: int = Field(gt=0, le=3650)


def _student_or_404(session, student_id: str) -> Student:
    student = session.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail=f"Unknown student {student_id}")
    return student


def _public_question(question: Question, content) -> dict:
    return {
        "id": question.id,
        "concept_id": question.concept_id,
        "concept_name": content.concepts[question.concept_id].name,
        "stem": question.stem,
        "options": [{"id": option.id, "text": option.text} for option in question.options],
    }


def _next_payload(student: Student, content) -> dict:
    if student.served_question_id is None:
        return {"status": "caught_up", "question": None, "rule": 6, "reason": "Nothing needs practice right now.", "hypotheses": []}
    return {
        "status": "question",
        "question": _public_question(content.questions[student.served_question_id], content),
        "rule": student.served_rule,
        "reason": student.served_reason,
        "hypotheses": json.loads(student.served_hypotheses_json or "[]"),
    }


@router.get("/students")
def list_students(request: Request) -> list[dict]:
    with request.app.state.session_factory() as session:
        students = session.exec(select(Student).where(Student.is_simulated == False).order_by(Student.id)).all()  # noqa: E712
        return [{"id": s.id, "name": s.name, "diagnostic_complete": s.diagnostic_complete} for s in students]


@router.get("/graph")
def graph(request: Request) -> dict:
    content = request.app.state.content
    with_questions = {q.concept_id for q in content.questions.values()}
    return {
        "concepts": [
            {**concept.model_dump(), "has_questions": concept.id in with_questions}
            for concept in content.concepts.values()
        ]
    }


@router.get("/students/{student_id}/next")
def next_question(student_id: str, request: Request) -> dict:
    state = request.app.state
    content = state.content
    with state.session_factory() as session:
        student = _student_or_404(session, student_id)
        if student.served_question_id in content.questions:
            return _next_payload(student, content)
        snapshot = store.load_snapshot(session, student_id)
        now = store.current_time(session)
    selection, question = decide_next(snapshot, now, content, state.llm)
    with state.session_factory() as session:
        if question is not None and question.source == "generated":
            store.save_generated(session, question, content)
        store.store_served(session, student_id, selection)
        session.commit()
        return _next_payload(session.get(Student, student_id), content)


@router.post("/students/{student_id}/answers")
def submit_answer(student_id: str, body: AnswerRequest, request: Request) -> dict:
    state = request.app.state
    content = state.content
    with state.session_factory() as session:
        student = _student_or_404(session, student_id)
        if student.served_question_id != body.question_id or body.question_id not in content.questions:
            raise HTTPException(status_code=409, detail="This isn't the question currently set for this student.")
        question = content.questions[body.question_id]
        if body.option_id not in {option.id for option in question.options}:
            raise HTTPException(status_code=422, detail=f"Unknown option {body.option_id}")
        served = (student.served_rule, student.served_reason, student.served_hypotheses_json)
        if not store.claim_served_question(session, student_id, body.question_id):
            raise HTTPException(status_code=409, detail="This answer was already submitted.")
        snapshot = store.load_snapshot(session, student_id)
        now = store.current_time(session)

    try:
        outcome = process_answer(
            snapshot, question, body.option_id, body.reasoning, body.confidence_tap, now, content, state.llm
        )
        with state.session_factory() as session:
            store.save_applied(
                session,
                student_id,
                question,
                body.option_id,
                body.reasoning,
                body.confidence_tap,
                outcome.diagnosis_result.diagnosis.model_dump_json(),
                outcome.trace,
                outcome.applied,
                now,
            )
            if outcome.next_question is not None and outcome.next_question.source == "generated":
                store.save_generated(session, outcome.next_question, content)
            store.store_served(session, student_id, outcome.next_selection)
            session.commit()
    except Exception:
        with state.session_factory() as session:
            store.restore_served_question(session, student_id, body.question_id)
        raise

    diagnosis = outcome.diagnosis_result.diagnosis
    misconception = content.misconceptions.get(diagnosis.misconception_id) if diagnosis.misconception_id else None
    return {
        "correct": outcome.applied.correct,
        "correct_option_id": outcome.applied.correct_option_id,
        "diagnosis": {
            **diagnosis.model_dump(),
            "misconception_description": misconception.description if misconception else None,
        },
        "diagnosis_status": outcome.diagnosis_result.status,
        "mastery_changes": [
            {**change, "name": content.concepts[change["id"]].name} for change in outcome.applied.mastery_changes
        ],
        "misconception_changes": [
            {**change, "description": content.misconceptions[change["id"]].description}
            for change in outcome.applied.misconception_changes
        ],
        "trace": outcome.trace,
        "next_reason": outcome.next_selection.reason if outcome.next_selection else None,
        "caught_up": outcome.next_question is None,
    }


@router.get("/students/{student_id}/state")
def student_state(student_id: str, request: Request) -> dict:
    state = request.app.state
    content = state.content
    with state.session_factory() as session:
        _student_or_404(session, student_id)
        now = store.current_time(session)
        offset = store.offset_days(session)
        snapshot = store.load_snapshot(session, student_id)

    with_questions = {q.concept_id for q in content.questions.values()}
    concepts = []
    due = []
    for concept in content.concepts.values():
        concept_state = snapshot.concept_states.get(concept.id, ConceptState(concept.id))
        recall_value = concept_recall(concept_state, now)
        assessed = concept_state.last_practiced_at is not None
        concepts.append(
            {
                "id": concept.id,
                "name": concept.name,
                "chapter": concept.chapter,
                "prerequisites": concept.prerequisites,
                "mastery": concept_state.mastery if concept.id in snapshot.concept_states else DEFAULT_MASTERY,
                "displayed_mastery": displayed_mastery(concept_state.mastery, recall_value),
                "recall": recall_value,
                "assessed": assessed,
                "has_questions": concept.id in with_questions,
            }
        )
        if assessed and concept.id in with_questions and is_due(recall_value):
            due.append({"kind": "concept", "id": concept.id, "name": concept.name, "recall": recall_value})

    misconceptions = []
    for misconception_id, misconception_state in sorted(
        snapshot.misconception_states.items(), key=lambda item: -item[1].probability
    ):
        misconception_state: MisconceptionState
        misconception = content.misconceptions[misconception_id]
        misconceptions.append(
            {
                "id": misconception_id,
                "description": misconception.description,
                "probability": misconception_state.probability,
                "status": misconception_state.status,
            }
        )
        recall_value = misconception_recall(misconception_state, now)
        if misconception_state.status == "resolved" and is_due(recall_value):
            due.append({"kind": "misconception", "id": misconception_id, "name": misconception.description, "recall": recall_value})

    return {
        "concepts": concepts,
        "misconceptions": misconceptions,
        "due_reviews": due,
        "offset_days": offset,
        "answer_count": snapshot.answer_count,
        "diagnostic_complete": snapshot.diagnostic_complete,
    }


@router.post("/clock/advance")
def advance_clock(body: ClockRequest, request: Request) -> dict:
    with request.app.state.session_factory() as session:
        offset = store.offset_days(session) + body.days
        store.set_offset_days(session, offset)
        for student in session.exec(select(Student).where(Student.is_simulated == False)).all():  # noqa: E712
            store.clear_served(student)
            session.add(student)
        session.commit()
        return {"offset_days": offset}


@router.post("/clock/reset")
def reset_clock(request: Request) -> dict:
    with request.app.state.session_factory() as session:
        store.set_offset_days(session, 0)
        for student in session.exec(select(Student).where(Student.is_simulated == False)).all():  # noqa: E712
            store.clear_served(student)
            session.add(student)
        session.commit()
        return {"offset_days": 0}


@router.post("/demo/reset")
def reset_demo(request: Request) -> dict:
    with request.app.state.session_factory() as session:
        store.reset_demo(session)
    return {"status": "ok"}


def _class_summary(request: Request) -> dict:
    content = request.app.state.content
    with request.app.state.session_factory() as session:
        now = store.current_time(session)
        students = session.exec(
            select(Student).where(Student.is_simulated == True).order_by(Student.id)  # noqa: E712
        ).all()
        views = []
        for student in students:
            snapshot = store.load_snapshot(session, student.id)
            views.append(StudentView(student.id, student.name, snapshot.concept_states, snapshot.misconception_states))
        question_elo = {
            row.question_id: (row.difficulty_elo, row.attempts) for row in session.exec(select(QuestionState)).all()
        }
    return build_class_summary(views, content, question_elo, now)


@router.get("/class/summary")
def class_summary(request: Request) -> dict:
    return _class_summary(request)


@router.post("/class/plan")
def class_plan(request: Request) -> dict:
    state = request.app.state
    content = state.content
    groups = _class_summary(request)["groups"]
    if not groups:
        raise HTTPException(status_code=404, detail="No active misconception to plan for.")
    top = groups[0]
    student_count = len(top["students"])
    plan = draft_lesson_plan(top["misconception_id"], student_count, content, state.llm)
    if plan is None:
        raise HTTPException(status_code=503, detail="The lesson plan couldn't be drafted. Check that Ollama is running.")
    check_question = content.questions.get(plan.check_question_id)
    return {
        **plan.model_dump(),
        "check_question_stem": check_question.stem if check_question else "",
        "misconception_id": top["misconception_id"],
        "misconception_description": top["description"],
        "student_count": student_count,
    }
