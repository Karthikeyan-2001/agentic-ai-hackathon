import json
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from tests.helpers import DemoClient

from agent.content import ContentError
from agent.generate import GeneratedOption, GeneratedQuestion
from api.main import create_app
from tests.fakes import FailingLLM, FakeLLM

REASONING = {
    "The first bulb used up half": ("misconception", "current_consumed", "used up half"),
    "The bulbs are identical": ("misconception", "identical_implies_equal", "bulbs are identical"),
    "One path so the current stays the same": ("none", None, None),
}


def responder(system, user, schema):
    reasoning = user.split("<student_reasoning>\n")[1].split("\n</student_reasoning>")[0]
    error_type, misconception_id, quote = REASONING.get(reasoning, ("gap", None, None))
    return schema(
        error_type=error_type,
        misconception_id=misconception_id,
        first_wrong_step=None,
        evidence_quote=quote,
        confidence=0.9,
    )


@pytest.fixture
def content_dir(tmp_path):
    target = tmp_path / "content"
    target.mkdir()
    for name in ["concepts.json", "misconceptions.json", "questions.json"]:
        shutil.copy(Path("content") / name, target / name)
    return target


@pytest.fixture
def client(tmp_path, content_dir):
    app = create_app(db_url=f"sqlite:///{tmp_path}/t.db", llm=FakeLLM(responder), content_dir=content_dir)
    with DemoClient(app) as test_client:
        yield test_client


def submit(client, student, question, text, reasoning, tap="sure"):
    option = next(o for o in question["options"] if o["text"] == text)
    return client.post(
        f"/api/students/{student}/answers",
        json={"question_id": question["id"], "option_id": option["id"], "reasoning": reasoning, "confidence_tap": tap},
    )


def next_question(client, student):
    return client.get(f"/api/students/{student}/next").json()["question"]


def mastery(client, student, concept_id):
    state = client.get(f"/api/students/{student}/state").json()
    return next(c for c in state["concepts"] if c["id"] == concept_id)


def test_students_lists_only_non_simulated(client):
    body = client.get("/api/students").json()
    assert [s["id"] for s in body] == ["A", "B", "C", "D"]


def test_graph_returns_concepts_and_links(client):
    body = client.get("/api/graph").json()
    assert any(c["id"] == "series_current" and c["prerequisites"] == ["electric_current"] for c in body["concepts"])
    assert len(body["concepts"]) >= 25


def test_next_hides_answer_key(client):
    body = client.get("/api/students/A/next").json()
    assert body["status"] == "question"
    assert body["question"]["id"] == "q_series_two_bulbs"
    assert "is_correct" not in json.dumps(body) and "misconception_ids" not in json.dumps(body)


def test_next_is_stable_across_refreshes(client):
    assert next_question(client, "D")["id"] == next_question(client, "D")["id"]


def test_answer_flow_changes_state(client):
    response = submit(client, "A", next_question(client, "A"), "0.25 A", "The first bulb used up half")
    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is False
    assert body["correct_option_id"] == "b"
    assert body["diagnosis"]["misconception_id"] == "current_consumed"
    assert body["diagnosis_status"] == "ok"
    assert [t["step"] for t in body["trace"]] == ["check", "diagnose", "validate", "update", "decide"]
    assert any(c["id"] == "series_current" for c in body["mastery_changes"])
    assert any(c["id"] == "current_consumed" for c in body["misconception_changes"])
    assert body["caught_up"] is False
    assert mastery(client, "A", "series_current")["mastery"] < 0.3
    assert next_question(client, "A")["id"] == "q_current_in_out"


def test_three_demo_students_get_different_paths(client):
    a = submit(client, "A", next_question(client, "A"), "0.25 A", "The first bulb used up half").json()
    c = submit(client, "C", next_question(client, "C"), "0.5 A", "The bulbs are identical").json()
    assert a["correct"] is False and c["correct"] is True
    assert next_question(client, "A")["id"] == "q_current_in_out"
    assert next_question(client, "C")["id"] == "q_different_bulbs"
    assert mastery(client, "C", "series_current")["mastery"] == pytest.approx(0.3)


