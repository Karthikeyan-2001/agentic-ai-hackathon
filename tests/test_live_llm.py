from pathlib import Path

import pytest

from agent.content import load_content
from agent.diagnose import diagnose
from agent.llm import OllamaClient

pytestmark = pytest.mark.llm


@pytest.mark.parametrize(
    "option_text,reasoning,expected_type,expected_misconception",
    [
        ("0.25 A", "The first bulb used up half", "misconception", "current_consumed"),
        ("0.25 A", "The current splits between them", "misconception", "series_parallel_confusion"),
        ("0.5 A", "The bulbs are identical", "misconception", "identical_implies_equal"),
        ("0.5 A", "A series circuit has one path, so the current is the same everywhere", "none", None),
    ],
)
def test_demo_cases_on_real_model(option_text, reasoning, expected_type, expected_misconception):
    content = load_content(Path("content"))
    question = content.questions["q_series_two_bulbs"]
    option = next(o for o in question.options if o.text == option_text)
    result = diagnose(question, option, option.is_correct, reasoning, content, OllamaClient())
    assert result.status == "ok"
    assert result.diagnosis.error_type == expected_type, result.raw
    assert result.diagnosis.misconception_id == expected_misconception, result.raw
