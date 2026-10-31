from fastapi.testclient import TestClient

from api.auth import DEMO_ACCOUNTS

# Type these exact answers in the demo. Each one is then answered from the cache, even with Ollama stopped.
DEMO_SCRIPT = {
    "A": [
        ("5 times", "It counts up to and including 5"),
        ("6", "range stops before its stop value, so 6 is the last number printed"),
    ],
    "B": [
        ("5 times", "The 5 says how many times"),
        ("2 times", "i takes the values 4 and 5, so the loop runs twice"),
    ],
    "C": [
        ("4 times", "It is always one less than the stop number"),
        ("5 times", "8 minus 3 is 5, so the loop runs for 3, 4, 5, 6 and 7"),
    ],
}


def _sign_in(client: TestClient, student_id: str | None) -> dict[str, str]:
    account = next(a for a in DEMO_ACCOUNTS if a.student_id == student_id)
    response = client.post("/api/auth/login", json={"username": account.username, "password": account.password})
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['token']}"}


def warm_demo(client: TestClient) -> None:
    teacher = _sign_in(client, None)
    client.post("/api/demo/reset", headers=teacher)
    for student, steps in DEMO_SCRIPT.items():
        headers = _sign_in(client, student)
        for text, reasoning in steps:
            question = client.get(f"/api/students/{student}/next", headers=headers).json()["question"]
            option = next((o for o in question["options"] if o["text"] == text), None) if question else None
            if option is None:
                raise RuntimeError(f"Student {student}: the demo expected option '{text}', but got {question}")
            response = client.post(
                f"/api/students/{student}/answers",
                json={
                    "question_id": question["id"],
                    "option_id": option["id"],
                    "reasoning": reasoning,
                    "confidence_tap": "sure",
                },
                headers=headers,
            )
            response.raise_for_status()
            body = response.json()
            print(f"{student}: {question['id']} -> {body['diagnosis']['error_type']}/{body['diagnosis']['misconception_id']}")
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
