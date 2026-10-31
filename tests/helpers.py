import re

from fastapi.testclient import TestClient

from api.auth import DEMO_ACCOUNTS

STUDENT_PATH = re.compile(r"^/api/students/([^/]+)/")


class DemoClient(TestClient):
    """Signs in as the student a path belongs to, or as the teacher for everything else."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tokens: dict[str | None, str] = {}

    def _token_for(self, student_id: str | None) -> str:
        if student_id not in self._tokens:
            account = next(a for a in DEMO_ACCOUNTS if a.student_id == student_id)
            response = super().request(
                "POST", "/api/auth/login", json={"username": account.username, "password": account.password}
            )
            self._tokens[student_id] = response.json()["token"]
        return self._tokens[student_id]

    def request(self, method, url, **kwargs):
        path = str(url)
        headers = dict(kwargs.pop("headers", None) or {})
        if not path.startswith("/api/auth") and "Authorization" not in headers:
            match = STUDENT_PATH.match(path)
            student_id = match.group(1) if match else None
            known = {account.student_id for account in DEMO_ACCOUNTS}
            headers["Authorization"] = f"Bearer {self._token_for(student_id if student_id in known else None)}"
        return super().request(method, url, headers=headers, **kwargs)
