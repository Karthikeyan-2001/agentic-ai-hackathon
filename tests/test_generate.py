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


def test_rejects_real_heater_failure_where_args_differ_from_stem():
    heater = good(
        stem="A heater rated at 2 kW is used for 3 hours. How much electrical energy does it consume?",
        function="energy",
        args=[2000, 3],
        options=[GeneratedOption(value=6000, misconception_id=None), GeneratedOption(value=6, misconception_id=None)],
    )
    assert "stem" in verify_generated(heater, "electric_energy", set())


def test_rejects_real_power_failure_where_args_differ_from_stem():
    power = good(
        stem="A resistor of 12 ohm carries a current of 0.32 A. What is the electric power?",
        function="power",
        args=[9.6, 0.32],
        options=[GeneratedOption(value=3.072, misconception_id=None), GeneratedOption(value=3.84, misconception_id=None)],
    )
    assert "stem" in verify_generated(power, "electric_power", set())


def test_rejects_swapped_argument_roles():
    swapped = good(
        args=[4, 12],
        options=[GeneratedOption(value=4 / 12, misconception_id=None), GeneratedOption(value=48, misconception_id=None)],
    )
    assert "stem" in verify_generated(swapped, "ohms_law", VALID)


def test_rejects_extra_number_in_stem():
    extra = good(stem="A 4 ohm resistor is across a 12 V supply for 9 seconds. What is the current?")
    assert "stem" in verify_generated(extra, "ohms_law", VALID)


def test_rejects_stem_asking_for_something_else():
    wrong_topic = good(stem="A 4 ohm resistor is across a 12 V supply. What is the power?")
    assert "stem" in verify_generated(wrong_topic, "ohms_law", VALID)


def test_accepts_ohm_symbol_and_full_unit_names():
    assert verify_generated(good(stem="A 4 Ω resistor is across a 12 volt supply. Find the current."), "ohms_law", VALID) is None


def test_accepts_power_from_voltage_and_resistance():
    question = good(
        stem="A 10 ohm resistor is connected to a 12 V battery. What is the power?",
        function="power_from_voltage_resistance",
        args=[12, 10],
        options=[GeneratedOption(value=14.4, misconception_id=None), GeneratedOption(value=120, misconception_id=None)],
    )
    assert verify_generated(question, "electric_power", set()) is None


def test_to_question_rounds_long_decimals():
    options = [GeneratedOption(value=1.90476, misconception_id=None), GeneratedOption(value=26, misconception_id=None)]
    question = to_question(
        good(function="parallel_resistance", args=[8, 15, 3], options=options), "g1", "parallel_resistance"
    )
    assert question.options[0].text == "1.9 ohm" and question.options[0].is_correct


def test_to_question_uses_code_owned_unit():
    question = to_question(good(unit="Amperes (A)"), "g1", "ohms_law")
    assert question.options[0].text == "3 A"


def test_assignment_is_repeatable_and_varies_by_question(content):
    prompts = {}

    def capture(s, u, schema):
        prompts.setdefault(u, 0)
        return good()

    llm = FakeLLM(capture)
    generate_question("ohms_law", "g1", content, llm)
    generate_question("ohms_law", "g1", content, llm)
    generate_question("ohms_law", "g2", content, llm)
    generate_question("ohms_law", "g3", content, llm)
    assert len(prompts) >= 2
    assert llm.calls[0][1] == llm.calls[1][1]
