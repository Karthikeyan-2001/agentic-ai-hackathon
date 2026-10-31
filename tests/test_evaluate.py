import json
import shutil
from pathlib import Path

import pytest
from tests.helpers import DemoClient

from agent.content import load_content, load_demo_script
from agent.plan import LessonPlan
from api import store
from api.main import create_app
from scripts.evaluate import load_samples, score
from scripts.seed_class import seed_class
from scripts.warm_demo import warm_demo
from tests.fakes import FailingLLM, FakeLLM

SCRIPT = load_demo_script(Path("content"), load_content(Path("content")))
EXPECTED = {answer.reasoning: answer for step in SCRIPT for answer in step.answers}


def row(expected_type, actual_type, expected_id=None, actual_id=None, seconds=1.0):
    return {
        "expected_error_type": expected_type,
        "error_type": actual_type,
        "expected_misconception_id": expected_id,
        "misconception_id": actual_id,
        "seconds": seconds,
    }


def test_score_counts_error_type_and_misconception():
    rows = [
        row("misconception", "misconception", "m1", "m1", seconds=1.0),
        row("misconception", "misconception", "m1", "m2", seconds=3.0),
        row("misconception", "none", "m2", None, seconds=2.0),
        row("none", "none", seconds=2.0),
    ]
    result = score(rows)
    assert result["count"] == 4
    assert result["error_type_accuracy"] == pytest.approx(0.75)
    assert result["misconception_accuracy"] == pytest.approx(1 / 3)
    assert result["per_misconception"] == {"m1": {"correct": 1, "total": 2}, "m2": {"correct": 0, "total": 1}}
    assert result["avg_seconds"] == pytest.approx(2.0)


def test_score_handles_empty_rows():
    result = score([])
    assert result["count"] == 0
    assert result["error_type_accuracy"] == 0
    assert result["misconception_accuracy"] == 0
    assert result["avg_seconds"] == 0


def test_samples_are_10_tune_and_30_heldout():
    assert len(load_samples(Path("content"), "tune")) == 10
    assert len(load_samples(Path("content"), "heldout")) == 30


def test_samples_reference_real_questions_and_options():
    content = load_content(Path("content"))
    for sample in load_samples(Path("content"), "tune") + load_samples(Path("content"), "heldout"):
        question = content.questions[sample["question_id"]]
        assert sample["option_id"] in {option.id for option in question.options}, sample["id"]
        if sample["expected_error_type"] == "misconception":
            assert sample["expected_misconception_id"] in content.misconceptions, sample["id"]
        else:
            assert sample["expected_misconception_id"] is None, sample["id"]


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
def content_dir(tmp_path):
    target = tmp_path / "content"
    target.mkdir()
    for name in ["concepts.json", "misconceptions.json", "questions.json", "generated_questions.json", "demo_script.json"]:
        shutil.copy(Path("content") / name, target / name)
    return target


def seeded(app):
    with app.state.session_factory() as session:
        now = store.current_time(session)
    seed_class(app.state.session_factory, app.state.content, now)
    return app


def replay(client, app):
    statuses = []
    client.post("/api/demo/reset")
    for step in SCRIPT:
        if step.clock_days:
            client.post("/api/clock/advance", json={"days": step.clock_days})
        student = step.account.replace("student.", "").upper() if step.answers else None
        for answer in step.answers:
            question = client.get(f"/api/students/{student}/next").json()["question"]
            option = next(o for o in question["options"] if o["text"] == answer.option)
            response = client.post(
                f"/api/students/{student}/answers",
                json={
                    "question_id": question["id"],
                    "option_id": option["id"],
                    "reasoning": answer.reasoning,
                    "confidence_tap": answer.confidence,
                },
            )
            statuses.append(response.json()["diagnosis_status"])
    return statuses


def test_warmed_demo_works_when_ollama_is_down(tmp_path, content_dir):
    db_url = f"sqlite:///{tmp_path}/w.db"
    warm_app = seeded(create_app(db_url=db_url, llm=FakeLLM(responder), content_dir=content_dir))
    with DemoClient(warm_app) as client:
        warm_demo(client)
    down_app = create_app(db_url=db_url, llm=FailingLLM(), content_dir=content_dir)
    with DemoClient(down_app) as client:
        statuses = replay(client, down_app)
    assert statuses and set(statuses) == {"cached"}


def test_warm_demo_leaves_students_reset(tmp_path, content_dir):
    app = seeded(create_app(db_url=f"sqlite:///{tmp_path}/r.db", llm=FakeLLM(responder), content_dir=content_dir))
    with DemoClient(app) as client:
        warm_demo(client)
        assert client.get("/api/students/A/next").json()["question"]["id"] == "q_range_count"
        assert client.get("/api/students/A/state").json()["answer_count"] == 0


def test_results_file_uses_the_expected_keys(tmp_path):
    from scripts.evaluate import merge_results

    path = tmp_path / "results.json"
    merge_results(path, "heldout_off", {"count": 1})
    merge_results(path, "heldout_on", {"count": 2})
    assert json.loads(path.read_text()) == {"heldout_off": {"count": 1}, "heldout_on": {"count": 2}}
