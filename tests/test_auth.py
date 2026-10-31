import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.auth import DEMO_ACCOUNTS
from api.main import create_app
from tests.fakes import FakeLLM

PUBLIC_ROUTES = {"/api/auth/login", "/api/auth/demo-accounts"}
TEACHER_ONLY = [
    ("get", "/api/students", None),
    ("get", "/api/class/summary", None),
    ("post", "/api/class/plan", None),
    ("post", "/api/clock/advance", {"days": 7}),
    ("post", "/api/clock/reset", None),
    ("post", "/api/demo/reset", None),
]
ANSWER = {"question_id": "q_range_count", "option_id": "b", "reasoning": "x", "confidence_tap": "sure"}


def responder(system, user, schema):
    return schema(error_type="gap", misconception_id=None, first_wrong_step=None, evidence_quote=None, confidence=0.9)


@pytest.fixture
def app(tmp_path):
    content = tmp_path / "content"
    content.mkdir()
    for name in ["concepts.json", "misconceptions.json", "questions.json"]:
        shutil.copy(Path("content") / name, content / name)
    return create_app(db_url=f"sqlite:///{tmp_path}/a.db", llm=FakeLLM(responder), content_dir=content)


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


def account(role, student_id=None):
    return next(a for a in DEMO_ACCOUNTS if a.role == role and a.student_id == student_id)


def sign_in(client, role, student_id=None):
    found = account(role, student_id)
    response = client.post("/api/auth/login", json={"username": found.username, "password": found.password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_login_returns_role_and_student(client):
    found = account("student", "A")
    body = client.post("/api/auth/login", json={"username": found.username, "password": found.password}).json()
    assert body["role"] == "student" and body["student_id"] == "A"
    assert body["display_name"] and body["token"]


def test_teacher_login_has_no_student(client):
    found = account("teacher")
    body = client.post("/api/auth/login", json={"username": found.username, "password": found.password}).json()
    assert body["role"] == "teacher" and body["student_id"] is None


def test_wrong_password_and_unknown_user_look_the_same(client):
    found = account("teacher")
    wrong = client.post("/api/auth/login", json={"username": found.username, "password": "nope"})
    unknown = client.post("/api/auth/login", json={"username": "ghost", "password": "nope"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_demo_accounts_lists_one_teacher_and_four_students(client):
    body = client.get("/api/auth/demo-accounts").json()
    assert sorted(a["role"] for a in body) == ["student"] * 4 + ["teacher"]
    assert all(a["username"] and a["password"] and a["display_name"] for a in body)


def test_me_returns_the_signed_in_user(client):
    headers = sign_in(client, "student", "B")
    assert client.get("/api/auth/me", headers=headers).json()["student_id"] == "B"


def test_logout_ends_the_session(client):
    headers = sign_in(client, "teacher")
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/auth/me", headers=headers).status_code == 401
    assert client.get("/api/class/summary", headers=headers).status_code == 401


def test_every_api_route_needs_a_session_except_login(app, client):
    checked = 0
    for route_path, methods in app.openapi()["paths"].items():
        if route_path in PUBLIC_ROUTES:
            continue
        for method in methods:
            url = route_path.replace("{student_id}", "A")
            response = client.request(method.upper(), url, json={})
            assert response.status_code == 401, f"{method} {url}"
            checked += 1
    assert checked >= 12


def test_invalid_token_is_rejected(client):
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer made-up"}).status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "made-up"}).status_code == 401


@pytest.mark.parametrize("method,path,body", TEACHER_ONLY)
def test_students_cannot_use_teacher_routes(client, method, path, body):
    headers = sign_in(client, "student", "A")
    response = client.request(method, path, json=body, headers=headers)
    assert response.status_code == 403


def test_blocked_student_clock_change_has_no_effect(client):
    student = sign_in(client, "student", "A")
    teacher = sign_in(client, "teacher")
    client.post("/api/clock/advance", json={"days": 7}, headers=student)
    assert client.get("/api/class/summary", headers=teacher).json()["offset_days"] == 0


def test_student_can_use_own_routes(client):
    headers = sign_in(client, "student", "A")
    question = client.get("/api/students/A/next", headers=headers).json()["question"]
    assert question["id"] == "q_range_count"
    assert client.get("/api/students/A/state", headers=headers).status_code == 200
    assert client.get("/api/graph", headers=headers).status_code == 200
    answer = client.post("/api/students/A/answers", json=ANSWER, headers=headers)
    assert answer.status_code == 200


@pytest.mark.parametrize("path", ["/api/students/B/next", "/api/students/B/state", "/api/students/ghost/state"])
def test_student_cannot_read_another_student(client, path):
    headers = sign_in(client, "student", "A")
    assert client.get(path, headers=headers).status_code == 403


def test_student_cannot_answer_for_another_student(client):
    a = sign_in(client, "student", "A")
    b = sign_in(client, "student", "B")
    client.get("/api/students/B/next", headers=b)
    assert client.post("/api/students/B/answers", json=ANSWER, headers=a).status_code == 403
    assert client.get("/api/students/B/state", headers=b).json()["answer_count"] == 0


def test_student_cannot_see_simulated_students(client):
    headers = sign_in(client, "student", "A")
    assert client.get("/api/students/S01/state", headers=headers).status_code == 403


def test_teacher_can_read_a_student_but_cannot_answer_or_change_their_question(client):
    headers = sign_in(client, "teacher")
    assert client.get("/api/students/A/state", headers=headers).status_code == 200
    assert client.get("/api/students/A/next", headers=headers).status_code == 403
    assert client.post("/api/students/A/answers", json=ANSWER, headers=headers).status_code == 403


def test_teacher_gets_404_for_unknown_student(client):
    headers = sign_in(client, "teacher")
    assert client.get("/api/students/ghost/state", headers=headers).status_code == 404


def test_teacher_routes_work_for_the_teacher(client):
    headers = sign_in(client, "teacher")
    assert [s["id"] for s in client.get("/api/students", headers=headers).json()] == ["A", "B", "C", "D"]
    summary = client.get("/api/class/summary", headers=headers).json()
    assert summary["offset_days"] == 0
    assert client.post("/api/clock/advance", json={"days": 7}, headers=headers).json()["offset_days"] == 7
    assert client.get("/api/class/summary", headers=headers).json()["offset_days"] == 7
    assert client.post("/api/demo/reset", headers=headers).status_code == 200


def test_sessions_do_not_survive_a_restart(tmp_path, app, client):
    headers = sign_in(client, "teacher")
    content = tmp_path / "content"
    with TestClient(create_app(db_url=f"sqlite:///{tmp_path}/a.db", llm=FakeLLM(responder), content_dir=content)) as new:
        assert new.get("/api/auth/me", headers=headers).status_code == 401
