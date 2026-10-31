from datetime import datetime, timedelta

from engine.selection import SelectionContext, choose_next, oldest_seen_question
from engine.types import Concept, ConceptState, MisconceptionState, Option, Question

NOW = datetime(2026, 1, 20)


def concept(id, *prerequisites):
    return Concept(id=id, name=id, chapter="Python Programming", description="d", prerequisites=list(prerequisites))


def question(id, concept_id="c", probes=(), difficulty=2):
    options = [Option(id="right", text="r", is_correct=True)]
    for index, group in enumerate(probes):
        ids = [group] if isinstance(group, str) else list(group)
        options.append(Option(id=f"w{index}", text="w", is_correct=False, misconception_ids=ids))
    return Question(id=id, concept_id=concept_id, stem="s", options=options, difficulty_prior=difficulty, source="seed")


def mastered(*concept_ids, mastery=0.9):
    return {c: ConceptState(c, mastery=mastery) for c in concept_ids}


def context(questions, concepts=None, **overrides):
    values = dict(
        now=NOW,
        pinned_question_id=None,
        diagnostic_complete=True,
        concepts=concepts or {"c": concept("c")},
        misconceptions={},
        questions={q.id: q for q in questions},
        concept_states={},
        misconception_states={},
        difficulty_elo={},
        ability_elo=1500.0,
        recent_question_ids=[],
        last_seen={},
    )
    values.update(overrides)
    return SelectionContext(**values)


def beliefs(**probabilities):
    return {
        key: MisconceptionState(key, probability=value, status="active" if value >= 0.5 else "candidate")
        for key, value in probabilities.items()
    }


def test_rule1_pinned_wins():
    result = choose_next(context([question("q1")], pinned_question_id="q1", diagnostic_complete=False))
    assert (result.rule, result.question_id) == (1, "q1")


def test_rule2_diagnostic_picks_closest_to_half():
    concepts = {"a": concept("a"), "b": concept("b")}
    questions = [question("qa", "a"), question("qb", "b")]
    states = {"a": ConceptState("a", mastery=0.1), "b": ConceptState("b", mastery=0.45)}
    result = choose_next(context(questions, concepts, diagnostic_complete=False, concept_states=states))
    assert (result.rule, result.question_id) == (2, "qb")


def test_rule2_tie_prefers_most_dependents():
    concepts = {"a": concept("a"), "b": concept("b", "a"), "z": concept("z")}
    questions = [question("qa", "a"), question("qb", "b"), question("qz", "z")]
    result = choose_next(context(questions, concepts, diagnostic_complete=False))
    assert result.question_id == "qa"


def test_rule2_skips_concepts_without_questions():
    concepts = {"a": concept("a"), "b": concept("b")}
    states = {"a": ConceptState("a", mastery=0.5), "b": ConceptState("b", mastery=0.1)}
    result = choose_next(context([question("qb", "b")], concepts, diagnostic_complete=False, concept_states=states))
    assert result.question_id == "qb"


def test_rule3_top_two_score():
    questions = [question("q_a", probes=["a"]), question("q_b", probes=["b"])]
    result = choose_next(context(questions, misconception_states=beliefs(a=0.65, b=0.24)))
    assert (result.rule, result.question_id) == (3, "q_a")
    assert result.hypotheses == [("a", 0.65), ("b", 0.24)]


def test_rule3_separating_bonus():
    questions = [question("q_a", probes=["a"]), question("q_both", probes=["a", "b"])]
    result = choose_next(context(questions, misconception_states=beliefs(a=0.65, b=0.24)))
    assert result.question_id == "q_both"


def test_rule3_same_option_gets_no_bonus():
    # q_same scores .89 without the bonus, so the separating question at 1.39 wins.
    questions = [question("q_same", probes=[("a", "b")]), question("q_sep", probes=["a", "b"])]
    result = choose_next(context(questions, misconception_states=beliefs(a=0.65, b=0.24)))
    assert result.question_id == "q_sep"


def test_rule3_excludes_recent():
    questions = [question("q_a", probes=["a"]), question("q_b", probes=["b"])]
    result = choose_next(
        context(questions, misconception_states=beliefs(a=0.65, b=0.24), recent_question_ids=["q_a"])
    )
    assert result.question_id == "q_b"


def test_rule3_falls_through_when_score_zero():
    questions = [question("q_plain")]
    states = mastered("c", mastery=0.3)
    result = choose_next(context(questions, misconception_states=beliefs(a=0.65), concept_states=states))
    assert result.rule == 5


def test_rule3_ignores_below_0_2():
    questions = [question("q_a", probes=["a"])]
    result = choose_next(
        context(questions, misconception_states=beliefs(a=0.19), concept_states=mastered("c"))
    )
    assert result is None


