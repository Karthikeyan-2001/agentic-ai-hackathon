from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from engine.elo import is_flagged, starting_elo
from engine.graph import root_prerequisite_below
from engine.scheduling import concept_recall, displayed_mastery, is_due
from engine.types import Concept, ConceptState, Misconception, MisconceptionState, Question

ASSESSED_CHAPTER = "Python Programming"
LOW_MASTERY = 0.5
GAP_THRESHOLD = 0.4


class SummaryContent(Protocol):
    concepts: dict[str, Concept]
    misconceptions: dict[str, Misconception]
    questions: dict[str, Question]


@dataclass
class StudentView:
    id: str
    name: str
    concept_states: dict[str, ConceptState]
    misconception_states: dict[str, MisconceptionState]


def _average(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _none_last(value: float | None) -> tuple[bool, float]:
    return (value is None, value if value is not None else 0.0)


def _displayed_by_concept(student: StudentView, concepts: list[Concept], now: datetime) -> dict[str, float | None]:
    displayed: dict[str, float | None] = {}
    for concept in concepts:
        state = student.concept_states.get(concept.id)
        if state is None or state.last_practiced_at is None:
            displayed[concept.id] = None
        else:
            displayed[concept.id] = displayed_mastery(state.mastery, concept_recall(state, now))
    return displayed


def _concept_gaps(concepts: list[Concept], rows: list[dict]) -> list[dict]:
    gaps = []
    for concept in concepts:
        values = [row["mastery"][concept.id] for row in rows if row["mastery"][concept.id] is not None]
        gaps.append(
            {
                "concept_id": concept.id,
                "name": concept.name,
                "average_mastery": _average(values),
                "below_40_count": sum(value < GAP_THRESHOLD for value in values),
                "assessed_count": len(values),
            }
        )
    return sorted(gaps, key=lambda gap: (*_none_last(gap["average_mastery"]), gap["concept_id"]))


def _heatmap(concepts: list[Concept], rows: list[dict], gaps: list[dict]) -> dict:
    """Weakest concepts and students come first, so the biggest gaps sit in the top-left corner."""
    names = {concept.id: concept.name for concept in concepts}

    def student_key(row: dict) -> tuple:
        values = [value for value in row["mastery"].values() if value is not None]
        return (*_none_last(_average(values)), row["id"])

    return {
        "concepts": [{"id": gap["concept_id"], "name": names[gap["concept_id"]]} for gap in gaps],
        "students": sorted(rows, key=student_key),
    }


def _groups(students: list[StudentView], content: SummaryContent) -> list[dict]:
    groups = []
    for misconception in content.misconceptions.values():
        members = [
            {"id": student.id, "name": student.name}
            for student in students
            if (state := student.misconception_states.get(misconception.id)) and state.status == "active"
        ]
        if members:
            groups.append(
                {"misconception_id": misconception.id, "description": misconception.description, "students": members}
            )
    return sorted(groups, key=lambda group: (-len(group["students"]), group["misconception_id"]))


def _root_causes(students: list[StudentView], concepts: list[Concept], content: SummaryContent) -> list[dict]:
    affected_students: dict[str, set[str]] = {}
    affected_concepts: dict[str, set[str]] = {}
    for student in students:
        # Only practised concepts count, so a never-assessed default can't be blamed.
        masteries = {
            key: state.mastery for key, state in student.concept_states.items() if state.last_practiced_at is not None
        }
        for concept in concepts:
            if masteries.get(concept.id, 1.0) >= LOW_MASTERY:
                continue
            root = root_prerequisite_below(concept.id, masteries, content.concepts, LOW_MASTERY)
            if root is not None:
                affected_students.setdefault(root, set()).add(student.id)
                affected_concepts.setdefault(root, set()).add(concept.name)
    causes = [
        {
            "concept_id": root,
            "name": content.concepts[root].name,
            "student_count": len(student_ids),
            "affects": sorted(affected_concepts[root]),
        }
        for root, student_ids in affected_students.items()
    ]
    return sorted(causes, key=lambda cause: (-cause["student_count"], cause["concept_id"]))


def _calibration_flags(question_elo: dict[str, tuple[float, int]], content: SummaryContent) -> list[dict]:
    flags = []
    for question_id, (current, attempts) in question_elo.items():
        question = content.questions.get(question_id)
        if question is None or not is_flagged(current, question.difficulty_prior, attempts):
            continue
        predicted = starting_elo(question.difficulty_prior)
        flags.append(
            {
                "question_id": question_id,
                "stem": question.stem,
                "predicted_elo": predicted,
                "current_elo": current,
                "attempts": attempts,
                "direction": "harder" if current > predicted else "easier",
            }
        )
    return sorted(flags, key=lambda flag: (-abs(flag["current_elo"] - flag["predicted_elo"]), flag["question_id"]))


def _reviews_by_concept(students: list[StudentView], content: SummaryContent, now: datetime) -> list[dict]:
    with_questions = {question.concept_id for question in content.questions.values()}
    counts: dict[str, int] = {}
    for student in students:
        for concept_id, state in student.concept_states.items():
            practised = state.last_practiced_at is not None
            if practised and concept_id in with_questions and is_due(concept_recall(state, now)):
                counts[concept_id] = counts.get(concept_id, 0) + 1
    reviews = [
        {"concept_id": concept_id, "name": content.concepts[concept_id].name, "student_count": count}
        for concept_id, count in counts.items()
    ]
    return sorted(reviews, key=lambda review: (-review["student_count"], review["concept_id"]))


def _overview(students: list[StudentView], rows: list[dict], reviews: list[dict]) -> dict:
    assessed = [value for row in rows for value in row["mastery"].values() if value is not None]
    with_active = sum(
        any(state.status == "active" for state in student.misconception_states.values()) for student in students
    )
    return {
        "student_count": len(students),
        "average_mastery": _average(assessed),
        "students_with_active_misconception": with_active,
        "reviews_due": sum(review["student_count"] for review in reviews),
    }


def build_class_summary(
    students: list[StudentView],
    content: SummaryContent,
    question_elo: dict[str, tuple[float, int]],
    now: datetime,
) -> dict:
    concepts = [concept for concept in content.concepts.values() if concept.chapter == ASSESSED_CHAPTER]
    rows = [
        {"id": student.id, "name": student.name, "mastery": _displayed_by_concept(student, concepts, now)}
        for student in students
    ]
    gaps = _concept_gaps(concepts, rows)
    reviews = _reviews_by_concept(students, content, now)
    return {
        "overview": _overview(students, rows, reviews),
        "concept_gaps": gaps,
        "reviews_by_concept": reviews,
        "heatmap": _heatmap(concepts, rows, gaps),
        "groups": _groups(students, content),
        "root_causes": _root_causes(students, concepts, content),
        "calibration_flags": _calibration_flags(question_elo, content),
        "student_count": len(students),
        "is_simulated": True,
    }
