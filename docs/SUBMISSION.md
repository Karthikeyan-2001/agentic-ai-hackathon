# Differential: Hackathon Submission

| | |
|---|---|
| **Hackathon** | Product Space AI Hackathon |
| **Problem statement** | Adaptive exam-prep tutor with a learner model |
| **Team name** | Works Locally |
| **Team members** | Karthikeyan, Nandini |
| **Project name** | Differential (from "differential diagnosis") |
| **Syllabus** | Class 10 Computer Science (Python Programming assessed) |
| **Repository** | https://github.com/Karthikeyan-2001/agentic-ai-hackathon |
| **Demo video** | _Add link before submitting_ |

---

## 1. Summary

Generic AI tutors answer questions, but they don't track what a student actually understands. **Differential** is a Class 10 Python Programming tutor that reads a student's *reasoning*, not just the final answer.

It works like a doctor making a differential diagnosis. When a student makes a mistake, it forms competing explanations (misconceptions), then asks the question that best separates them. Every answer updates a learner model with a mastery level for each concept and a probability for each misconception. That model then decides what to ask next, when to review, and what the teacher sees.

**Main design rule: the LLM interprets and the code decides.** The local LLM only reads the student's reasoning and returns structured data. Tested, deterministic code marks every answer, changes every score and chooses every question. Code written by the LLM is never run.

Everything runs locally on one PC, with a local model (`qwen3.5:9b` on Ollama). No student data leaves the machine, and the app works without internet. That is where our team name comes from.

## 2. The problem

A student who answers "5 times" to *"How many times does `for i in range(1, 5):` run?"* could be wrong for very different reasons. An answer-only tutor treats them all the same. A student who gets the right answer for the wrong reason is marked correct and moves on with a hidden misconception.

| Student | Answer | Reasoning | Differential's diagnosis | Mastery | Next question tests |
|---|---|---|---|---|---|
| A | 5 times (wrong) | "It counts up to and including 5" | Thinks `range` includes its stop value | Falls | The last number printed by `range(3, 7)` |
| B | 5 times (wrong) | "The 5 says how many times" | Thinks the stop value is the number of repeats | Falls | How many times `range(4, 6)` runs |
| C | 4 times (right) | "It is always one less than the stop number" | Right answer, wrong reason | Unchanged | How many times `range(3, 8)` runs |

A and B give the same wrong answer but get different diagnoses and different follow-up questions. C gets the right answer but gets no credit, because the reasoning would fail on other loops.

## 3. How each requirement is met