def test_rule4_due_resolved_misconception_before_concept():
    concepts = {"c": concept("c"), "d": concept("d")}
    questions = [question("q_c", "c"), question("q_d", "d", probes=["m"])]
    states = {
        "c": ConceptState("c", mastery=0.9, stability_days=1, last_practiced_at=NOW - timedelta(days=30)),
        "d": ConceptState("d", mastery=0.9),
    }
    resolved = {
        "m": MisconceptionState(
            "m", probability=0.1, status="resolved", stability_days=3, resolved_at=NOW - timedelta(days=1), was_active=True
        )
    }
    result = choose_next(context(questions, concepts, concept_states=states, misconception_states=resolved))
    assert (result.rule, result.question_id) == (4, "q_d")


def test_rule4_lowest_recall_first():
    concepts = {"a": concept("a"), "b": concept("b")}
    questions = [question("qa", "a"), question("qb", "b")]
    states = {
        "a": ConceptState("a", mastery=0.9, stability_days=2, last_practiced_at=NOW - timedelta(days=2)),
        "b": ConceptState("b", mastery=0.9, stability_days=2, last_practiced_at=NOW - timedelta(days=8)),
    }
    result = choose_next(context(questions, concepts, concept_states=states))
    assert (result.rule, result.question_id) == (4, "qb")


def test_rule4_prefers_unseen_question():
    questions = [question("q_seen"), question("q_new")]
    states = {"c": ConceptState("c", mastery=0.9, stability_days=2, last_practiced_at=NOW - timedelta(days=8))}
    result = choose_next(context(questions, concept_states=states, last_seen={"q_seen": NOW - timedelta(days=8)}))
    assert result.question_id == "q_new"


def test_rule5_weakest_with_met_prerequisites():
    concepts = {"a": concept("a"), "b": concept("b", "a"), "e": concept("e")}
    questions = [question("qa", "a"), question("qb", "b"), question("qe", "e")]
    states = {
        "a": ConceptState("a", mastery=0.4),
        "b": ConceptState("b", mastery=0.1),
        "e": ConceptState("e", mastery=0.6),
    }
    result = choose_next(context(questions, concepts, concept_states=states))
    assert (result.rule, result.question_id) == (5, "qa")


def test_rule5_goes_to_weakest_prerequisite_when_unmet():
    concepts = {"a": concept("a", "z"), "b": concept("b", "a"), "z": concept("z", "a2"), "a2": concept("a2")}
    questions = [question("qb", "b"), question("qa", "a")]
    states = {"b": ConceptState("b", mastery=0.1), "a": ConceptState("a", mastery=0.4)}
    result = choose_next(context(questions, concepts, concept_states=states))
    assert result.question_id == "qa"


def test_rule5_ignores_prerequisites_without_questions():
    # if_else has no questions, so it can't block for_range.
    concepts = {"blocker": concept("blocker"), "c": concept("c", "blocker")}
    states = {"blocker": ConceptState("blocker", mastery=0.1), "c": ConceptState("c", mastery=0.3)}
    result = choose_next(context([question("q1")], concepts, concept_states=states))
    assert (result.rule, result.question_id) == (5, "q1")


def test_rule5_skips_concepts_without_questions():
    concepts = {"a": concept("a"), "c": concept("c")}
    states = {"a": ConceptState("a", mastery=0.1), "c": ConceptState("c", mastery=0.9)}
    assert choose_next(context([question("q1")], concepts, concept_states=states)) is None


def test_rule6_returns_none_when_nothing_needed():
    assert choose_next(context([question("q1")], concept_states=mastered("c"))) is None


def test_no_unseen_returns_concept_with_null_question():
    result = choose_next(
        context([question("q1")], concept_states=mastered("c", mastery=0.3), last_seen={"q1": NOW})
    )
    assert (result.rule, result.question_id, result.concept_id) == (5, None, "c")


def test_tie_break_expected_near_0_6_then_id():
    questions = [question("q_hard", difficulty=5), question("q_mid", difficulty=3), question("q_mid2", difficulty=3)]
    result = choose_next(context(questions, concept_states=mastered("c", mastery=0.3)))
    # At ability 1500, both mid questions are nearest to 0.6 and tie, so the ID decides.
    assert result.question_id == "q_mid"


def test_difficulty_elo_overrides_prior():
    questions = [question("q1", difficulty=5), question("q2", difficulty=1)]
    elo = {"q1": 1430.0, "q2": 1000.0}
    result = choose_next(context(questions, concept_states=mastered("c", mastery=0.3), difficulty_elo=elo))
    assert result.question_id == "q1"


def test_repeatable():
    questions = [question("q_a", probes=["a"]), question("q_b", probes=["b"])]
    ctx = context(questions, misconception_states=beliefs(a=0.65, b=0.24))
    assert choose_next(ctx) == choose_next(ctx)


def test_reason_is_plain_text():
    result = choose_next(context([question("q1")], concept_states=mastered("c", mastery=0.3)))
    assert isinstance(result.reason, str) and result.reason


def test_oldest_seen_question():
    questions = [question("q1"), question("q2"), question("q3")]
    seen = {"q1": NOW - timedelta(days=1), "q2": NOW - timedelta(days=5)}
    assert oldest_seen_question(context(questions, last_seen=seen), "c") == "q2"


def test_oldest_seen_question_none_when_nothing_seen():
    assert oldest_seen_question(context([question("q1")]), "c") is None
