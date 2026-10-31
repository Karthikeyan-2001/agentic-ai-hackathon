from dataclasses import dataclass
from datetime import datetime

from engine.elo import expected, starting_elo
from engine.graph import dependents_count
from engine.scheduling import concept_recall, is_due, misconception_recall
from engine.types import Concept, ConceptState, Misconception, MisconceptionState, Question

TARGET_SUCCESS = 0.6
HYPOTHESIS_AT = 0.2
SEPARATION_BONUS = 0.5
MASTERED_AT = 0.7
PREREQUISITE_MET_AT = 0.5
DEFAULT_MASTERY = 0.3


@dataclass
class SelectionContext:
    now: datetime
    pinned_question_id: str | None
    diagnostic_complete: bool
    concepts: dict[str, Concept]
    misconceptions: dict[str, Misconception]
    questions: dict[str, Question]
    concept_states: dict[str, ConceptState]
    misconception_states: dict[str, MisconceptionState]
    difficulty_elo: dict[str, float]
    ability_elo: float
    recent_question_ids: list[str]
    last_seen: dict[str, datetime]


@dataclass
class Selection:
    rule: int
    reason: str
    question_id: str | None
    concept_id: str | None
    hypotheses: list[tuple[str, float]]


def _mastery(ctx: SelectionContext, concept_id: str) -> float:
    state = ctx.concept_states.get(concept_id)
    return state.mastery if state else DEFAULT_MASTERY


def _available(ctx: SelectionContext) -> list[Question]:
    recent = set(ctx.recent_question_ids)
    return [q for q in ctx.questions.values() if q.id not in recent]


def _unseen(ctx: SelectionContext, concept_id: str) -> list[Question]:
    return [q for q in _available(ctx) if q.concept_id == concept_id and q.id not in ctx.last_seen]


def _success_gap(ctx: SelectionContext, question: Question) -> float:
    difficulty = ctx.difficulty_elo.get(question.id, starting_elo(question.difficulty_prior))
    return abs(expected(ctx.ability_elo, difficulty) - TARGET_SUCCESS)


def _best(ctx: SelectionContext, questions: list[Question]) -> Question:
    return min(questions, key=lambda q: (_success_gap(ctx, q), q.id))


def _hypotheses(ctx: SelectionContext) -> list[tuple[str, float]]:
    ranked = sorted(
        (
            (key, state.probability)
            for key, state in ctx.misconception_states.items()
            if state.probability >= HYPOTHESIS_AT
        ),
        key=lambda item: (-item[1], item[0]),
    )
    return ranked[:2]


def _name(ctx: SelectionContext, concept_id: str) -> str:
    concept = ctx.concepts.get(concept_id)
    return concept.name if concept else concept_id


def _for_concept(
    ctx: SelectionContext, rule: int, concept_id: str, reason: str, hypotheses: list[tuple[str, float]]
) -> Selection:
    unseen = _unseen(ctx, concept_id)
    question_id = _best(ctx, unseen).id if unseen else None
    return Selection(rule, reason, question_id, concept_id, hypotheses)


def _diagnostic(ctx: SelectionContext, hypotheses: list[tuple[str, float]]) -> Selection | None:
    with_unseen = {q.concept_id for q in _available(ctx) if q.id not in ctx.last_seen}
    with_available = {q.concept_id for q in _available(ctx)}
    candidates = with_unseen or with_available
    if not candidates:
        return None
    dependents = dependents_count(ctx.concepts)
    concept_id = min(
        candidates,
        key=lambda c: (abs(_mastery(ctx, c) - 0.5), -dependents.get(c, 0), c),
    )
    reason = f"Diagnostic: {_name(ctx, concept_id)} is the concept the tutor is least certain about."
    return _for_concept(ctx, 2, concept_id, reason, hypotheses)


