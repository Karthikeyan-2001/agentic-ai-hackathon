from engine.types import ErrorType

MIN_MASTERY = 0.01
MAX_MASTERY = 0.99


def _params(correct: bool, error_type: ErrorType) -> tuple[float, float, float]:
    """Return slip, guess and learn for an answer (spec section 7.1)."""
    if correct:
        if error_type == "none":
            return 0.1, 0.2, 0.1
        if error_type in ("misconception", "gap"):
            return 0.1, 0.9, 0.0
        return 0.1, 0.5, 0.0
    if error_type == "slip":
        return 0.6, 0.2, 0.0
    return 0.1, 0.2, 0.0


def update_mastery(p: float, correct: bool, error_type: ErrorType) -> float:
    slip, guess, learn = _params(correct, error_type)
    if correct:
        posterior = p * (1 - slip) / (p * (1 - slip) + (1 - p) * guess)
    else:
        posterior = p * slip / (p * slip + (1 - p) * (1 - guess))
    learned = posterior + (1 - posterior) * learn
    return min(MAX_MASTERY, max(MIN_MASTERY, learned))
