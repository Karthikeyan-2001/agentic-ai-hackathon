# Demo video script

About 4 minutes. The guided demo fills in every answer, so on camera you only click **Submit answer**, **Next question** and **Next step**.

## Before you record

Stop any server that's already running, because an old one keeps serving old content. Then run these once, in order.

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

- `warm_demo` stops with an error if any answer or diagnosis differs from the script. If it finishes, the flow below will match.
- Open http://localhost:8000 in a browser window at least 1280×800, and hide the bookmarks bar.
- Practise once. **Start guided demo** resets the four demo students every time, so a retake is one click.
- The buttons on long questions sit below the guide bar. Scroll down to reach **Submit answer**.

## The flow

| Time | Step on screen | Do this | Point to | Say |
|---|---|---|---|---|
| 0:00 | Landing page | Nothing yet | The headline | "Generic AI tutors answer questions, but they don't track what a student actually understands. Differential is a Class 10 Python tutor that reads a student's reasoning, and it works like a doctor: it forms competing explanations, then asks the question that best separates them." |
| 0:20 | Landing page | Click **Start guided demo** | | "One rule runs through the whole system: the LLM interprets and the code decides. It never sets a score, marks an answer or chooses a question." |
| 0:30 | **1. Student A** | Submit, then scroll to the result | "You wrote…" quote, mastery 30% → 5%, the steps in the thinking panel | "A answers 5 times and says it counts up to and including 5. The model matches that to a known misconception, and it has to quote A's own words. Code marked the answer and updated mastery." |
| 0:55 | **1. Student A** | **Next question**, then Submit | `range_includes_stop` falling from 72% to 36%, mastery 5% → 27% | "The next question was picked to test that belief. A gets it right, so the probability falls and mastery rises." |
| 1:10 | **2. Student B** | **Next step**, then Submit | The different diagnosis | "B gives the same wrong answer, but says the 5 says how many times. A tutor that only checks answers would treat A and B alike. Here B gets a different diagnosis and a different next question." |
| 1:30 | **3. Student C** | **Next step**, then Submit | "The answer is right, but the reason isn't", mastery 30% → 30% | "C gets the right answer, but says it's always one less than the stop number. That reasoning breaks for other loops, so it doesn't count towards mastery." |
| 1:45 | **3. Student C** | **Next question**, then Submit | Mastery 30% → 69% | "When C's reasoning holds up on a different start value, mastery moves." |
| 1:55 | **4. Student D** | **Next step**, Submit through questions 1 to 8 quickly | "Diagnostic: question N of 8", then the completion banner | "Student D takes the 8-question diagnostic. Each question goes to the concept the tutor is least certain about. On the last one D admits to guessing, and that reads as a knowledge gap, not a misconception." |
| 2:20 | **4. Student D** | Scroll to the concept map | Green concepts, red Traversing a list, grey "Not assessed" | "This is the concept graph for the syllabus. Mastery is tracked per concept, and it spreads along the prerequisites." |
| 2:35 | **5. Student D** | **Next step**, **Next question** | The "Generated question" badge, "weakest concept" in the thinking panel | "Code picks D's weakest concept, then the question closest to a 60% chance of success, using Elo ratings. The model wrote this question ahead of time, and code worked out the correct answer. LLM-written code is never run." |
| 2:55 | **6. Teacher** | Submit D's answer, **Next step**, click **Jump 7 days** | "Live demo students", then reviews due rising | "Each answer also schedules a review on a forgetting curve. Moving the clock a week makes recall fall, so reviews come due." |
| 3:10 | **7. Student C** | **Next step**, scroll to Reviews due, then Submit | "for loops with range, recall 3%", "Review:" in the thinking panel, mastery 69% → 92% | "C's loop concept has faded, so the tutor brings it back before moving on." |
| 3:25 | **8. Teacher** | **Next step**, scroll down the page | The "Simulated class" label, biggest gaps, shared misconceptions, root causes | "This is a simulated class of 30 made-up students, to show how the dashboard works. It ranks the biggest gaps, groups students who share a misconception, and traces low scores back to the prerequisite behind them." |
| 3:45 | **8. Teacher** | Click **Draft a plan**, then scroll to the bottom | The plan, then Difficulty surprises | "It drafts a plan for Monday, which the teacher reviews. Further down, class results move each question's difficulty: this one was predicted at 1350 and now sits at 1476." |
| 4:00 | **9. Close** | **Next step**, then **Finish** | The results | "On 30 written test cases held out from tuning, it got the error type right 30 of 30 times and identified the misconception 18 of 18 times, in about 0.8 seconds on one PC. These aren't real students, and the same AI assistant that helped write the misconception list also wrote the test cases, so we treat this as a check that the system works, not proof of accuracy with real students." |

## Where each requirement appears

| Requirement in the brief | Step |
|---|---|
| A diagnostic test | 4: the 8-question counter and completion banner |
| A concept graph for one syllabus | 4: the concept map |
| A learner model that updates mastery after every answer | 1 to 5: the before and after mastery on every result |
| Generated questions targeted at weak concepts, with difficulty calibration | 5: the badge and reason. 8: the Elo moves |
| Misconceptions from reasoning, not just the wrong answer | 1, 2 and 3: same answer with different diagnoses, and a right answer with a wrong reason |
| Spaced-repetition scheduling | 6 and 7: the clock jump and C's review |
| A teacher dashboard of class-wide gaps | 8 |

## Keep it accurate on camera

- **"Diagnosis status: cached"** shows in the thinking panel because `warm_demo` ran these answers through the real model beforehand. That keeps the demo steady if Ollama stops. If you're asked, say so.
- **The generated question** was made ahead of time and is served to any student who needs it. It wasn't written live for Student D, so don't say it was.
- **Difficulty surprises** shows the largest moves so far. No question passes the 150-point flag in this flow, and the page says so.
- **Class numbers** on the dashboard are lower than on the landing page, because the 7-day jump has made recall fall. The landing page shows the class before the jump.
- **Editing a prefilled answer** sends it to the live model, which is a fair thing to show. It can change the questions that follow, and those will then appear empty. Press **Start guided demo** to go back to the script.
- **Back** returns to a step's account, but it doesn't undo answers. Use **Start guided demo** for a clean retake.