| # | Requirement | What we built | Where in the code |
|---|---|---|---|
| 1 | **Diagnostic test** | An 8-question adaptive diagnostic. Each question goes to the concept the tutor is least sure about (mastery closest to 0.5), with ties broken by how many concepts depend on it. Every answer needs written reasoning and a "Sure" / "Not sure" confidence tap. | `engine/selection.py` |
| 2 | **Concept graph for one syllabus** | 29 concepts across Class 10 Computer Science with prerequisite links: Python Programming (12), Computer Networks (6), Web Pages with HTML (6) and Cyber Ethics (5). A test makes sure the graph has no cycles. Python Programming is assessed; the other chapters show as "not assessed". | `content/concepts.json`, `engine/graph.py`, `web/src/components/ConceptGraph.tsx` |
| 3 | **Learner model updated after every answer** | Bayesian Knowledge Tracing per concept, with slip and guess values that depend on the diagnosis. A right answer with flawed reasoning leaves mastery unchanged, and a careless slip barely lowers it. Changes spread to prerequisites up to two links away. Each misconception also has its own probability and status (inactive, candidate, active, resolved). | `engine/mastery.py`, `engine/graph.py`, `engine/misconceptions.py` |
| 4 | **Question generation targeted at weak concepts, with difficulty calibration** | Code chooses the target: first the question that best separates the student's top two suspected misconceptions, then due reviews, then the weakest concept whose prerequisites are in place. Among candidates it picks the question closest to a 60% chance of success. Generated questions use fixed program templates: the LLM writes only the wording and options, and code works out the correct answer and rejects bad questions. Elo ratings for students and questions are updated from every answer, and the dashboard flags questions whose class results disagree with their predicted difficulty. | `engine/selection.py`, `engine/elo.py`, `agent/generate.py`, `agent/solvers.py`, `scripts/pregenerate.py` |
| 5 | **Misconception detection from reasoning** | The LLM classifies the student's written reasoning into an error type (`none`, `misconception`, `slip`, `gap`, `unclear`) and matches it to a catalogue of 8 Python misconceptions. It must quote the student's own words as evidence. Code checks that the quote really appears in the student's text, and otherwise caps the confidence. Low-confidence diagnoses are treated as `unclear`, so the tutor asks another question instead of asserting a misconception. | `agent/diagnose.py`, `content/misconceptions.json` |
| 6 | **Spaced-repetition scheduling** | A forgetting curve, `R = exp(-days / S)`, for each concept and for each cleared misconception. A review is due when recall falls below 0.85. Sound answers double stability, wrong answers halve it. Reviews always use a question the student hasn't seen recently. A **Jump 7 days** button moves the app clock for the demo. | `engine/scheduling.py` |
| 7 | **Teacher dashboard of class-wide gaps** | A class summary, the biggest concept gaps, reviews due, students grouped by shared misconception, root causes (the deepest weak prerequisite behind low scores), a student-by-concept heatmap, difficulty surprises from Elo, and an AI-drafted Monday lesson plan for the teacher to review. It is always labelled "Simulated class". | `engine/class_summary.py`, `agent/plan.py`, `web/src/pages/TeacherPage.tsx` |

## 4. Architecture

```text
React app  ->  FastAPI  ->  agent loop  ->  agent/llm.py  ->  Ollama (qwen3.5:9b, local)
                               |
                               +-> engine/ (pure functions, fully unit-tested)
                               +-> SQLite + content JSON
```

### What happens on every answer

1. **Check:** code marks the selected option right or wrong.
2. **Diagnose:** the LLM classifies the reasoning and returns structured JSON (validated with Pydantic).
3. **Validate:** code checks the diagnosis against the catalogue and the student's own text.
4. **Update:** the engine updates mastery, misconception probabilities, the review schedule and Elo ratings.
5. **Decide:** code chooses the next question.
6. **Explain:** the response carries a trace, shown in the student's "thinking panel", so every decision can be seen.

### Folder layout

| Folder | Owns |
|---|---|
| `content/` | Concept graph, misconception catalogue, questions, evaluation samples |
| `engine/` | Mastery, misconceptions, scheduling, Elo, graph, selection, class summary. Pure code: no LLM, database, network or system clock |
| `agent/` | LLM client, diagnosis, question generation, solvers, lesson plan, agent loop |
| `api/` | Database tables, persistence, routes, mock sign-in |
| `scripts/` | Seeding the simulated class, pre-generating questions, evaluation, demo tools |
| `web/` | React app (student app, teacher dashboard, landing page, guided demo) |

### Technology

| Layer | Choice |
|---|---|
| Backend | Python 3.12, FastAPI, SQLModel on SQLite |
| LLM | Ollama running `qwen3.5:9b` locally, thinking off, temperature 0, 30-second timeout, up to two retries, responses cached |
| Frontend | React 19, Vite, TypeScript, Tailwind CSS, React Flow with Dagre for the concept graph |
| Tests | pytest, httpx |

### Safety and robustness

- **Student text is untrusted.** It is wrapped in delimiters, the prompt treats it only as data, and the reply schema limits what the model can return.
- **The LLM never runs code or sets scores.** Generated questions come from fixed templates, and code computes the answer.
- **If the LLM fails** (down, slow or invalid after retries), the answer is still saved and scored from the selected option, and the student sees a small notice.
- **Role checks on every API request:** students can only see and answer their own questions; only the teacher can see the class dashboard.

