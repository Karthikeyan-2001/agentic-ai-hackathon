from pathlib import Path

import pytest

from agent.content import load_content
from agent.generate import (
    GeneratedOption,
    GeneratedQuestion,
    _assignment,
    generate_question,
    to_question,
    verify_generated,
)
from agent.solvers import NUMERIC_CONCEPTS, SOLVERS
from tests.fakes import FailingLLM, FakeLLM

VALID = {"integer_division_rounds"}


def good(**overrides):
    values = dict(
        stem="What does this program print?",
        function="floor_div",
        args=[19, 4],
        options=[
            GeneratedOption(value=4, misconception_id=None),
            GeneratedOption(value=4.75, misconception_id=None),
            GeneratedOption(value=5, misconception_id="integer_division_rounds"),
        ],
        difficulty_prior=2,
    )
    values.update(overrides)
    return GeneratedQuestion(**values)


@pytest.fixture(scope="module")
def content():
    return load_content(Path("content"))


def test_verify_accepts_good_question():
    assert verify_generated(good(), "arithmetic_operators", VALID) is None


def test_verify_rejects_unknown_function():
    assert "function" in verify_generated(good(function="delete_files"), "arithmetic_operators", VALID)


def test_verify_rejects_function_not_allowed_for_concept():
    assert "function" in verify_generated(good(function="range_sum"), "arithmetic_operators", VALID)


def test_verify_rejects_wrong_arg_count():
    assert "argument" in verify_generated(good(args=[19]), "arithmetic_operators", VALID)


def test_verify_rejects_division_by_zero():
    assert "argument" in verify_generated(good(args=[19, 0]), "arithmetic_operators", VALID)


def test_verify_rejects_decimal_arguments():
    assert "whole" in verify_generated(good(args=[19.5, 4]), "arithmetic_operators", VALID)


def test_verify_rejects_oversized_arguments():
    assert "argument" in verify_generated(good(args=[1000000, 4]), "arithmetic_operators", VALID)


def test_verify_rejects_empty_range():
    question = good(
        function="range_sum",
        args=[6, 2],
        options=[GeneratedOption(value=0, misconception_id=None), GeneratedOption(value=14, misconception_id=None)],
    )
    assert "range" in verify_generated(question, "running_total", set())


def test_verify_rejects_no_matching_option():
    options = [GeneratedOption(value=48, misconception_id=None), GeneratedOption(value=5, misconception_id=None)]
    assert "correct" in verify_generated(good(options=options), "arithmetic_operators", VALID)


def test_verify_rejects_an_option_that_is_only_close_to_the_answer():
    question = good(
        function="range_sum",
        args=[1, 50],
        options=[GeneratedOption(value=1224, misconception_id=None), GeneratedOption(value=2, misconception_id=None)],
    )
    assert "correct" in verify_generated(question, "running_total", set())


def test_verify_accepts_a_correct_answer_of_zero():
    question = good(
        function="modulo",
        args=[12, 4],
        options=[GeneratedOption(value=0, misconception_id=None), GeneratedOption(value=3, misconception_id=None)],
    )
    assert verify_generated(question, "arithmetic_operators", VALID) is None


def test_verify_rejects_duplicate_values():
    options = [
        GeneratedOption(value=4, misconception_id=None),
        GeneratedOption(value=5, misconception_id=None),
        GeneratedOption(value=5, misconception_id=None),
    ]
    assert "different" in verify_generated(good(options=options), "arithmetic_operators", VALID)


def test_verify_rejects_unknown_misconception():
    options = [GeneratedOption(value=4, misconception_id=None), GeneratedOption(value=5, misconception_id="ghost")]
    assert "ghost" in verify_generated(good(options=options), "arithmetic_operators", VALID)


def test_verify_rejects_misconception_on_correct_option():
    options = [
        GeneratedOption(value=4, misconception_id="integer_division_rounds"),
        GeneratedOption(value=5, misconception_id=None),
    ]
    assert "correct" in verify_generated(good(options=options), "arithmetic_operators", VALID)


def test_verify_rejects_too_few_options():
    options = [GeneratedOption(value=4, misconception_id=None)]
    assert "options" in verify_generated(good(options=options), "arithmetic_operators", VALID)


def test_verify_rejects_bad_difficulty():
    assert "difficulty" in verify_generated(good(difficulty_prior=9), "arithmetic_operators", VALID)


def test_verify_rejects_digits_in_the_stem():
    # The program holds the numbers, so a number in the wording could contradict it.
    assert "stem" in verify_generated(good(stem="What does this print for 20 // 4?"), "arithmetic_operators", VALID)


def test_verify_rejects_stem_asking_for_something_else():
    assert "stem" in verify_generated(good(stem="Why is Python popular?"), "arithmetic_operators", VALID)


def test_verify_rejects_print_wording_for_star_counts():
    # The program prints stars, so "what does it print?" doesn't have a number as its answer.
    options = [GeneratedOption(value=6, misconception_id=None), GeneratedOption(value=5, misconception_id=None)]
    question = good(function="nested_count", args=[2, 3], options=options)
    assert "how many" in verify_generated(question, "nested_loops", set())


