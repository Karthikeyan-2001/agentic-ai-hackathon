import json

import pytest

from agent.content import ContentError, load_content


def concept(id, prerequisites=()):
    return {"id": id, "name": id, "chapter": "Python Programming", "description": "d", "prerequisites": list(prerequisites)}


def misconception(id="m1", concept_id="a"):
    return {"id": id, "concept_id": concept_id, "description": "d", "example_wordings": ["w"]}


def question(id="q1", concept_id="a", options=None):
    return {
        "id": id,
        "concept_id": concept_id,
        "stem": "s",
        "options": options
        or [
            {"id": "x", "text": "x", "is_correct": True, "misconception_ids": []},
            {"id": "y", "text": "y", "is_correct": False, "misconception_ids": ["m1"]},
        ],
        "difficulty_prior": 2,
        "source": "seed",
    }


def write(tmp_path, concepts=None, misconceptions=None, questions=None):
    (tmp_path / "concepts.json").write_text(json.dumps(concepts or [concept("a")]))
    (tmp_path / "misconceptions.json").write_text(json.dumps(misconceptions or [misconception()]))
    (tmp_path / "questions.json").write_text(json.dumps(questions or [question()]))
    return tmp_path


def test_loads_valid_content(tmp_path):
    content = load_content(write(tmp_path))
    assert content.concepts["a"].name == "a"
    assert content.misconceptions["m1"].concept_id == "a"
    assert content.questions["q1"].options[0].is_correct is True


def test_rejects_cycle(tmp_path):
    write(tmp_path, concepts=[concept("a", ["b"]), concept("b", ["a"])])
    with pytest.raises(ContentError, match="cycle.*(a|b)"):
        load_content(tmp_path)


def test_rejects_unknown_prerequisite(tmp_path):
    write(tmp_path, concepts=[concept("a", ["ghost"])])
    with pytest.raises(ContentError, match="ghost"):
        load_content(tmp_path)


def test_rejects_unknown_misconception_on_option(tmp_path):
    options = [
        {"id": "x", "text": "x", "is_correct": True, "misconception_ids": []},
        {"id": "y", "text": "y", "is_correct": False, "misconception_ids": ["ghost"]},
    ]
    write(tmp_path, questions=[question(options=options)])
    with pytest.raises(ContentError, match="ghost"):
        load_content(tmp_path)


def test_rejects_two_correct_options(tmp_path):
    options = [
        {"id": "x", "text": "x", "is_correct": True, "misconception_ids": []},
        {"id": "y", "text": "y", "is_correct": True, "misconception_ids": []},
    ]
    write(tmp_path, questions=[question(options=options)])
    with pytest.raises(ContentError, match="q1"):
        load_content(tmp_path)


def test_rejects_invalid_json_names_file(tmp_path):
    write(tmp_path)
    (tmp_path / "questions.json").write_text("{not json")
    with pytest.raises(ContentError) as error:
        load_content(tmp_path)
    assert "questions.json" in str(error.value)


def test_merges_generated_questions_when_present(tmp_path):
    write(tmp_path)
    generated = question(id="g1")
    generated["source"] = "generated"
    (tmp_path / "generated_questions.json").write_text(json.dumps([generated]))
    content = load_content(tmp_path)
    assert set(content.questions) == {"q1", "g1"}


def test_rejects_malformed_generated_question_names_file(tmp_path):
    write(tmp_path)
    (tmp_path / "generated_questions.json").write_text(json.dumps([question(id="g1", concept_id="ghost")]))
    with pytest.raises(ContentError) as error:
        load_content(tmp_path)
    assert "generated_questions.json" in str(error.value)


def test_rejects_invalid_item_names_file_and_item(tmp_path):
    bad = question()
    bad["difficulty_prior"] = 9
    write(tmp_path, questions=[bad])
    with pytest.raises(ContentError) as error:
        load_content(tmp_path)
    assert "questions.json" in str(error.value) and "q1" in str(error.value)
