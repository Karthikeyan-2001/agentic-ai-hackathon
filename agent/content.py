import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ValidationError

from engine.types import Concept, Misconception, Question


class ContentError(Exception):
    pass


@dataclass
class Content:
    concepts: dict[str, Concept]
    misconceptions: dict[str, Misconception]
    questions: dict[str, Question]


def _load_items(path: Path, model: type[BaseModel]) -> dict:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContentError(f"{path.name}: {error}") from error
    items = {}
    for entry in raw:
        item_id = entry.get("id", "<no id>") if isinstance(entry, dict) else "<not an object>"
        try:
            item = model.model_validate(entry)
        except ValidationError as error:
            raise ContentError(f"{path.name}: item {item_id}: {error}") from error
        if item.id in items:
            raise ContentError(f"{path.name}: duplicate item {item.id}")
        items[item.id] = item
    return items


def _check_acyclic(concepts: dict[str, Concept]) -> None:
    done: set[str] = set()

    def visit(concept_id: str, path: tuple[str, ...]) -> None:
        if concept_id in path:
            raise ContentError(f"concepts.json: cycle at {concept_id}")
        if concept_id in done:
            return
        for prerequisite in concepts[concept_id].prerequisites:
            visit(prerequisite, path + (concept_id,))
        done.add(concept_id)

    for concept_id in concepts:
        visit(concept_id, ())


def _check_references(content: Content, source: str = "questions.json") -> None:
    for concept in content.concepts.values():
        for prerequisite in concept.prerequisites:
            if prerequisite not in content.concepts:
                raise ContentError(f"concepts.json: item {concept.id}: unknown prerequisite {prerequisite}")
    _check_acyclic(content.concepts)
    for misconception in content.misconceptions.values():
        if misconception.concept_id not in content.concepts:
            raise ContentError(
                f"misconceptions.json: item {misconception.id}: unknown concept {misconception.concept_id}"
            )
    for question in content.questions.values():
        check_question(question, content, source)


def check_question(question: Question, content: Content, source: str) -> None:
    if question.concept_id not in content.concepts:
        raise ContentError(f"{source}: item {question.id}: unknown concept {question.concept_id}")
    correct = [option for option in question.options if option.is_correct]
    if len(correct) != 1:
        raise ContentError(f"{source}: item {question.id}: needs exactly one correct option, found {len(correct)}")
    for option in question.options:
        for misconception_id in option.misconception_ids:
            if misconception_id not in content.misconceptions:
                raise ContentError(f"{source}: item {question.id}: unknown misconception {misconception_id}")


def load_content(content_dir: Path) -> Content:
    content_dir = Path(content_dir)
    content = Content(
        concepts=_load_items(content_dir / "concepts.json", Concept),
        misconceptions=_load_items(content_dir / "misconceptions.json", Misconception),
        questions=_load_items(content_dir / "questions.json", Question),
    )
    _check_references(content)
    return content
