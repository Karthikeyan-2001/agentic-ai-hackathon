from pathlib import Path

import pytest

from agent.content import load_content
from agent.generate import GeneratedOption, GeneratedQuestion, generate_question, to_question, verify_generated
from tests.fakes import FailingLLM, FakeLLM

VALID = {"battery_constant_current"}


def good(**overrides):
    values = dict(
        stem="A 4 ohm resistor is across a 12 V supply. What is the current?",
        function="ohm_current",
        args=[12, 4],
        unit="A",
        options=[
            GeneratedOption(value=3, misconception_id=None),
            GeneratedOption(value=48, misconception_id=None),
            GeneratedOption(value=0.33, misconception_id="battery_constant_current"),
        ],
        difficulty_prior=2,
    )
    values.update(overrides)
    return GeneratedQuestion(**values)


@pytest.fixture(scope="module")
def content():
    return load_content(Path("content"))


def test_verify_accepts_good_question():
    assert verify_generated(good(), "ohms_law", VALID) is None


def test_verify_rejects_unknown_function():
    assert "function" in verify_generated(good(function="delete_files"), "ohms_law", VALID)


def test_verify_rejects_function_not_allowed_for_concept():
    assert "function" in verify_generated(good(function="power"), "ohms_law", VALID)


def test_verify_rejects_wrong_arg_count():
    assert "argument" in verify_generated(good(args=[12]), "ohms_law", VALID)


def test_verify_rejects_division_by_zero():
    assert "argument" in verify_generated(good(args=[12, 0]), "ohms_law", VALID)


def test_verify_rejects_no_matching_option():
    options = [GeneratedOption(value=48, misconception_id=None), GeneratedOption(value=5, misconception_id=None)]
    assert "correct" in verify_generated(good(options=options), "ohms_law", VALID)


def test_verify_rejects_two_matching_options():
    options = [GeneratedOption(value=3, misconception_id=None), GeneratedOption(value=3.01, misconception_id=None)]
    assert "correct" in verify_generated(good(options=options), "ohms_law", VALID)


def test_verify_rejects_duplicate_values():
    options = [
        GeneratedOption(value=3, misconception_id=None),
        GeneratedOption(value=5, misconception_id=None),
        GeneratedOption(value=5, misconception_id=None),
    ]
    assert "different" in verify_generated(good(options=options), "ohms_law", VALID)


def test_verify_rejects_unknown_misconception():
    options = [GeneratedOption(value=3, misconception_id=None), GeneratedOption(value=5, misconception_id="ghost")]
    assert "ghost" in verify_generated(good(options=options), "ohms_law", VALID)


def test_verify_rejects_misconception_on_correct_option():
    options = [
        GeneratedOption(value=3, misconception_id="battery_constant_current"),
        GeneratedOption(value=5, misconception_id=None),
    ]
    assert "correct" in verify_generated(good(options=options), "ohms_law", VALID)


def test_verify_rejects_too_few_options():
    assert "options" in verify_generated(good(options=[GeneratedOption(value=3, misconception_id=None)]), "ohms_law", VALID)


def test_verify_rejects_bad_difficulty():
    assert "difficulty" in verify_generated(good(difficulty_prior=9), "ohms_law", VALID)


def test_to_question_marks_computed_answer_correct():
    question = to_question(good(), "g_ohms_law_1", "ohms_law")
    correct = [o for o in question.options if o.is_correct]
    assert [o.text for o in correct] == ["3 A"]
    assert question.source == "generated" and question.id == "g_ohms_law_1"
    assert question.options[2].misconception_ids == ["battery_constant_current"]
    assert question.options[1].misconception_ids == []
    assert [o.id for o in question.options] == ["a", "b", "c"]


def test_generate_retries_after_rejection(content):
    replies = [good(args=[12, 0]), good()]
    llm = FakeLLM(lambda s, u, schema: replies.pop(0))
    question = generate_question("ohms_law", "g1", content, llm)
    assert question.id == "g1" and len(llm.calls) == 2


def test_generate_returns_none_after_three_failures(content):
    llm = FakeLLM(lambda s, u, schema: good(function="ghost"))
    assert generate_question("ohms_law", "g1", content, llm) is None
    assert len(llm.calls) == 3


def test_generate_returns_none_on_llm_error(content):
    assert generate_question("ohms_law", "g1", content, FailingLLM()) is None


def test_generate_returns_none_for_non_numeric_concept(content):
    llm = FakeLLM(lambda s, u, schema: good())
    assert generate_question("series_current", "g1", content, llm) is None
    assert llm.calls == []


def test_prompt_offers_only_the_concepts_misconceptions(content):
    llm = FakeLLM(lambda s, u, schema: good())
    generate_question("ohms_law", "g1", content, llm)
    system, user, _ = llm.calls[0]
    assert "battery_constant_current" in system + user
    assert "current_consumed" not in system + user
