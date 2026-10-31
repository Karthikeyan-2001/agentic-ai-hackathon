from pydantic import BaseModel

from agent.content import Content
from agent.llm import LLMClient, LLMError

SYSTEM = """You help a Class 10 physics teacher plan a short lesson that corrects one misconception.
Give a short title, a board demonstration the teacher can run in 10 minutes, and a check question ID chosen from the list."""


class LessonPlan(BaseModel):
    title: str
    board_demo: str
    check_question_id: str


def _probing_questions(misconception_id: str, content: Content) -> list[str]:
    return sorted(
        q.id for q in content.questions.values() if any(misconception_id in o.misconception_ids for o in q.options)
    )


def draft_lesson_plan(
    misconception_id: str, student_count: int, content: Content, llm: LLMClient
) -> LessonPlan | None:
    misconception = content.misconceptions[misconception_id]
    probing = _probing_questions(misconception_id, content)
    listed = "\n".join(f"- {qid}: {content.questions[qid].stem}" for qid in probing)
    prompt = (
        f"Misconception: {misconception.description}\n"
        f"Students affected: {student_count}\n"
        f"Check questions:\n{listed}"
    )
    try:
        plan = llm.complete(SYSTEM, prompt, LessonPlan).value
    except LLMError:
        return None
    if plan.check_question_id not in probing and probing:
        plan = plan.model_copy(update={"check_question_id": probing[0]})
    return plan
