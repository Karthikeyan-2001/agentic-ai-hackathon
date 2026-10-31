import re
from pathlib import Path

import pytest

from agent.content import load_content

DEMO_MISCONCEPTIONS = {"current_consumed", "series_parallel_confusion", "identical_implies_equal"}


@pytest.fixture(scope="module")
def content():
    return load_content(Path("content"))


def test_counts(content):
    assert 25 <= len(content.concepts) <= 35
    assert len([c for c in content.concepts.values() if c.chapter == "Electricity"]) == 12
    assert len(content.misconceptions) == 8
    assert len([q for q in content.questions.values() if q.source == "seed"]) == 12


def test_demo_question_wrong_option_maps_to_both(content):
    question = content.questions["q_series_two_bulbs"]
    wrong = next(o for o in question.options if not o.is_correct and o.text == "0.25 A")
    assert set(wrong.misconception_ids) == {"current_consumed", "series_parallel_confusion"}
    assert next(o for o in question.options if o.is_correct).text == "0.5 A"


@pytest.mark.parametrize(
    "question_id,misconception_id",
    [
        ("q_current_in_out", "current_consumed"),
        ("q_series_vs_parallel", "series_parallel_confusion"),
        ("q_different_bulbs", "identical_implies_equal"),
    ],
)
def test_followups_probe_only_their_misconception(content, question_id, misconception_id):
    question = content.questions[question_id]
    assert {m for o in question.options for m in o.misconception_ids} == {misconception_id}


def test_every_misconception_has_a_question(content):
    probed = {m for q in content.questions.values() for o in q.options for m in o.misconception_ids}
    assert probed == set(content.misconceptions)


def test_no_other_question_has_options_for_two_demo_misconceptions(content):
    for question in content.questions.values():
        if question.id == "q_series_two_bulbs":
            continue
        probed = {m for o in question.options for m in o.misconception_ids}
        assert len(probed & DEMO_MISCONCEPTIONS) <= 1, question.id


def test_generated_adds_tags_equal_the_sum_of_the_resistances(content):
    for question in content.questions.values():
        if question.source != "generated":
            continue
        numbers = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", question.stem)]
        for option in question.options:
            if "parallel_resistance_adds" in option.misconception_ids:
                assert float(option.text.split()[0]) == sum(numbers), question.id
