# Demo video script (2 minutes)

**Team:** Works Locally (Karthikeyan and Nandini)
**Project:** Differential, an adaptive exam-prep tutor with a learner model
**Length:** 2:00, about 270 spoken words
**Shown on:** the website's **Start guided demo** flow

Every requirement in the brief appears on screen at least once (see the checklist at the end). The longer 4-minute version is in [demo-video-script.md](demo-video-script.md).

---

## How to record it

Clicking through the guided demo takes about 4 minutes, mostly because Student D answers 8 diagnostic questions. To fit 2 minutes, record in two passes:

1. **Screen pass, no voice.** Run the whole guided demo calmly, and pause on each screen for 3 to 4 seconds so you have footage to cut.
2. **Edit.** Cut the screen recording to the timings in the table below. Speed up or cut the clicking between screens (see the cut list).
3. **Voice pass.** Record the narration over the edited video. Talk at a relaxed pace of about 2.5 words a second.

**Who speaks:** Karthikeyan narrates the student part (0:00 to 1:20), and Nandini narrates the teacher part and the close (1:20 to 2:00). One voice for the whole video also works.

### Before you record

Stop any server that is already running, then run these in order:

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

- Open http://localhost:8000 in a browser window at least 1280×800. Hide the bookmarks bar and close other tabs.
- Turn on cursor highlighting in your screen recorder if it has it, so viewers can follow clicks.
- Zoom the browser to 110% if the text looks small in the recording.
- Practise once. **Start guided demo** resets the four demo students, so a retake takes one click.
- The numbers below come from the scripted demo. If anything on screen differs in your practice run, say the number you see.

---

## The script

| Time | Screen | Do this | Point to (zoom or circle in the edit) | Say |
|---|---|---|---|---|
| **0:00–0:12** | Landing page | Nothing. Let the page settle | The headline *"Your tutor knows the answer was wrong. Ours knows why."* | **K:** "AI tutors answer questions, but don't track what a student understands. We're Works Locally, and this is Differential: a Class 10 Python tutor that reads *why* a student is wrong." |
| **0:12–0:20** | Landing page | Click **Start guided demo** | The guide bar at the bottom | **K:** "One rule: the AI interprets, the code decides. The AI never marks answers, sets scores or picks questions." |
| **0:20–0:40** | **Step 1: Student A** | Click **Submit answer**, then scroll to the result | The answer "5 times", the quoted reasoning, **30% → 5%**, then the thinking panel (72% and 24%) | **K:** "The loop runs four times. Student A says five: *'it counts up to and including 5'*. A local model names that misconception, quoting A's own words. Code drops mastery from 30 to 5 percent, and picks a question to test that belief." |
| **0:40–0:52** | **Step 2: Student B** | **Next step**, then **Submit answer** | The different diagnosis | **K:** "Student B gives the same wrong answer, but says *'the 5 says how many times'*. Different belief, so a different diagnosis and a different next question." |
| **0:52–1:02** | **Step 3: Student C** | **Next step**, then **Submit answer** | "The answer is right, but the reason isn't", **30% → 30%** | **K:** "Student C is right, but says it's always one less than the stop number. That breaks on other loops, so mastery doesn't move." |
| **1:02–1:12** | **Step 4: Student D** | **Next step**. Show question 1 of 8, then cut to the completion banner, then scroll to the concept map | "Diagnostic: question 1 of 8", then the concept map with red **Traversing a list** and grey "Not assessed" | **K:** "Student D takes an eight-question adaptive diagnostic. Mastery is tracked on a concept graph of the syllabus, and changes spread along prerequisites." |
| **1:12–1:20** | **Step 5: Student D** | **Next step**, then **Next question** | The **Generated question** badge and "weakest concept" in the thinking panel | **K:** "Next, code targets D's weakest concept with a generated question. Code computed its answer, and Elo ratings pick the right difficulty." |
| **1:20–1:32** | **Step 6: Teacher**, then **Step 7: Student C** | Submit D's answer, **Next step**, click **Jump 7 days**, **Next step**, scroll to **Reviews due** | Reviews due rising, then "for loops with range, recall 3%" | **N:** "Every answer also schedules a review on a forgetting curve. Jump a week ahead, recall fades, and C's loop concept comes back for review." |
| **1:32–1:50** | **Step 8: Teacher** | **Next step**, then scroll slowly down the dashboard | The **Simulated class** label, Biggest class gaps, Shared misconceptions, Root causes, then the heatmap | **N:** "For teachers, here's a simulated class of thirty made-up students. The dashboard ranks the biggest gaps, groups students who share a misconception, and traces low scores back to the prerequisite behind them, so the teacher knows what to reteach on Monday." |
| **1:50–2:00** | **Step 9: Close** | **Next step** | 18 of 18, 30 of 30, 0.8 s | **N:** "On thirty held-out written test cases, it identified every misconception, in under a second, fully offline on one PC. Differential: it knows why. Thank you." |

