import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, SQLModel, create_engine

from agent.content import load_content, load_demo_script
from agent.llm import DEFAULT_MODEL, CachedClient, LLMClient, OllamaClient
from api import store
from api.auth import SessionStore
from api.routes import router

WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"


def create_app(
    db_url: str = "sqlite:///tutor.db", llm: LLMClient | None = None, content_dir: Path = Path("content")
) -> FastAPI:
    load_dotenv()
    content = load_content(content_dir)
    demo_script = load_demo_script(content_dir, content)
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    def session_factory() -> Session:
        return Session(engine, expire_on_commit=False)

    with session_factory() as session:
        store.initialise(session, content)

    model = os.environ.get("LLM_MODEL", DEFAULT_MODEL)
    inner = llm or OllamaClient(model=model)
    app = FastAPI(title="Differential")
    app.state.content = content
    app.state.demo_script = demo_script
    app.state.session_factory = session_factory
    app.state.sessions = SessionStore()
    app.state.llm = CachedClient(inner, store.SqlCacheStore(session_factory), model)
    app.include_router(router)

    if WEB_DIST.exists():
        app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str) -> FileResponse:
            if path.startswith("api/"):
                raise HTTPException(status_code=404)
            candidate = (WEB_DIST / path).resolve()
            if path and candidate.is_file() and candidate.is_relative_to(WEB_DIST):
                return FileResponse(candidate)
            return FileResponse(WEB_DIST / "index.html")

    return app


def __getattr__(name: str):
    # Lets `uvicorn api.main:app` build the app on demand, so importing this module has no side effects.
    if name == "app":
        return create_app()
    raise AttributeError(name)
