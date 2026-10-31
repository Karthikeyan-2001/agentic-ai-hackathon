# Differential

A Class 10 physics tutor that diagnoses a student's reasoning, not just their final answer. It works like a doctor: it forms competing explanations for a mistake, then asks the question that best separates them.

## The idea in one example

Three students answer: *"Two bulbs are in series. The current through the first is 0.5 A. What is the current through the second?"*

| Student | Answer | Reasoning | Diagnosis | Mastery | Next question tests |
|---|---|---|---|---|---|
| A | 0.25 A | "The first bulb used up half" | Thinks current gets consumed | Falls | Whether current leaving a bulb equals current entering it |
| B | 0.25 A | "The current splits between them" | Confuses series with parallel | Falls | The same bulbs in series and in parallel |
| C | 0.5 A | "The bulbs are identical" | Right answer, wrong reason | Unchanged | Two different bulbs in series |

## What's included

- **Diagnostic test:** 8 adaptive questions, each with reasoning and a confidence tap.
- **Concept graph:** 29 concepts across Class 10 physics, with misconceptions and questions for Electricity.
- **Learner model:** Bayesian Knowledge Tracing per concept, and a probability per misconception, updated after every answer.
- **Question selection and generation:** code picks the question that best separates explanations. Generated numeric questions are checked by code against the numbers in the question.
- **Difficulty calibration:** Elo ratings adjust question difficulty from class responses.
- **Misconception detection:** a local LLM matches reasoning to a catalogue and must quote the student's own words.
- **Spaced repetition:** a forgetting curve per concept and per cleared misconception.
- **Teacher dashboard:** a class summary, the biggest concept gaps, reviews due, shared misconceptions, root causes, a heatmap, difficulty surprises and a lesson plan.

The main rule is that the LLM interprets and the code decides. The LLM never sets a score, marks an answer or chooses a question.

## Measured accuracy

Measured on `qwen3.5:9b` with thinking off, using 30 held-out written test cases that weren't used for tuning:

| Measure | Result |
|---|---|
| Error type correct | 29 of 30 (97%) |
| Misconception identified, where one was expected | 18 of 18 (100%) |
| Average time per diagnosis | 0.8 seconds |

These are written test cases, not real student data, and the same AI assistant that helped write the misconception list also wrote them. Treat the result as a check that the system works, not as evidence of accuracy with real students. Full results are in `eval/results.json`.

The teacher dashboard uses a simulated class of 30 made-up students, and is labelled that way.

## Setup

You need Python 3.12 or later, Node 20 or later, and [Ollama](https://ollama.com) running locally.

```bash
ollama pull qwen3.5:9b
```
```bash
python -m venv .venv
```
```bash
.venv/Scripts/pip install -r requirements.txt
```
```bash
npm --prefix web install
```
```bash
npm --prefix web run build
```

The `.venv/Scripts` paths are for Windows. On macOS or Linux, use `.venv/bin`.

## Run it

```bash
.venv/Scripts/python -m scripts.seed_class
```
```bash
.venv/Scripts/python -m scripts.warm_demo
```
```bash
.venv/Scripts/python -m uvicorn api.main:app --port 8000
```

Then open http://localhost:8000. `seed_class` creates the simulated class, and `warm_demo` caches the demo answers.

## Demo accounts

These are mock accounts for the local demo. The login page also has a one-click button for each one.

| Role | Username | Password |
|---|---|---|
| Teacher | `teacher` | `Teacher-Demo-2026` |
| Student A | `student.a` | `Student-A-2026` |
| Student B | `student.b` | `Student-B-2026` |
| Student C | `student.c` | `Student-C-2026` |
| Student D (takes the diagnostic) | `student.d` | `Student-D-2026` |

The server checks the role on every API request:

- Students can only see and answer their own questions.
- Only the teacher can see the class dashboard or use **Jump 7 days** and **Reset demo**.
- The teacher can read a student's progress, but can't answer for them.

The passwords are in the code in plain text, sessions are kept in memory, and restarting the server signs everyone out. This separates roles for a demo, and it isn't real security.

Each browser tab signs in separately, so you can keep the teacher in one window and a student in another.

## Demo script (3 minutes)

Keep the teacher signed in on one window, and click **Reset demo** there first. Use a second window for students: sign in, answer, sign out, then choose the next student. Type these exact answers, tapping **Sure** each time, so they're answered from the cache even if Ollama stops.

| Student | Choose | Reasoning |
|---|---|---|
| A | 0.25 A | The first bulb used up half |
| A, next question | The two readings are equal | Charge is not used up, so the current leaving the bulb equals the current entering it |
| B | 0.25 A | The current splits between them |
| B, next question | Series | In series there is one path, so each bulb carries the battery current |
| C | 0.5 A | The bulbs are identical |
| C, next question | 0.5 A | In series there is one path, so the current is the same in both bulbs |

1. Show students A, B and C with the thinking panel visible (90 seconds).
2. Show a misconception's probability falling. Then click **Jump 7 days** in the teacher window, and return to the student window to show the review due (30 seconds).
3. Go to the teacher window for the class summary, biggest gaps, shared misconceptions and root causes, and draft the Monday plan (40 seconds).
4. Finish with the accuracy result and how it was measured (20 seconds).

## Tests

```bash
.venv/Scripts/python -m pytest
```
```bash
.venv/Scripts/python -m pytest -m llm
```

The second command runs the demo cases against the real model.

## Limits

- Questions cover Electricity only. Other chapters appear in the graph as "not assessed".
- Sign-in is mock, so this runs as a local demo. Don't expose it to the internet as it is.
- No real student has used it yet.
- The AI-written lesson plan is a draft for a teacher to review.