**Spoken words:** about 270, so roughly 2.3 words a second. If you run long, swap in the "Shorter lines" below.

---

## Cut list for the edit

| Time in video | What to cut or speed up |
|---|---|
| 0:20–0:40 | Cut the wait while the answer submits. Keep the scroll to the result card. |
| 0:40–0:52 | Show only the result card. Cut the scroll back up. |
| 1:02–1:12 | **Biggest cut.** Show question 1 of 8 for about 2 seconds, then jump straight to the completion banner and the concept map. Optionally show questions 2 to 8 at 8× speed for 2 seconds. |
| 1:20–1:32 | Cut the account switching. Keep the **Jump 7 days** click and the Reviews due list. You don't need to show C answering the review. |
| 1:32–1:50 | Scroll at an even speed. Pause about 3 seconds each on gaps, shared misconceptions and root causes. Skip **Draft a plan** to save time. |

---

## Shorter lines (if you're over 2:00)

Use these in place of the full lines:

- **0:20–0:40:** "Student A says five: *'up to and including 5'*. The model names that belief. Code drops mastery to 5 percent and tests it next."
- **1:32–1:50:** "Here's a simulated class of thirty made-up students. The dashboard shows the biggest gaps, shared misconceptions and the prerequisite behind them."
- **1:50–2:00:** "On thirty held-out written test cases, it identified every misconception, in under a second, offline. Thank you."

---

## Keep it accurate on camera

- **Say "simulated class"** every time the dashboard is on screen. The page also shows the label.
- **The accuracy result is from written test cases,** not real students. The close says "written test cases" for this reason, so don't shorten it to "students".
- **The generated question** was made ahead of time, not live for Student D. "Code targets D's weakest concept with a generated question" is accurate; "it just wrote this question for D" is not.
- **"Diagnosis status: cached"** may show in the thinking panel because `warm_demo` ran the answers through the real model beforehand. If a judge asks, say so.
- **Don't edit a prefilled answer** during recording. It goes to the live model and can change the questions that follow.

---

## Requirement checklist

| Requirement in the brief | Where it appears | Time |
|---|---|---|
| Diagnostic test | Student D, question 1 of 8 and the completion banner | 1:02 |
| Concept graph for one syllabus | Student D's concept map | 1:06 |
| Learner model updated after every answer | Mastery before and after for A, B and C | 0:20–1:02 |
| Question generation targeted at weak concepts, with difficulty calibration | Generated question badge and "weakest concept", Elo | 1:12 |
| Misconception detection from reasoning | A and B: same answer, different diagnoses. C: right answer, wrong reason | 0:20–1:02 |
| Spaced-repetition scheduling | Jump 7 days and C's review | 1:20 |
| Teacher dashboard of class-wide gaps | Gaps, shared misconceptions, root causes, heatmap | 1:32 |