def test_verify_accepts_how_many_wording_for_star_counts():
    options = [GeneratedOption(value=6, misconception_id=None), GeneratedOption(value=5, misconception_id=None)]
    question = good(stem="How many stars does this program print?", function="nested_count", args=[2, 3], options=options)
    assert verify_generated(question, "nested_loops", set()) is None


def test_to_question_marks_computed_answer_correct():
    question = to_question(good(), "g_arithmetic_operators_1", "arithmetic_operators")
    correct = [o for o in question.options if o.is_correct]
    assert [o.text for o in correct] == ["4"]
    assert question.source == "generated" and question.id == "g_arithmetic_operators_1"
    tags = {o.text: o.misconception_ids for o in question.options}
    assert tags["5"] == ["integer_division_rounds"]
    assert tags["4.75"] == []
    assert [o.id for o in question.options] == ["a", "b", "c"]


def test_to_question_moves_the_correct_option_around():
    positions = {
        [o.is_correct for o in to_question(good(), f"g{number}", "arithmetic_operators").options].index(True)
        for number in range(20)
    }
    assert positions == {0, 1, 2}


def test_to_question_order_is_repeatable_for_one_question():
    first = to_question(good(), "g1", "arithmetic_operators")
    assert first == to_question(good(), "g1", "arithmetic_operators")


def test_to_question_adds_the_program_from_code():
    question = to_question(good(), "g1", "arithmetic_operators")
    assert question.stem == "What does this program print?\n\nprint(19 // 4)"


def test_to_question_rounds_long_decimals():
    options = [GeneratedOption(value=4, misconception_id=None), GeneratedOption(value=4.7512, misconception_id=None)]
    question = to_question(good(options=options), "g1", "arithmetic_operators")
    assert {o.text for o in question.options} == {"4", "4.75"}


def test_generate_retries_after_rejection(content):
    replies = [good(args=[19, 0]), good()]
    llm = FakeLLM(lambda s, u, schema: replies.pop(0))
    question = generate_question("arithmetic_operators", "g1", content, llm)
    assert question.id == "g1" and len(llm.calls) == 2


def test_generate_returns_none_after_three_failures(content):
    llm = FakeLLM(lambda s, u, schema: good(function="ghost"))
    assert generate_question("arithmetic_operators", "g1", content, llm) is None
    assert len(llm.calls) == 3


def test_generate_returns_none_on_llm_error(content):
    assert generate_question("arithmetic_operators", "g1", content, FailingLLM()) is None


def test_generate_returns_none_for_non_numeric_concept(content):
    llm = FakeLLM(lambda s, u, schema: good())
    assert generate_question("for_range", "g1", content, llm) is None
    assert llm.calls == []


def test_prompt_offers_only_the_concepts_misconceptions(content):
    llm = FakeLLM(lambda s, u, schema: good())
    generate_question("arithmetic_operators", "g1", content, llm)
    system, user, _ = llm.calls[0]
    assert "integer_division_rounds" in system + user
    assert "range_includes_stop" not in system + user


def test_prompt_says_to_use_null_when_a_concept_has_no_misconceptions(content):
    llm = FakeLLM(lambda s, u, schema: good())
    generate_question("running_total", "g1", content, llm)
    _, user, _ = llm.calls[0]
    assert "Use null for every misconception ID" in user


def test_assignment_is_repeatable_and_varies_by_question(content):
    prompts = {}

    def capture(s, u, schema):
        prompts.setdefault(u, 0)
        return good()

    llm = FakeLLM(capture)
    generate_question("arithmetic_operators", "g1", content, llm)
    generate_question("arithmetic_operators", "g1", content, llm)
    generate_question("arithmetic_operators", "g2", content, llm)
    generate_question("arithmetic_operators", "g3", content, llm)
    assert len(prompts) >= 2
    assert llm.calls[0][1] == llm.calls[1][1]


def test_assigned_arguments_pass_the_checks():
    for concept_id in NUMERIC_CONCEPTS:
        for number in range(30):
            function, args = _assignment(concept_id, f"g{number}")
            options = [
                GeneratedOption(value=SOLVERS[function](*args), misconception_id=None),
                GeneratedOption(value=-1, misconception_id=None),
            ]
            stem = "How many stars does this program print?"
            question = good(stem=stem, function=function, args=args, options=options)
            assert verify_generated(question, concept_id, set()) is None


def test_verify_rejects_rounds_tag_that_is_not_the_rounded_quotient():
    options = [
        GeneratedOption(value=4, misconception_id=None),
        GeneratedOption(value=6, misconception_id="integer_division_rounds"),
    ]
    assert "rounded" in verify_generated(good(options=options), "arithmetic_operators", VALID)


def test_verify_accepts_rounds_tag_on_the_rounded_quotient():
    options = [
        GeneratedOption(value=4, misconception_id=None),
        GeneratedOption(value=5, misconception_id="integer_division_rounds"),
    ]
    assert verify_generated(good(options=options), "arithmetic_operators", VALID) is None


def test_verify_rejects_rounds_tag_on_other_operators():
    question = good(
        function="modulo",
        args=[19, 4],
        options=[
            GeneratedOption(value=3, misconception_id=None),
            GeneratedOption(value=5, misconception_id="integer_division_rounds"),
        ],
    )
    assert "rounded" in verify_generated(question, "arithmetic_operators", VALID)
