from fastapi.testclient import TestClient

from agent.content import DemoStep
from api.auth import DEMO_ACCOUNTS


def _sign_in(client: TestClient, username: str) -> dict[str, str]:
    account = next(a for a in DEMO_ACCOUNTS if a.username == username)
    response = client.post("/api/auth/login", json={"username": account.username, "password": account.password})
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['token']}"}


def play_step(client: TestClient, step: DemoStep) -> None:
    """Plays one step the way the guided demo does, and stops if the tutor does anything the script doesn't expect."""
    if step.clock_days:
        client.post("/api/clock/advance", json={"days": step.clock_days}, headers=_sign_in(client, "teacher")).raise_for_status()
    if not step.answers:
        return
    student = next(a.student_id for a in DEMO_ACCOUNTS if a.username == step.account)
    headers = _sign_in(client, step.account)
    for answer in step.answers:
        question = client.get(f"/api/students/{student}/next", headers=headers).json()["question"]
        if question is None or question["id"] != answer.question_id:
            raise RuntimeError(
                f"Step {step.id}: the script expected {answer.question_id}, but the tutor served "
                f"{question['id'] if question else 'nothing'}. Run scripts.seed_class, then try again."
            )
        option = next(o for o in question["options"] if o["text"] == answer.option)
        response = client.post(
            f"/api/students/{student}/answers",
            json={
                "question_id": question["id"],
                "option_id": option["id"],
                "reasoning": answer.reasoning,
                "confidence_tap": answer.confidence,
            },
            headers=headers,
        )
        response.raise_for_status()
        diagnosis = response.json()["diagnosis"]
        found = (diagnosis["error_type"], diagnosis["misconception_id"])
        wanted = (answer.expect_error_type, answer.expect_misconception_id)
        if found != wanted:
            raise RuntimeError(f"Step {step.id}, {answer.question_id}: the script expected {wanted}, but got {found}.")
        print(f"{student}: {question['id']} -> {found[0]}/{found[1]}")


def warm_demo(client: TestClient) -> None:
    teacher = _sign_in(client, "teacher")
    client.post("/api/demo/reset", headers=teacher)
    for step in client.app.state.demo_script:
        play_step(client, step)
    plan = client.post("/api/class/plan", headers=teacher)
    print(f"Lesson plan: {plan.status_code}")
    client.post("/api/demo/reset", headers=teacher)


def main() -> None:
    from api.main import create_app

    with TestClient(create_app()) as client:
        warm_demo(client)
    print("Demo answers are cached.")


if __name__ == "__main__":
    main()
