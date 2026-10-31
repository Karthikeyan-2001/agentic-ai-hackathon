from dataclasses import dataclass, replace
from datetime import datetime

from agent.content import Content
from agent.diagnose import DiagnosisResult, diagnose
from agent.generate import generate_question
from agent.llm import LLMClient
from agent.solvers import NUMERIC_CONCEPTS
from engine.elo import starting_elo, update_elo
from engine.graph import propagate
from engine.mastery import update_mastery
from engine.misconceptions import update_misconceptions
from engine.scheduling import update_stability
from engine.selection import DEFAULT_MASTERY, Selection, SelectionContext, choose_next, oldest_seen_question
from engine.types import ConceptState, ConfidenceTap, Diagnosis, MisconceptionState, Question

DIAGNOSTIC_LENGTH = 8
RECENT_LIMIT = 3


@dataclass
class LearnerSnapshot:
    ability_elo: float
    pinned_question_id: str | None
    diagnostic_complete: bool
    answer_count: int
    concept_states: dict[str, ConceptState]
    misconception_states: dict[str, MisconceptionState]
    difficulty_elo: dict[str, float]
    recent_question_ids: list[str]
    last_seen: dict[str, datetime]


@dataclass
class AppliedAnswer:
    snapshot: LearnerSnapshot
    correct: bool
    correct_option_id: str
    mastery_changes: list[dict]
    misconception_changes: list[dict]


@dataclass
class AnswerOutcome:
    applied: AppliedAnswer
    diagnosis_result: DiagnosisResult
    next_selection: Selection | None
    next_question: Question | None
    trace: list[dict]


def new_snapshot(
    content: Content,
    pinned_question_id: str | None = None,
    diagnostic_complete: bool = False,
    ability_elo: float = 1500.0,
) -> LearnerSnapshot:
    return LearnerSnapshot(
        ability_elo=ability_elo,
        pinned_question_id=pinned_question_id,
        diagnostic_complete=diagnostic_complete,
        answer_count=0,
        concept_states={},
        misconception_states={},
        difficulty_elo={q.id: starting_elo(q.difficulty_prior) for q in content.questions.values()},
        recent_question_ids=[],
        last_seen={},
    )


def _updated_concept_states(
    snapshot: LearnerSnapshot, question: Question, correct: bool, diagnosis: Diagnosis, now: datetime, content: Content
) -> tuple[dict[str, ConceptState], list[dict]]:
    states = {key: replace(state) for key, state in snapshot.concept_states.items()}
    concept_id = question.concept_id
    current = states.get(concept_id, ConceptState(concept_id))
    new_mastery = update_mastery(current.mastery, correct, diagnosis.error_type)
    states[concept_id] = replace(
        current,
        mastery=new_mastery,
        stability_days=update_stability(current.stability_days, correct, diagnosis.error_type),
        last_practiced_at=now,
    )

    masteries = {key: states[key].mastery if key in states else DEFAULT_MASTERY for key in content.concepts}
    propagated = propagate(masteries, concept_id, new_mastery - current.mastery, content.concepts)
    changes = [{"id": concept_id, "before": current.mastery, "after": new_mastery}]
    for key, value in propagated.items():
        if key != concept_id and value != masteries[key]:
            states[key] = replace(states.get(key, ConceptState(key)), mastery=value)
            changes.append({"id": key, "before": masteries[key], "after": value})
    return states, changes


def apply_answer(
    snapshot: LearnerSnapshot,
    question: Question,
    option_id: str,
    diagnosis: Diagnosis,
    confidence_tap: ConfidenceTap,
    now: datetime,
    content: Content,
) -> AppliedAnswer:
    option = next((o for o in question.options if o.id == option_id), None)
    if option is None:
        raise ValueError(f"Unknown option {option_id} for question {question.id}")
    correct = option.is_correct
    concept_states, mastery_changes = _updated_concept_states(snapshot, question, correct, diagnosis, now, content)

    misconception_states = update_misconceptions(
        snapshot.misconception_states, diagnosis, question, option, correct, confidence_tap, now
    )
    misconception_changes = []
    for key, state in misconception_states.items():
        before = snapshot.misconception_states.get(key, MisconceptionState(key)).probability
        if state.probability != before:
            misconception_changes.append({"id": key, "before": before, "after": state.probability})

    difficulty_elo = dict(snapshot.difficulty_elo)
    difficulty = difficulty_elo.get(question.id, starting_elo(question.difficulty_prior))
    ability_elo, difficulty_elo[question.id] = update_elo(snapshot.ability_elo, difficulty, correct)

    answer_count = snapshot.answer_count + 1
    new_snapshot_value = LearnerSnapshot(
        ability_elo=ability_elo,
        pinned_question_id=None if snapshot.pinned_question_id == question.id else snapshot.pinned_question_id,
        diagnostic_complete=snapshot.diagnostic_complete or answer_count >= DIAGNOSTIC_LENGTH,
        answer_count=answer_count,
        concept_states=concept_states,
        misconception_states=misconception_states,
        difficulty_elo=difficulty_elo,
        recent_question_ids=(snapshot.recent_question_ids + [question.id])[-RECENT_LIMIT:],
        last_seen={**snapshot.last_seen, question.id: now},
    )
    correct_option_id = next(o.id for o in question.options if o.is_correct)
    return AppliedAnswer(new_snapshot_value, correct, correct_option_id, mastery_changes, misconception_changes)