def test_state_reports_misconceptions_and_assessed_flag(client):
    submit(client, "A", next_question(client, "A"), "0.25 A", "The first bulb used up half")
    state = client.get("/api/students/A/state").json()
    assert mastery(client, "A", "series_current")["assessed"] is True
    assert mastery(client, "A", "reflection_laws")["assessed"] is False
    active = next(m for m in state["misconceptions"] if m["id"] == "current_consumed")
    assert active["status"] == "active"
    assert active["description"]
    assert state["due_reviews"] == []


def test_double_submit_returns_409_and_keeps_mastery(client):
    question = next_question(client, "A")
    submit(client, "A", question, "0.25 A", "The first bulb used up half")
    before = mastery(client, "A", "series_current")["mastery"]
    second = submit(client, "A", question, "0.25 A", "The first bulb used up half")
    assert second.status_code == 409
    assert mastery(client, "A", "series_current")["mastery"] == before


def test_answering_a_different_question_returns_409(client):
    next_question(client, "A")
    response = client.post(
        "/api/students/A/answers",
        json={"question_id": "q_ohm_basic", "option_id": "c", "reasoning": "x", "confidence_tap": "sure"},
    )
    assert response.status_code == 409


def test_answering_before_any_question_is_served_returns_409(client):
    response = client.post(
        "/api/students/A/answers",
        json={"question_id": "q_series_two_bulbs", "option_id": "b", "reasoning": "x", "confidence_tap": "sure"},
    )
    assert response.status_code == 409


def test_reasoning_over_2000_chars_returns_422(client):
    response = submit(client, "A", next_question(client, "A"), "0.5 A", "x" * 2001)
    assert response.status_code == 422


def test_blank_reasoning_is_accepted_as_unclear(client):
    response = submit(client, "A", next_question(client, "A"), "0.5 A", "   ")
    assert response.status_code == 200
    assert response.json()["diagnosis"]["error_type"] == "unclear"


def test_unknown_student_returns_404(client):
    assert client.get("/api/students/ghost/next").status_code == 403
    assert client.get("/api/students/ghost/state").status_code == 404
    response = client.post(
        "/api/students/ghost/answers",
        json={"question_id": "q", "option_id": "a", "reasoning": "x", "confidence_tap": "sure"},
    )
    assert response.status_code == 403


def test_unknown_option_returns_422(client):
    question = next_question(client, "A")
    response = client.post(
        "/api/students/A/answers",
        json={"question_id": question["id"], "option_id": "ghost", "reasoning": "x", "confidence_tap": "sure"},
    )
    assert response.status_code == 422
    assert next_question(client, "A")["id"] == question["id"]


def test_invalid_confidence_tap_returns_422(client):
    question = next_question(client, "A")
    response = client.post(
        "/api/students/A/answers",
        json={"question_id": question["id"], "option_id": "a", "reasoning": "x", "confidence_tap": "maybe"},
    )
    assert response.status_code == 422


def test_llm_failure_returns_failed_status_not_500(tmp_path, content_dir):
    app = create_app(db_url=f"sqlite:///{tmp_path}/f.db", llm=FailingLLM(), content_dir=content_dir)
    with DemoClient(app) as client:
        response = submit(client, "A", next_question(client, "A"), "0.25 A", "used up")
    assert response.status_code == 200
    assert response.json()["diagnosis_status"] == "failed"


def test_clock_advance_brings_review_due(client):
    submit(client, "A", next_question(client, "A"), "0.5 A", "One path so the current stays the same")
    assert next_question(client, "A") is not None
    assert client.post("/api/clock/advance", json={"days": 7}).json()["offset_days"] == 7
    state = client.get("/api/students/A/state").json()
    assert any(r["id"] == "series_current" for r in state["due_reviews"])
    body = client.get("/api/students/A/next").json()
    assert body["rule"] == 4
    assert body["question"]["concept_id"] == "series_current"


