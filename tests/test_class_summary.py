from datetime import datetime, timedelta
from pathlib import Path

import pytest

from agent.content import load_content
from engine.class_summary import StudentView, build_class_summary
from engine.types import ConceptState, MisconceptionState

NOW = datetime(2026, 1, 15)


@pytest.fixture(scope="module")
def content():
    return load_content(Path("content"))


def practised(concept_id, mastery, days_ago=0, stability=100.0):
    return ConceptState(concept_id, mastery=mastery, stability_days=stability, last_practiced_at=NOW - timedelta(days=days_ago))


def student(id, concepts=(), misconceptions=()):
    return StudentView(
        id=id,
        name=f"Student {id}",
        concept_states={c.concept_id: c for c in concepts},
        misconception_states={m.misconception_id: m for m in misconceptions},
    )


def test_empty_class_returns_empty_lists(content):
    summary = build_class_summary([], content, {}, NOW)
    assert summary["student_count"] == 0
    assert summary["heatmap"]["students"] == []
    assert summary["groups"] == [] and summary["root_causes"] == [] and summary["calibration_flags"] == []
    assert summary["is_simulated"] is True


def test_heatmap_uses_displayed_mastery_for_electricity_concepts(content):
    state = ConceptState("ohms_law", mastery=0.8, stability_days=2, last_practiced_at=NOW - timedelta(days=2))
    summary = build_class_summary([student("1", [state])], content, {}, NOW)
    assert {c["id"] for c in summary["heatmap"]["concepts"]} == {
        c.id for c in content.concepts.values() if c.chapter == "Electricity"
    }
    cell = summary["heatmap"]["students"][0]["mastery"]
    assert cell["ohms_law"] == pytest.approx(0.5472, abs=0.001)
    assert cell["series_current"] is None


def test_groups_list_only_active_misconceptions(content):
    active = MisconceptionState("current_consumed", probability=0.7, status="active", was_active=True)
    candidate = MisconceptionState("voltage_is_current", probability=0.3, status="candidate")
    summary = build_class_summary(
        [student("1", misconceptions=[active, candidate]), student("2", misconceptions=[active])], content, {}, NOW
    )
    assert [g["misconception_id"] for g in summary["groups"]] == ["current_consumed"]
    assert [s["id"] for s in summary["groups"][0]["students"]] == ["1", "2"]
    assert summary["groups"][0]["description"]


def test_groups_sort_largest_first(content):
    a = MisconceptionState("voltage_is_current", probability=0.7, status="active", was_active=True)
    b = MisconceptionState("current_consumed", probability=0.7, status="active", was_active=True)
    summary = build_class_summary(
        [student("1", misconceptions=[a, b]), student("2", misconceptions=[b])], content, {}, NOW
    )
    assert [g["misconception_id"] for g in summary["groups"]] == ["current_consumed", "voltage_is_current"]


def test_root_cause_counts_each_student_once(content):
    # Two concepts share the same weak prerequisite, so the student counts once and both concepts are listed.
    weak = [practised("ohms_law", 0.2), practised("electric_power", 0.2), practised("resistance_factors", 0.3)]
    summary = build_class_summary([student("1", weak)], content, {}, NOW)
    root = next(r for r in summary["root_causes"] if r["concept_id"] == "ohms_law")
    assert root["student_count"] == 1
    assert set(root["affects"]) == {"Electric power", "Factors affecting resistance"}


def test_root_cause_ignores_concepts_never_practised(content):
    # electric_current has never been assessed, so its default mastery can't be blamed.
    summary = build_class_summary([student("1", [practised("series_current", 0.2)])], content, {}, NOW)
    assert summary["root_causes"] == []


def test_root_cause_sorts_by_student_count(content):
    first = student("1", [practised("ohms_law", 0.2), practised("electric_power", 0.2)])
    second = student("2", [practised("ohms_law", 0.2), practised("electric_power", 0.2)])
    third = student("3", [practised("series_current", 0.2), practised("parallel_current", 0.2)])
    summary = build_class_summary([first, second, third], content, {}, NOW)
    assert [r["student_count"] for r in summary["root_causes"]] == [2, 1]


def test_calibration_flag_uses_spec_threshold(content):
    question = content.questions["q_series_two_bulbs"]  # Prior 2 starts at 1350.
    elo = {
        question.id: (1500.0, 10),
        "q_ohm_basic": (1100.0, 10),  # Prior 1 starts at 1200, so a difference of 100 isn't flagged.
        "q_parallel_total": (1600.0, 9),  # Too few attempts.
    }
    flags = build_class_summary([], content, elo, NOW)["calibration_flags"]
    assert [f["question_id"] for f in flags] == [question.id]
    assert flags[0]["direction"] == "harder"
    assert flags[0]["predicted_elo"] == 1350 and flags[0]["current_elo"] == 1500


def test_calibration_flag_direction_easier(content):
    elo = {"q_series_two_bulbs": (1200.0, 12)}
    assert build_class_summary([], content, elo, NOW)["calibration_flags"][0]["direction"] == "easier"
