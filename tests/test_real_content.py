import math
import re
from pathlib import Path

import pytest

from agent.content import load_content
from agent.solvers import SOLVERS

DEMO_MISCONCEPTIONS = {"range_includes_stop", "range_stop_is_count", "range_one_less_than_stop"}


@pytest.fixture(scope="module")
def content():
    return load_content(Path("content"))


def test_counts(content):
    assert 25 <= len(content.concepts) <= 35
    assert len([c for c in content.concepts.values() if c.chapter == "Python Programming"]) == 12
    assert len(content.misconceptions) == 8
    assert len([q for q in content.questions.values() if q.source == "seed"]) == 12


def test_demo_question_wrong_option_maps_to_both(content):
    question = content.questions["q_range_count"]
    wrong = next(o for o in question.options if not o.is_correct and o.text == "5 times")
    assert set(wrong.misconception_ids) == {"range_includes_stop", "range_stop_is_count"}
    assert next(o for o in question.options if o.is_correct).text == "4 times"


@pytest.mark.parametrize(
    "question_id,misconception_id",
    [
        ("q_range_last_value", "range_includes_stop"),
        ("q_range_two_bounds", "range_stop_is_count"),
        ("q_range_other_start", "range_one_less_than_stop"),
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
        if question.id == "q_range_count":
            continue
        probed = {m for o in question.options for m in o.misconception_ids}
        assert len(probed & DEMO_MISCONCEPTIONS) <= 1, question.id


def test_generated_rounds_tags_equal_the_rounded_quotient(content):
    for question in content.questions.values():
        if question.source != "generated":
            continue
        for option in question.options:
            if "integer_division_rounds" in option.misconception_ids:
                dividend, divisor = re.search(r"print\((\d+) // (\d+)\)", question.stem).groups()
                assert float(option.text) == math.floor(int(dividend) / int(divisor) + 0.5), question.id


def test_generated_answers_match_the_solver_for_their_program(content):
    for question in content.questions.values():
        if question.source != "generated":
            continue
        correct = next(o for o in question.options if o.is_correct)
        found = re.search(r"print\((\d+) (//|%|\*\*) (\d+)\)", question.stem)
        if found:
            function = {"//": "floor_div", "%": "modulo", "**": "power_of"}[found.group(2)]
            assert float(correct.text) == SOLVERS[function](int(found.group(1)), int(found.group(3))), question.id


def test_every_assessed_concept_is_in_the_python_chapter(content):
    with_questions = {q.concept_id for q in content.questions.values()}
    assert {content.concepts[c].chapter for c in with_questions} == {"Python Programming"}
