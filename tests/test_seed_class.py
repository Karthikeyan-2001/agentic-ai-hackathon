import shutil
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from api.main import create_app
from api.models import AnswerRow, Student
from agent.plan import LessonPlan
from scripts.seed_class import seed_class
from tests.fakes import FailingLLM, FakeLLM

NOW = datetime(2026, 1, 15)


@pytest.fixture
def content_dir(tmp_path):
    target = tmp_path / "content"
    target.mkdir()
    for name in ["concepts.json", "misconceptions.json", "questions.json"]:
        shutil.copy(Path("content") / name, target / name)
    return target


@pytest.fixture
def llm():
    return FakeLLM(
        lambda s, u, schema: LessonPlan(title="Current is not used up", board_demo="Two ammeters", check_question_id="q_current_in_out")
    )


@pytest.fixture
def app(tmp_path, content_dir, llm):
    return create_app(db_url=f"sqlite:///{tmp_path}/s.db", llm=llm, content_dir=content_dir)


def seed(app, seed_value=42):
    return seed_class(app.state.session_factory, app.state.content, NOW, seed=seed_value)


def simulated(app):
    with app.state.session_factory() as session:
        return session.exec(select(Student).where(Student.is_simulated == True)).all()  # noqa: E712


def test_seed_creates_30_students(app):
    assert seed(app) == 30
    assert len(simulated(app)) == 30


def test_seed_twice_keeps_30_and_preserves_demo_students(app):
    seed(app)
    seed(app)
    assert len(simulated(app)) == 30
    with TestClient(app) as client:
        assert [s["id"] for s in client.get("/api/students").json()] == ["A", "B", "C", "D"]


def test_seed_is_repeatable(app):
    seed(app)
    with TestClient(app) as client:
        first = client.get("/api/class/summary").json()
        seed(app)
        second = client.get("/api/class/summary").json()
    assert first["groups"] == second["groups"]
    assert first["root_causes"] == second["root_causes"]
    assert first["calibration_flags"] == second["calibration_flags"]


def test_seed_answers_per_student_are_12_or_fewer_when_pool_is_small(app):
    # The test bank has 12 questions, so nobody can get more than that.
    seed(app)
    with app.state.session_factory() as session:
        answers = session.exec(select(AnswerRow)).all()
    counts = {}
    for answer in answers:
        counts[answer.student_id] = counts.get(answer.student_id, 0) + 1
    assert len(counts) == 30
    assert all(count == 12 for count in counts.values())


def test_seed_answers_per_student_are_12_to_15_with_a_full_pool(tmp_path, llm):
    from scripts.seed_class import answers_for_student
    import random

    rng = random.Random(1)
    assert all(12 <= answers_for_student(rng, 40) <= 15 for _ in range(50))
    assert answers_for_student(rng, 12) == 12


def test_seed_makes_no_llm_calls(tmp_path, content_dir):
    llm = FailingLLM()
    app = create_app(db_url=f"sqlite:///{tmp_path}/n.db", llm=llm, content_dir=content_dir)
    seed(app)
    assert llm.calls == 0


def test_summary_route_returns_groups_after_seed(app):
    seed(app)
    with TestClient(app) as client:
        body = client.get("/api/class/summary").json()
    assert body["student_count"] == 30
    assert body["is_simulated"] is True
    assert body["groups"]
    assert len(body["heatmap"]["students"]) == 30


def test_summary_route_excludes_demo_students(app):
    with TestClient(app) as client:
        body = client.get("/api/class/summary").json()
    assert body["student_count"] == 0 and body["heatmap"]["students"] == []


def test_plan_route_caches_result(app, llm):
    seed(app)
    with TestClient(app) as client:
        first = client.post("/api/class/plan")
        count = len(llm.calls)
        second = client.post("/api/class/plan")
    assert first.status_code == 200
    assert first.json() == second.json()
    assert first.json()["student_count"] > 0
    assert first.json()["check_question_stem"]
    assert len(llm.calls) == count == 1


def test_plan_route_with_no_active_misconception_returns_404(app):
    with TestClient(app) as client:
        assert client.post("/api/class/plan").status_code == 404


def test_plan_route_reports_llm_failure(tmp_path, content_dir):
    app = create_app(db_url=f"sqlite:///{tmp_path}/f.db", llm=FailingLLM(), content_dir=content_dir)
    seed(app)
    with TestClient(app) as client:
        assert client.post("/api/class/plan").status_code == 503
