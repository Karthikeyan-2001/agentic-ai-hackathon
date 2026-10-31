# Differential

A Class 10 Python programming tutor that diagnoses a student's reasoning, not just their final answer. It works like a doctor: it forms competing explanations for a mistake, then asks the question that best separates them.

## The idea in one example

Three students answer: *"How many times does the body of `for i in range(1, 5):` run?"*

| Student | Answer | Reasoning | Diagnosis | Mastery | Next question tests |
|---|---|---|---|---|---|
| A | 5 times | "It counts up to and including 5" | Thinks `range` includes its stop value | Falls | The last number printed by `range(3, 7)` |
| B | 5 times | "The 5 says how many times" | Thinks the stop value is the number of repeats | Falls | How many times `range(4, 6)` runs |
| C | 4 times | "It is always one less than the stop number" | Right answer, wrong reason | Unchanged | How many times `range(3, 8)` runs |

## What's included

- **Diagnostic test:** 8 adaptive questions, each with reasoning and a confidence tap.
- **Concept graph:** 29 concepts across Class 10 computer science, with misconceptions and questions for Python Programming. Computer Networks, Web Pages with HTML and Cyber Ethics complete the graph.
- **Learner model:** Bayesian Knowledge Tracing per concept, and a probability per misconception, updated after every answer.
- **Question selection and generation:** code picks the question that best separates explanations. Generated questions use fixed program templates, and code works out the correct answer. LLM-written code is never run.
- **Difficulty calibration:** Elo ratings adjust question difficulty from class responses.
- **Misconception detection:** a local LLM matches reasoning to a catalogue and must quote the student's own words.
- **Spaced repetition:** a forgetting curve per concept and per cleared misconception.
- **Teacher dashboard:** a class summary, the biggest concept gaps, reviews due, shared misconceptions, root causes, a heatmap, difficulty surprises and a lesson plan.

The main rule is that the LLM interprets and the code decides. The LLM never sets a score, marks an answer or chooses a question.

## Measured accuracy

Measured on `qwen3.5:9b` with thinking off, using 30 held-out written test cases that weren't used for tuning:

| Measure | Result |
|---|---|
| Error type correct | 30 of 30 (100%) |
| Misconception identified, where one was expected | 18 of 18 (100%) |
| Average time per diagnosis | 0.8 seconds |

These are written test cases, not real student data, and the same AI assistant that helped write the misconception list also wrote them, in fairly clear wording. Expect real students to be harder, so treat the result as a check that the system works, not as evidence of accuracy with real students. Full results are in `eval/results.json`.

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

## Guided demo (about 4 minutes)

Click **Start guided demo** on the landing page or the sign-in page. It resets the four demo students, then a bar at the bottom of the page walks through 9 steps, switching accounts for you:

1. **Student A** has a misconception, and the next question tests it.
2. **Student B** gives the same wrong answer for a different reason, and gets a different diagnosis.
3. **Student C** gives the right answer for the wrong reason, so mastery doesn't move.
4. **Student D** takes the 8-question diagnostic, then the concept map shows the weak spot.
5. **Student D** gets a generated question on the weakest concept.
6. **Teacher** clicks **Jump 7 days**.
7. **Student C** has a spaced review come due.
8. **Teacher** shows class-wide gaps and drafts the Monday plan.
9. **Close** shows the accuracy result and how it was measured.

Each form is filled in from `content/demo_script.json`, so you only click **Submit answer**, **Next question** and **Next step**. The answers still go through the same diagnosis and scoring as typed ones. `warm_demo` caches them, so they work even if Ollama stops, and it fails loudly if the tutor stops following the script.

Timings, narration and a list of where each requirement appears are in [docs/demo-video-script.md](docs/demo-video-script.md).

## Tests

```bash
.venv/Scripts/python -m pytest
```
```bash
.venv/Scripts/python -m pytest -m llm
```

The second command runs the demo cases against the real model.

## Limits

- Questions cover Python Programming only. Other chapters appear in the graph as "not assessed".
- Comparison and logic, if and else, and functions have no questions yet.
- Code can generate new questions for arithmetic, running totals, nested loops and list traversal only. A student who stays weak on any other concept cycles through its existing questions. If generation fails, the student sees an older question again.
- Sign-in is mock, so this runs as a local demo. Don't expose it to the internet as it is.
- No real student has used it yet.
- The AI-written lesson plan is a draft for a teacher to review.