## 5. Evaluation

We measured diagnosis accuracy on **40 written test cases**: 10 used to tune the prompt and **30 held out** and used only for the reported result.

| Measure (held out, thinking off) | Result |
|---|---|
| Error type correct | 30 of 30 (100%) |
| Misconception identified, where one was expected | 18 of 18 (100%) |
| Average time per diagnosis | 0.84 seconds |

With thinking turned on, accuracy was the same but each diagnosis took about 3.8 seconds, so we kept thinking off. Full results are in `eval/results.json`, produced by `scripts/evaluate.py`.

**Honest limits of this result:** these are written test cases, not real student data. The same AI assistant that helped write the misconception catalogue also wrote the test cases, in fairly clear wording. Real students will be harder, so we treat this as a check that the system works, not as evidence of accuracy with real students.

**Testing:** 271 automated tests cover the engine formulas, graph and content checks, selection rules, the agent with a fake LLM, the three-student demo, sign-in and the API. A separate `pytest -m llm` run checks the demo cases against the real model.

## 6. Demo

The app includes a **guided demo** (about 4 minutes) that switches accounts and fills in answers from a script, while still sending every answer through the real diagnosis and scoring:

1. **Student A** has a misconception, and the next question tests it.
2. **Student B** gives the same wrong answer for a different reason, and gets a different diagnosis.
3. **Student C** gives the right answer for the wrong reason, so mastery doesn't move.
4. **Student D** takes the 8-question diagnostic, then the concept map shows the weak spot.
5. **Student D** gets a generated question on the weakest concept.
6. **Teacher** clicks **Jump 7 days**.
7. **Student C** has a spaced review come due.
8. **Teacher** sees class-wide gaps and drafts the Monday plan.
9. **Close** shows the accuracy result and how it was measured.

The narration and timings are in [`docs/demo-video-script.md`](demo-video-script.md).

### Demo accounts (mock, local only)

| Role | Username | Password |
|---|---|---|
| Teacher | `teacher` | `Teacher-Demo-2026` |
| Student A | `student.a` | `Student-A-2026` |
| Student B | `student.b` | `Student-B-2026` |
| Student C | `student.c` | `Student-C-2026` |
| Student D (takes the diagnostic) | `student.d` | `Student-D-2026` |

The teacher dashboard uses a **simulated class of 30 made-up students** to show how it works. It is labelled "Simulated class" on the page and isn't evidence that diagnosis works.

## 7. How to run it

You need Python 3.12 or later, Node 20 or later, and [Ollama](https://ollama.com) running locally. On macOS or Linux, use `.venv/bin` instead of `.venv/Scripts`.

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
```bash
.venv/Scripts/python -m scripts.seed_class
```
```bash
.venv/Scripts/python -m scripts.warm_demo
```
```bash
.venv/Scripts/python -m uvicorn api.main:app --port 8000
```

Then open http://localhost:8000 and click **Start guided demo**.

## 8. Limits and next steps

**Current limits:**

- Questions cover Python Programming only. Other chapters appear in the graph as "not assessed".
- Comparison and logic, if and else, and functions have no questions yet.
- Code can generate new questions for arithmetic, running totals, nested loops and list traversal only.
- Sign-in is mock, so this is a local demo and shouldn't be exposed to the internet as it is.
- No real student has used it yet.
- The AI-written lesson plan is a draft for a teacher to review.

**Next steps:**

1. Test with real Class 10 students and teachers, and measure diagnosis accuracy on their real reasoning.
2. Add questions and misconceptions for the remaining Python concepts, then the other chapters.
3. Add more question templates so more concepts can get new generated questions.
4. Add real accounts and support for several classes and teachers.
5. Let teachers record "I taught this" and see the effect on the class before and after.

## 9. Team

**Works Locally**

- Karthikeyan
- Nandini
