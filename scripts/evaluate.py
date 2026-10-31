import argparse
import json
import sys
import time
from pathlib import Path

from agent.content import Content, load_content
from agent.diagnose import diagnose
from agent.llm import LLMClient, OllamaClient

CONTENT_DIR = Path("content")
RESULTS_PATH = Path("eval/results.json")


def load_samples(content_dir: Path, split: str) -> list[dict]:
    samples = json.loads((content_dir / "eval_samples.json").read_text(encoding="utf-8"))
    return [sample for sample in samples if sample["split"] == split]


def score(rows: list[dict]) -> dict:
    total = len(rows)
    expecting = [row for row in rows if row["expected_misconception_id"]]
    per_misconception: dict[str, dict[str, int]] = {}
    for row in expecting:
        entry = per_misconception.setdefault(row["expected_misconception_id"], {"correct": 0, "total": 0})
        entry["total"] += 1
        if row["misconception_id"] == row["expected_misconception_id"]:
            entry["correct"] += 1
    correct_ids = sum(entry["correct"] for entry in per_misconception.values())
    return {
        "count": total,
        "error_type_accuracy": sum(r["error_type"] == r["expected_error_type"] for r in rows) / total if total else 0,
        "misconception_accuracy": correct_ids / len(expecting) if expecting else 0,
        "per_misconception": per_misconception,
        "avg_seconds": sum(r["seconds"] for r in rows) / total if total else 0,
    }


def run(samples: list[dict], content: Content, llm: LLMClient) -> list[dict]:
    rows = []
    for sample in samples:
        question = content.questions[sample["question_id"]]
        option = next(o for o in question.options if o.id == sample["option_id"])
        started = time.perf_counter()
        result = diagnose(question, option, option.is_correct, sample["reasoning"], content, llm)
        rows.append(
            {
                "id": sample["id"],
                "reasoning": sample["reasoning"],
                "expected_error_type": sample["expected_error_type"],
                "expected_misconception_id": sample["expected_misconception_id"],
                "error_type": result.diagnosis.error_type,
                "misconception_id": result.diagnosis.misconception_id,
                "status": result.status,
                "seconds": time.perf_counter() - started,
            }
        )
    return rows


def merge_results(path: Path, key: str, value: dict) -> None:
    results = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    results[key] = value
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure diagnosis accuracy on written test cases.")
    parser.add_argument("--think", choices=["on", "off"], default="off")
    parser.add_argument("--split", choices=["tune", "heldout"], default="tune")
    args = parser.parse_args()

    content = load_content(CONTENT_DIR)
    llm = OllamaClient(think=args.think == "on")
    rows = run(load_samples(CONTENT_DIR, args.split), content, llm)
    summary = score(rows)
    summary["mistakes"] = [
        row
        for row in rows
        if row["error_type"] != row["expected_error_type"]
        or row["misconception_id"] != row["expected_misconception_id"]
    ]
    merge_results(RESULTS_PATH, f"{args.split}_{args.think}", summary)

    sys.stdout.reconfigure(encoding="utf-8")
    print(f"split={args.split} think={args.think} samples={summary['count']}")
    print(f"error type accuracy: {summary['error_type_accuracy']:.0%}")
    print(f"misconception accuracy: {summary['misconception_accuracy']:.0%}")
    print(f"average time: {summary['avg_seconds']:.1f} seconds")
    for row in summary["mistakes"]:
        print(
            f"  MISS {row['id']}: expected {row['expected_error_type']}/{row['expected_misconception_id']}, "
            f"got {row['error_type']}/{row['misconception_id']} ({row['status']}): {row['reasoning']}"
        )


if __name__ == "__main__":
    main()