def _context(snapshot: LearnerSnapshot, now: datetime, content: Content) -> SelectionContext:
    return SelectionContext(
        now=now,
        pinned_question_id=snapshot.pinned_question_id,
        diagnostic_complete=snapshot.diagnostic_complete,
        concepts=content.concepts,
        misconceptions=content.misconceptions,
        questions=content.questions,
        concept_states=snapshot.concept_states,
        misconception_states=snapshot.misconception_states,
        difficulty_elo=snapshot.difficulty_elo,
        ability_elo=snapshot.ability_elo,
        recent_question_ids=snapshot.recent_question_ids,
        last_seen=snapshot.last_seen,
    )


def decide_next(
    snapshot: LearnerSnapshot, now: datetime, content: Content, llm: LLMClient
) -> tuple[Selection | None, Question | None]:
    ctx = _context(snapshot, now, content)
    selection = choose_next(ctx)
    if selection is None:
        return None, None
    if selection.question_id is not None:
        return selection, content.questions[selection.question_id]

    concept_id = selection.concept_id
    if concept_id in NUMERIC_CONCEPTS:
        question_id = f"g_live_{concept_id}_{len(content.questions) + 1}"
        generated = generate_question(concept_id, question_id, content, llm)
        if generated is not None:
            return replace(selection, question_id=generated.id), generated
    fallback = oldest_seen_question(ctx, concept_id)
    if fallback is None:
        return None, None
    return replace(selection, question_id=fallback), content.questions[fallback]


def process_answer(
    snapshot: LearnerSnapshot,
    question: Question,
    option_id: str,
    reasoning: str,
    confidence_tap: ConfidenceTap,
    now: datetime,
    content: Content,
    llm: LLMClient,
) -> AnswerOutcome:
    option = next((o for o in question.options if o.id == option_id), None)
    if option is None:
        raise ValueError(f"Unknown option {option_id} for question {question.id}")
    result = diagnose(question, option, option.is_correct, reasoning, content, llm)
    applied = apply_answer(snapshot, question, option_id, result.diagnosis, confidence_tap, now, content)
    selection, next_question = decide_next(applied.snapshot, now, content, llm)

    diagnosis = result.diagnosis
    raw = result.raw
    trace = [
        {
            "step": "check",
            "detail": f"The answer is {'correct' if applied.correct else 'wrong'}, marked by code.",
            "data": {"correct": applied.correct},
        },
        {
            "step": "diagnose",
            "detail": f"Diagnosis status: {result.status}.",
            "data": {"status": result.status, "raw": raw.model_dump() if raw else None},
        },
        {
            "step": "validate",
            "detail": f"Accepted as {diagnosis.error_type}" + (f": {diagnosis.misconception_id}." if diagnosis.misconception_id else "."),
            "data": diagnosis.model_dump(),
        },
        {
            "step": "update",
            "detail": f"Updated {len(applied.mastery_changes)} concepts and {len(applied.misconception_changes)} misconceptions.",
            "data": {"mastery": applied.mastery_changes, "misconceptions": applied.misconception_changes},
        },
        {
            "step": "decide",
            "detail": selection.reason if selection else "Nothing needs practice right now.",
            "data": {
                "rule": selection.rule if selection else 6,
                "question_id": selection.question_id if selection else None,
                "hypotheses": [list(item) for item in selection.hypotheses] if selection else [],
            },
        },
    ]
    return AnswerOutcome(applied, result, selection, next_question, trace)
