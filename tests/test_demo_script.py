import json
from pathlib import Path

import pytest
from tests.helpers import DemoClient

from agent.content import ContentError, load_content, load_demo_script
from agent.plan import LessonPlan
from api import store
from api.auth import DEMO_ACCOUNTS
from api.main import create_app
from scripts.seed_class import seed_class
from scripts.warm_demo import play_step, warm_demo
from tests.fakes import FakeLLM

CONTENT = Path("content")
SCRIPT = load_demo_script(CONTENT, load_content(CONTENT))
EXPECTED = {answer.reasoning: answer for step in SCRIPT for answer in step.answers}


def responder(system, user, schema):
    if schema is LessonPlan:
        return LessonPlan(title="T", board_demo="D", check_question_id="q_range_last_value")
    reasoning = user.split("<student_reasoning>\n")[1].split("\n</student_reasoning>")[0]
    answer = EXPECTED[reasoning]
    return schema(
        error_type=answer.expect_error_type,
        misconception_id=answer.expect_misconception_id,
        first_wrong_step=None,
        evidence_quote=reasoning if answer.expect_misconception_id else None,
        confidence=0.9,
    )


@pytest.fixture
def client(tmp_path):
    app = create_app(db_url=f"sqlite:///{tmp_path}/demo.db", llm=FakeLLM(responder), content_dir=CONTENT)
    with app.state.session_factory() as session:
        now = store.current_time(session)
    seed_class(app.state.session_factory, app.state.content, now)
    with DemoClient(app) as test_client:
        yield test_client


def step_named(step_id):
    return next(step for step in SCRIPT if step.id == step_id)


def test_script_visits_every_part_of_the_brief_in_order():
    assert [step.id for step in SCRIPT] == [
        "student_a",
        "student_b",
        "student_c",
        "student_d_diagnostic",
        "student_d_targeted",
        "teacher_jump",
        "student_c_review",
        "teacher_dashboard",
        "close",
    ]


def test_script_uses_real_accounts():
    usernames = {account.username for account in DEMO_ACCOUNTS}
    assert all(step.account in usernames for step in SCRIPT if step.account is not None)


def test_every_scripted_answer_matches_the_question_the_tutor_serves(client):
    for step in SCRIPT:
        play_step(client, step)


def test_same_wrong_answer_gets_different_diagnoses():
    first, second = step_named("student_a").answers[0], step_named("student_b").answers[0]
    assert (first.question_id, first.option) == (second.question_id, second.option)
    assert first.expect_misconception_id != second.expect_misconception_id


def test_diagnostic_takes_eight_answers_then_serves_a_generated_question_on_the_weakest_concept(client):
    for step in SCRIPT[:3]:
        play_step(client, step)
    diagnostic = step_named("student_d_diagnostic")
    assert len(diagnostic.answers) == 8
    play_step(client, diagnostic)

    state = client.get("/api/students/D/state").json()
    assert state["diagnostic_complete"] is True and state["answer_count"] == 8
    served = client.get("/api/students/D/next").json()
    assert served["rule"] == 5 and "weakest" in served["reason"]
    assert served["question"]["source"] == "generated"
    assert served["question"]["concept_id"] == "list_traversal"
    assert served["question"]["id"] == step_named("student_d_targeted").answers[0].question_id


def test_jump_brings_a_spaced_review_for_student_c(client):
    for step in SCRIPT[:6]:
        play_step(client, step)
    state = client.get("/api/students/C/state").json()
    assert any(review["id"] == "for_range" for review in state["due_reviews"])
    served = client.get("/api/students/C/next").json()
    assert served["rule"] == 4 and served["question"]["concept_id"] == "for_range"


def test_warm_demo_stops_when_a_scripted_question_is_not_served(client):
    step = step_named("student_b").model_copy(deep=True)
    step.answers[0].question_id = "q_list_index"
    with pytest.raises(RuntimeError, match="q_list_index"):
        play_step(client, step)


def test_warm_demo_stops_when_a_diagnosis_differs_from_the_script(client):
    step = step_named("student_a").model_copy(deep=True)
    step.answers[0].expect_misconception_id = "range_stop_is_count"
    with pytest.raises(RuntimeError, match="range_stop_is_count"):
        play_step(client, step)


def test_warm_demo_leaves_everyone_reset(client):
    warm_demo(client)
    assert client.get("/api/students/A/next").json()["question"]["id"] == "q_range_count"
    state = client.get("/api/students/D/state").json()
    assert state["answer_count"] == 0 and state["offset_days"] == 0


def test_script_route_needs_no_sign_in(client):
    response = client.get("/api/auth/demo-script")
    assert response.status_code == 200
    assert [step["id"] for step in response.json()["steps"]][0] == "student_a"


def test_script_route_is_empty_when_there_is_no_script_file(tmp_path):
    source = tmp_path / "content"
    source.mkdir()
    for name in ["concepts.json", "misconceptions.json", "questions.json"]:
        (source / name).write_text((CONTENT / name).read_text(encoding="utf-8"), encoding="utf-8")
    app = create_app(db_url=f"sqlite:///{tmp_path}/none.db", llm=FakeLLM(responder), content_dir=source)
    with DemoClient(app) as test_client:
        assert test_client.get("/api/auth/demo-script").json() == {"steps": []}


def _write_script(path, answer):
    path.write_text(
        json.dumps({"steps": [{"id": "s", "title": "T", "note": "N", "account": "student.a", "answers": [answer]}]}),
        encoding="utf-8",
    )


def test_loader_rejects_an_unknown_question(tmp_path):
    _write_script(
        tmp_path / "demo_script.json",
        {"question_id": "ghost", "option": "5 times", "reasoning": "R", "confidence": "sure", "expect_error_type": "none"},
    )
    with pytest.raises(ContentError, match="ghost"):
        load_demo_script(tmp_path, load_content(CONTENT))


def test_loader_rejects_an_unknown_option(tmp_path):
    _write_script(
        tmp_path / "demo_script.json",
        {"question_id": "q_range_count", "option": "99 times", "reasoning": "R", "confidence": "sure", "expect_error_type": "none"},
    )
    with pytest.raises(ContentError, match="99 times"):
        load_demo_script(tmp_path, load_content(CONTENT))
