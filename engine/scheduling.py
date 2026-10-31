import math
from datetime import datetime

from engine.types import ConceptState, ErrorType, MisconceptionState

DUE_BELOW = 0.85
MIN_STABILITY = 1.0
SECONDS_PER_DAY = 86400


def recall(days: float, stability: float) -> float:
    return math.exp(-days / stability)


def is_due(recall_value: float) -> bool:
    return recall_value < DUE_BELOW


def displayed_mastery(mastery: float, recall_value: float) -> float:
    return mastery * (0.5 + 0.5 * recall_value)


def update_stability(stability: float, correct: bool, error_type: ErrorType) -> float:
    if correct and error_type == "none":
        return stability * 2
    if error_type in ("slip", "unclear"):
        return stability
    return max(MIN_STABILITY, stability / 2)


def _days_between(earlier: datetime, later: datetime) -> float:
    return max(0.0, (later - earlier).total_seconds() / SECONDS_PER_DAY)


def concept_recall(state: ConceptState, now: datetime) -> float:
    if state.last_practiced_at is None:
        return 1.0
    return recall(_days_between(state.last_practiced_at, now), state.stability_days)


def misconception_recall(state: MisconceptionState, now: datetime) -> float:
    if state.status != "resolved" or state.resolved_at is None:
        return 1.0
    return recall(_days_between(state.resolved_at, now), state.stability_days)
