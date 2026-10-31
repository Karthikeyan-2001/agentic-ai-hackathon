"""Mock sign-in for the local demo. The passwords below are not secrets, and this isn't production authentication."""

import hmac
import secrets
from dataclasses import dataclass
from typing import Literal

from fastapi import Depends, HTTPException, Request

Role = Literal["student", "teacher"]


@dataclass(frozen=True)
class DemoAccount:
    username: str
    password: str
    role: Role
    student_id: str | None
    display_name: str


DEMO_ACCOUNTS = (
    DemoAccount("teacher", "Teacher-Demo-2026", "teacher", None, "Class Teacher"),
    DemoAccount("student.a", "Student-A-2026", "student", "A", "Student A"),
    DemoAccount("student.b", "Student-B-2026", "student", "B", "Student B"),
    DemoAccount("student.c", "Student-C-2026", "student", "C", "Student C"),
    DemoAccount("student.d", "Student-D-2026", "student", "D", "Student D"),
)


def authenticate(username: str, password: str) -> DemoAccount | None:
    match = None
    for account in DEMO_ACCOUNTS:
        username_ok = hmac.compare_digest(account.username.encode(), username.encode())
        password_ok = hmac.compare_digest(account.password.encode(), password.encode())
        if username_ok and password_ok:
            match = account
    return match


class SessionStore:
    """Sessions live in memory, so restarting the server signs everyone out."""

    def __init__(self) -> None:
        self._sessions: dict[str, DemoAccount] = {}

    def create(self, account: DemoAccount) -> str:
        token = secrets.token_urlsafe(32)
        self._sessions[token] = account
        return token

    def get(self, token: str) -> DemoAccount | None:
        return self._sessions.get(token)

    def delete(self, token: str) -> None:
        self._sessions.pop(token, None)


def _bearer_token(request: Request) -> str | None:
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    return token if scheme.lower() == "bearer" and token else None


def current_account(request: Request) -> DemoAccount:
    token = _bearer_token(request)
    account = request.app.state.sessions.get(token) if token else None
    if account is None:
        raise HTTPException(status_code=401, detail="Please sign in.")
    return account


def require_teacher(account: DemoAccount = Depends(current_account)) -> DemoAccount:
    if account.role != "teacher":
        raise HTTPException(status_code=403, detail="Only the teacher can do this.")
    return account


def require_this_student(student_id: str, account: DemoAccount = Depends(current_account)) -> DemoAccount:
    if account.role != "student" or account.student_id != student_id:
        raise HTTPException(status_code=403, detail="You can only use your own student account.")
    return account


def require_this_student_or_teacher(student_id: str, account: DemoAccount = Depends(current_account)) -> DemoAccount:
    if account.role != "teacher" and account.student_id != student_id:
        raise HTTPException(status_code=403, detail="You can only see your own progress.")
    return account