def _separation_score(question: Question, hypotheses: list[tuple[str, float]]) -> float:
    score = 0.0
    option_sets = []
    for misconception_id, probability in hypotheses:
        options = {o.id for o in question.options if misconception_id in o.misconception_ids}
        if options:
            score += probability
            option_sets.append(options)
    if len(option_sets) == 2 and option_sets[0] != option_sets[1]:
        score += SEPARATION_BONUS
    return score


def _separating(ctx: SelectionContext, hypotheses: list[tuple[str, float]]) -> Selection | None:
    if not hypotheses:
        return None
    scored = [(_separation_score(q, hypotheses), q) for q in _available(ctx)]
    scored = [item for item in scored if item[0] > 0]
    if not scored:
        return None
    best = min(scored, key=lambda item: (-item[0], _success_gap(ctx, item[1]), item[1].id))[1]
    names = " and ".join(key for key, _ in hypotheses)
    reason = f"This question best tests the current explanations: {names}."
    return Selection(3, reason, best.id, best.concept_id, hypotheses)


def _review(ctx: SelectionContext, hypotheses: list[tuple[str, float]]) -> Selection | None:
    resolved = sorted(
        (
            (misconception_recall(state, ctx.now), key)
            for key, state in ctx.misconception_states.items()
            if state.status == "resolved" and is_due(misconception_recall(state, ctx.now))
        ),
    )
    for _, misconception_id in resolved:
        probing = [
            q for q in _available(ctx) if any(misconception_id in o.misconception_ids for o in q.options)
        ]
        if probing:
            unseen = [q for q in probing if q.id not in ctx.last_seen]
            choice = _best(ctx, unseen) if unseen else min(probing, key=lambda q: (ctx.last_seen[q.id], q.id))
            reason = f"Review: checking whether {misconception_id} has come back."
            return Selection(4, reason, choice.id, choice.concept_id, hypotheses)

    with_questions = {q.concept_id for q in ctx.questions.values()}
    due = sorted(
        (
            (concept_recall(state, ctx.now), key)
            for key, state in ctx.concept_states.items()
            if key in with_questions and is_due(concept_recall(state, ctx.now))
        ),
    )
    if due:
        concept_id = due[0][1]
        reason = f"Review: {_name(ctx, concept_id)} is due, because predicted recall has dropped."
        return _for_concept(ctx, 4, concept_id, reason, hypotheses)
    return None


def _weakest(ctx: SelectionContext, hypotheses: list[tuple[str, float]]) -> Selection | None:
    with_questions = {q.concept_id for q in ctx.questions.values()}
    candidates = [c for c in with_questions if _mastery(ctx, c) < MASTERED_AT]

    def prerequisites_met(concept_id: str) -> bool:
        concept = ctx.concepts.get(concept_id)
        prerequisites = concept.prerequisites if concept else []
        return all(
            _mastery(ctx, p) >= PREREQUISITE_MET_AT for p in prerequisites if p in with_questions
        )

    ready = [c for c in candidates if prerequisites_met(c)]
    if not ready:
        return None
    concept_id = min(ready, key=lambda c: (_mastery(ctx, c), c))
    reason = f"{_name(ctx, concept_id)} is the weakest concept the student is ready to practise."
    return _for_concept(ctx, 5, concept_id, reason, hypotheses)


def choose_next(ctx: SelectionContext) -> Selection | None:
    hypotheses = _hypotheses(ctx)
    if ctx.pinned_question_id:
        question = ctx.questions[ctx.pinned_question_id]
        return Selection(1, "This question was set for this student.", question.id, question.concept_id, hypotheses)
    if not ctx.diagnostic_complete:
        selection = _diagnostic(ctx, hypotheses)
        if selection:
            return selection
    return _separating(ctx, hypotheses) or _review(ctx, hypotheses) or _weakest(ctx, hypotheses)


def oldest_seen_question(ctx: SelectionContext, concept_id: str) -> str | None:
    seen = [q for q in ctx.questions.values() if q.concept_id == concept_id and q.id in ctx.last_seen]
    if not seen:
        return None
    return min(seen, key=lambda q: (ctx.last_seen[q.id], q.id)).id