def test_clock_advance_rejects_invalid_days(client):
    assert client.post("/api/clock/advance", json={"days": 0}).status_code == 422
    assert client.post("/api/clock/advance", json={"days": -3}).status_code == 422


def test_clock_reset(client):
    client.post("/api/clock/advance", json={"days": 7})
    assert client.post("/api/clock/reset").json()["offset_days"] == 0


def test_demo_reset_restores_pins_and_clock(client):
    submit(client, "A", next_question(client, "A"), "0.25 A", "The first bulb used up half")
    client.post("/api/clock/advance", json={"days": 7})
    assert client.post("/api/demo/reset").status_code == 200
    assert next_question(client, "A")["id"] == "q_series_two_bulbs"
    assert mastery(client, "A", "series_current")["mastery"] == 0.3
    assert client.post("/api/clock/advance", json={"days": 1}).json()["offset_days"] == 1


def test_restart_keeps_state_and_demo_students(tmp_path, content_dir):
    db_url = f"sqlite:///{tmp_path}/r.db"
    with DemoClient(create_app(db_url=db_url, llm=FakeLLM(responder), content_dir=content_dir)) as client:
        submit(client, "A", next_question(client, "A"), "0.25 A", "The first bulb used up half")
        before = mastery(client, "A", "series_current")["mastery"]
    with DemoClient(create_app(db_url=db_url, llm=FakeLLM(responder), content_dir=content_dir)) as client:
        assert [s["id"] for s in client.get("/api/students").json()] == ["A", "B", "C", "D"]
        assert mastery(client, "A", "series_current")["mastery"] == before
        assert next_question(client, "A")["id"] == "q_current_in_out"


def test_malformed_content_stops_startup(tmp_path, content_dir):
    (content_dir / "questions.json").write_text("{broken")
    with pytest.raises(ContentError, match="questions.json"):
        create_app(db_url=f"sqlite:///{tmp_path}/m.db", llm=FakeLLM(responder), content_dir=content_dir)


def test_generated_questions_are_saved(tmp_path, content_dir):
    def generating(system, user, schema):
        if schema is GeneratedQuestion:
            return GeneratedQuestion(
                stem="A 4 ohm resistor is across a 12 V supply. Find the current.",
                function="ohm_current",
                args=[12, 4],
                unit="A",
                options=[GeneratedOption(value=3, misconception_id=None), GeneratedOption(value=48, misconception_id=None)],
                difficulty_prior=2,
            )
        return responder(system, user, schema)

    # With only one question in the bank, the second question has to be generated.
    questions = json.loads((content_dir / "questions.json").read_text())
    (content_dir / "questions.json").write_text(json.dumps([q for q in questions if q["id"] == "q_ohm_basic"]))
    db_url = f"sqlite:///{tmp_path}/g.db"
    with DemoClient(create_app(db_url=db_url, llm=FakeLLM(generating), content_dir=content_dir)) as client:
        submit(client, "D", next_question(client, "D"), "3 A", "dunno")
        generated = next_question(client, "D")
    assert generated["id"].startswith("g_live_ohms_law")
    reopened = create_app(db_url=db_url, llm=FakeLLM(generating), content_dir=content_dir)
    assert generated["id"] in reopened.state.content.questions


def test_concurrent_double_submit_applies_once(tmp_path, content_dir):
    def slow(system, user, schema):
        time.sleep(0.2)
        return responder(system, user, schema)

    app = create_app(db_url=f"sqlite:///{tmp_path}/c.db", llm=FakeLLM(slow), content_dir=content_dir)
    with DemoClient(app) as client:
        question = next_question(client, "A")
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(submit, client, "A", question, "0.25 A", "The first bulb used up half") for _ in range(2)
            ]
            statuses = sorted(future.result().status_code for future in futures)
        assert statuses == [200, 409]
        assert client.get("/api/students/A/state").json()["answer_count"] == 1
