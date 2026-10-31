from engine.mastery import MAX_MASTERY, MIN_MASTERY
from engine.types import Concept

POSITIVE_WEIGHT = 0.3
NEGATIVE_WEIGHT = 0.1
MAX_LINKS = 2


def propagate(
    masteries: dict[str, float], concept_id: str, delta: float, concepts: dict[str, Concept]
) -> dict[str, float]:
    result = dict(masteries)
    weight = POSITIVE_WEIGHT if delta > 0 else NEGATIVE_WEIGHT
    seen = {concept_id}
    level = [concept_id]
    for link in range(1, MAX_LINKS + 1):
        next_level = []
        for current in level:
            for prerequisite in concepts[current].prerequisites:
                if prerequisite in seen:
                    continue
                seen.add(prerequisite)
                next_level.append(prerequisite)
                if prerequisite in result:
                    changed = result[prerequisite] + delta * weight**link
                    result[prerequisite] = min(MAX_MASTERY, max(MIN_MASTERY, changed))
        level = next_level
    return result


def _ancestors_with_depth(concept_id: str, concepts: dict[str, Concept]) -> dict[str, int]:
    depths: dict[str, int] = {}
    level = [concept_id]
    depth = 0
    while level:
        depth += 1
        next_level = []
        for current in level:
            for prerequisite in concepts[current].prerequisites:
                depths[prerequisite] = depth
                next_level.append(prerequisite)
        level = next_level
    return depths


def dependents_count(concepts: dict[str, Concept]) -> dict[str, int]:
    counts = {concept_id: 0 for concept_id in concepts}
    for concept_id in concepts:
        for ancestor in _ancestors_with_depth(concept_id, concepts):
            counts[ancestor] += 1
    return counts


def root_prerequisite_below(
    concept_id: str, masteries: dict[str, float], concepts: dict[str, Concept], threshold: float = 0.5
) -> str | None:
    below = [
        (depth, ancestor)
        for ancestor, depth in _ancestors_with_depth(concept_id, concepts).items()
        if masteries.get(ancestor, 1.0) < threshold
    ]
    if not below:
        return None
    return min(below, key=lambda item: (-item[0], item[1]))[1]
