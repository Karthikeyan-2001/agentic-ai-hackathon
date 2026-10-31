from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from engine.elo import is_flagged, starting_elo
from engine.graph import root_prerequisite_below
from engine.scheduling import concept_recall, displayed_mastery
from engine.types import Concept, ConceptState, Misconception, MisconceptionState, Question

ELECTRICITY = "Electricity"
LOW_MASTERY = 0.5


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


def _heatmap(students: list[StudentView], concepts: list[Concept], now: datetime) -> dict:
    rows = []
    for student in students:
        mastery: dict[str, float | None] = {}
        for concept in concepts:
            state = student.concept_states.get(concept.id)
            if state is None or state.last_practiced_at is None:
                mastery[concept.id] = None
            else:
                mastery[concept.id] = displayed_mastery(state.mastery, concept_recall(state, now))
        rows.append({"id": student.id, "name": student.name, "mastery": mastery})
    return {"concepts": [{"id": c.id, "name": c.name} for c in concepts], "students": rows}


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


def build_class_summary(
    students: list[StudentView],
    content: SummaryContent,
    question_elo: dict[str, tuple[float, int]],
    now: datetime,
) -> dict:
    concepts = [concept for concept in content.concepts.values() if concept.chapter == ELECTRICITY]
    return {
        "heatmap": _heatmap(students, concepts, now),
        "groups": _groups(students, content),
        "root_causes": _root_causes(students, concepts, content),
        "calibration_flags": _calibration_flags(question_elo, content),
        "student_count": len(students),
        "is_simulated": True,
    }
