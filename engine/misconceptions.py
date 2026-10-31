from dataclasses import replace
from datetime import datetime

from engine.types import ConfidenceTap, Diagnosis, MisconceptionState, Option, Question

ACTIVE_AT = 0.5
CANDIDATE_AT = 0.2
MIN_NAMED_CONFIDENCE = 0.6


def _status(state: MisconceptionState) -> str:
    if state.probability >= ACTIVE_AT:
        return "active"
    if state.was_active and state.probability < CANDIDATE_AT:
        return "resolved"
    if state.probability >= CANDIDATE_AT:
        return "candidate"
    return "inactive"


def _settle(state: MisconceptionState, now: datetime) -> None:
    if state.probability >= ACTIVE_AT:
        state.was_active = True
    status = _status(state)
    if status == "resolved" and state.status != "resolved":
        state.resolved_at = now
    state.status = status


def update_misconceptions(
    states: dict[str, MisconceptionState],
    diagnosis: Diagnosis,
    question: Question,
    option: Option,
    correct: bool,
    confidence_tap: ConfidenceTap,
    now: datetime,
) -> dict[str, MisconceptionState]:
    result = {key: replace(state) for key, state in states.items()}
    k = 1.0 if confidence_tap == "sure" else 0.6
    touched: set[str] = set()

    def state_for(misconception_id: str) -> MisconceptionState:
        touched.add(misconception_id)
        return result.setdefault(misconception_id, MisconceptionState(misconception_id))

    named = None
    if diagnosis.error_type == "misconception" and diagnosis.confidence >= MIN_NAMED_CONFIDENCE:
        named = diagnosis.misconception_id
    if named:
        state = state_for(named)
        state.probability += (1 - state.probability) * 0.7 * diagnosis.confidence * k

    for misconception_id in option.misconception_ids:
        if misconception_id != named:
            state = state_for(misconception_id)
            state.probability += (1 - state.probability) * 0.2 * k

    if correct and diagnosis.error_type == "none":
        probed = {m for each in question.options for m in each.misconception_ids}
        for misconception_id in probed:
            state = state_for(misconception_id)
            state.probability *= 0.5
            if state.status == "resolved":
                state.stability_days *= 2
                state.resolved_at = now

    for misconception_id in touched:
        _settle(result[misconception_id], now)
    return result
