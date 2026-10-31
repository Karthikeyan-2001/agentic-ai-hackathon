from pathlib import Path

import pytest

from agent.content import load_content
from agent.plan import LessonPlan, draft_lesson_plan
from tests.fakes import FailingLLM, FakeLLM


@pytest.fixture(scope="module")
def content():
    return load_content(Path("content"))


def plan(check="q_current_in_out"):
    return LessonPlan(title="Current is not used up", board_demo="Two ammeters", check_question_id=check)


def test_plan_keeps_a_valid_check_question(content):
    result = draft_lesson_plan("current_consumed", 12, content, FakeLLM(lambda s, u, schema: plan()))
    assert result == plan()


def test_plan_replaces_unknown_check_question_with_one_that_probes_the_misconception(content):
    result = draft_lesson_plan("current_consumed", 12, content, FakeLLM(lambda s, u, schema: plan("ghost")))
    probed = {m for o in content.questions[result.check_question_id].options for m in o.misconception_ids}
    assert "current_consumed" in probed


def test_plan_prompt_names_misconception_and_student_count(content):
    llm = FakeLLM(lambda s, u, schema: plan())
    draft_lesson_plan("current_consumed", 12, content, llm)
    _, user, _ = llm.calls[0]
    assert "uses up current" in user and "12" in user


def test_plan_returns_none_on_llm_error(content):
    assert draft_lesson_plan("current_consumed", 12, content, FailingLLM()) is None
