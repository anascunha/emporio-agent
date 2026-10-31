"""Compare models on the evaluation cases.

    python -m evals.run                                  # default model list
    python -m evals.run --models anthropic:claude-sonnet-5-5 ollama:qwen2.5:3b
    python -m evals.run --cases 11 16 --no-judge

Each case runs as a fresh conversation. Results go to evals/results/<timestamp>.md
(summary) and .json (full transcripts, tool calls, checks and judge scores).
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path

from emporio.agent import create_agent
from emporio.config import load_settings
from emporio.prompts import build_system_prompt

from .checks import check_turn
from .judge import CRITERIA, JUDGE_MODEL, judge

EVALS_DIR = Path(__file__).resolve().parent
DEFAULT_MODELS = [
    "anthropic:claude-sonnet-5-5",
    "anthropic:claude-haiku-5-5",
    "anthropic:claude-opus-5-5",
    "ollama:qwen2.5:3b",
    "ollama:llama3.2",
]

# USD per million tokens: (input, output). Cache reads cost 10% of input, writes 125%.
PRICES = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}


def cost(model: str, usage: dict) -> float:
    if model not in PRICES:
        return 0.0  # local models
    price_in, price_out = PRICES[model]
    return (
        usage.get("input", 0) * price_in
        + usage.get("cache_read", 0) * price_in * 0.10
        + usage.get("cache_write", 0) * price_in * 1.25
        + usage.get("output", 0) * price_out
    ) / 1_000_000


def run_case(settings, provider: str, model: str, case: dict) -> dict:
    agent = create_agent(settings, provider, model)
    turns, checks, latencies = [], [], []
    error = None
    for spec in case["turns"]:
        start = time.perf_counter()
        try:
            reply = agent.reply(spec["message"])
        except Exception as exc:  # record API/model failures as a failed case
            error = f"{type(exc).__name__}: {exc}"
            break
        latencies.append(time.perf_counter() - start)
        turns.append((spec["message"], reply))
        checks.extend(check_turn(spec, reply))
    return {
        "case": case["id"],
        "passed": error is None and all(c["passed"] for c in checks),
        "checks": checks,
        "error": error,
        "latencies": latencies,
        "usage": dict(agent.session.usage),
        "turns": turns,
    }


def summarize(model: str, results: list[dict]) -> dict:
    checks = [c for r in results for c in r["checks"]]
    tool = [c for c in checks if c["kind"] == "tool"]
    content = [c for c in checks if c["kind"] == "content"]
    latencies = [lat for r in results for lat in r["latencies"]]
    usage: dict[str, int] = {}
    for r in results:
        for key, value in r["usage"].items():
            usage[key] = usage.get(key, 0) + value
    scores = [r["judge"] for r in results if r.get("judge")]
    return {
        "cases_passed": sum(r["passed"] for r in results),
        "cases": len(results),
        "tool_accuracy": sum(c["passed"] for c in tool) / len(tool) if tool else None,
        "content_accuracy": sum(c["passed"] for c in content) / len(content) if content else None,
        "avg_latency": sum(latencies) / len(latencies) if latencies else None,
        "cost_usd": cost(model, usage),
        "judge": {k: sum(s[k] for s in scores) / len(scores) for k in CRITERIA} if scores else None,
    }


def pct(value):
    return "–" if value is None else f"{value:.0%}"


def write_report(path: Path, runs: dict[str, list[dict]], summaries: dict[str, dict], cases: list[dict]):
    lines = [
        f"# Model evaluation — {datetime.now():%Y-%m-%d %H:%M}",
        "",
        f"{len(cases)} cases, each a fresh conversation. Judge: `{JUDGE_MODEL}` (scores 1–5).",
        "",
        "| Model | Cases passed | Tool checks | Content checks | Grounding | Tone | Helpfulness | Policy | Avg latency/turn | Cost (all cases) |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name, s in summaries.items():
        j = s["judge"] or {}
        judge_cols = [f"{j[k]:.1f}" if k in j else "–" for k in CRITERIA]
        latency = "–" if s["avg_latency"] is None else f"{s['avg_latency']:.1f}s"
        lines.append(
            f"| `{name}` | {s['cases_passed']}/{s['cases']} | {pct(s['tool_accuracy'])} | "
            f"{pct(s['content_accuracy'])} | {' | '.join(judge_cols)} | {latency} | ${s['cost_usd']:.3f} |"
        )
    lines += ["", "## Per case", "", "| Case | " + " | ".join(f"`{m}`" for m in runs) + " |",
              "|---|" + "---|" * len(runs)]
    for case in cases:
        row = []
        for results in runs.values():
            r = next(r for r in results if r["case"] == case["id"])
            row.append("✅" if r["passed"] else "❌")
        lines.append(f"| {case['id']} | " + " | ".join(row) + " |")
    lines += ["", "## Failures", ""]
    for name, results in runs.items():
        for r in results:
            failed = [c for c in r["checks"] if not c["passed"]]
            if r["error"] or failed:
                lines.append(f"- `{name}` · **{r['case']}**: " + (r["error"] or "; ".join(
                    f"{c['check']}" + (f" ({c['detail']})" if c["detail"] else "") for c in failed)))
            if r.get("judge") and r["judge"].get("comment") and min(r["judge"][k] for k in CRITERIA) <= 3:
                lines.append(f"  - judge: {r['judge']['comment']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def to_json(results: list[dict]) -> list[dict]:
    out = []
    for r in results:
        r = dict(r)
        r["turns"] = [
            {
                "customer": message,
                "tools": [{"name": e.name, "arguments": e.arguments, "result": e.result} for e in reply.tool_events],
                "mel": reply.text,
            }
            for message, reply in r["turns"]
        ]
        out.append(r)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS, help="provider:model entries")
    parser.add_argument("--cases", nargs="+", help="case id prefixes to run (e.g. 03 11)")
    parser.add_argument("--no-judge", action="store_true", help="skip the LLM judge")
    args = parser.parse_args()

    settings = load_settings()
    cases = json.loads((EVALS_DIR / "cases.json").read_text(encoding="utf-8"))
    if args.cases:
        cases = [c for c in cases if any(c["id"].startswith(p) for p in args.cases)]

    judge_client = None
    if not args.no_judge:
        if os.getenv("ANTHROPIC_API_KEY"):
            import anthropic

            judge_client = anthropic.Anthropic()
        else:
            print("ANTHROPIC_API_KEY not set: skipping the LLM judge.")

    runs: dict[str, list[dict]] = {}
    summaries: dict[str, dict] = {}
    judge_usage = {"input": 0, "output": 0}
    for entry in args.models:
        provider, model = entry.split(":", 1)
        if provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
            print(f"Skipping {entry}: ANTHROPIC_API_KEY not set.")
            continue
        print(f"\n== {entry}")
        results = []
        for case in cases:
            result = run_case(settings, provider, model, case)
            if judge_client and result["turns"]:
                result["judge"], usage = judge(
                    judge_client, case["description"], result["turns"], build_system_prompt(settings.today)
                )
                for key in judge_usage:
                    judge_usage[key] += usage[key]
            print(f"  {'PASS' if result['passed'] else 'FAIL'}  {case['id']}")
            results.append(result)
        runs[entry] = results
        summaries[entry] = summarize(model, results)

    if not runs:
        print("Nothing was run.")
        return
    results_dir = EVALS_DIR / "results"
    results_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    write_report(results_dir / f"{stamp}.md", runs, summaries, cases)
    (results_dir / f"{stamp}.json").write_text(
        json.dumps(
            {
                "summaries": summaries,
                "judge_cost_usd": cost(JUDGE_MODEL, judge_usage),
                "runs": {k: to_json(v) for k, v in runs.items()},
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    print(f"\nReport: {results_dir / f'{stamp}.md'}")


if __name__ == "__main__":
    main()
