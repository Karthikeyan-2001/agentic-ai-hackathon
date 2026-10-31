from pathlib import Path

import pytest

from agent.content import load_content, load_demo_script
from agent.diagnose import diagnose
from agent.llm import OllamaClient

pytestmark = pytest.mark.llm


@pytest.mark.parametrize(
    "option_text,reasoning,expected_type,expected_misconception",
    [
        ("5 times", "It counts up to and including 5", "misconception", "range_includes_stop"),
        ("5 times", "The 5 says how many times", "misconception", "range_stop_is_count"),
        ("4 times", "It is always one less than the stop number", "misconception", "range_one_less_than_stop"),
        ("4 times", "It starts at 1 and stops before 5, so it runs for 1, 2, 3 and 4", "none", None),
    ],
)
def test_demo_cases_on_real_model(option_text, reasoning, expected_type, expected_misconception):
    content = load_content(Path("content"))
    question = content.questions["q_range_count"]
    option = next(o for o in question.options if o.text == option_text)
    result = diagnose(question, option, option.is_correct, reasoning, content, OllamaClient())
    assert result.status == "ok"
    assert result.diagnosis.error_type == expected_type, result.raw
    assert result.diagnosis.misconception_id == expected_misconception, result.raw


DEMO_ANSWERS = [
    answer
    for step in load_demo_script(Path("content"), load_content(Path("content")))
    for answer in step.answers
]


@pytest.mark.parametrize("answer", DEMO_ANSWERS, ids=lambda answer: answer.question_id)
def test_demo_script_answers_on_real_model(answer):
    content = load_content(Path("content"))
    question = content.questions[answer.question_id]
    option = next(o for o in question.options if o.text == answer.option)
    result = diagnose(question, option, option.is_correct, answer.reasoning, content, OllamaClient())
    assert result.diagnosis.error_type == answer.expect_error_type, result.raw
    assert result.diagnosis.misconception_id == answer.expect_misconception_id, result.raw
