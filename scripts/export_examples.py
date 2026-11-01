"""Export example conversations from a saved evaluation run (no API calls).

The evaluation stores every conversation, tool call and judge score in
evals/results/*.json. This script turns selected ones into Markdown:

- examples/NN-*.md: one real conversation each, from the default model;
- examples/model-comparison.md: the same questions answered by every model tested.

    uv run python scripts/export_examples.py
    uv run python scripts/export_examples.py --run evals/results/run2-judge-and-prompt-fixes.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN = ROOT / "evals" / "results" / "run2-judge-and-prompt-fixes.json"
EXAMPLES_DIR = ROOT / "examples"
MAIN_MODEL = "anthropic:claude-sonnet-5-5"

# (output file, case id, title)
EXAMPLES = [
    ("01-catalog-price-range", "01-catalog-price-range", "Catalog search by category and budget"),
    ("02-promotion-and-pix", "03-active-promotion-no-pix-stacking", "Active promotion: original price, discount, no PIX stacking"),
    ("03-order-status-with-verification", "10-late-order-with-verification", "Order status: identity check, then a late delivery"),
    ("04-return-expired-but-warranty", "11-return-expired-but-warranty", "Non-trivial: regret window expired, defect still under the legal warranty"),
    ("05-english-speaking-customer", "16-english-customer", "English-speaking customer: price and installments answered in English"),
]
COMPARISON_CASES = [
    "03-active-promotion-no-pix-stacking",
    "11-return-expired-but-warranty",
    "15-jailbreak-discount",
    "16-english-customer",
]
CRITERIA = ["grounding", "tone", "helpfulness", "policy_adherence"]


def render_turns(turns: list[dict], heading: str = "") -> list[str]:
    lines = []
    for turn in turns:
        lines += [f"**Customer:** {turn['customer']}", ""]
        for tool in turn["tools"]:
            args = json.dumps(tool["arguments"], ensure_ascii=False)
            lines.append(f"> 🔧 `{tool['name']}({args})`")
        if turn["tools"]:
            lines.append("")
        lines += [f"**Mel{heading}:** {turn['mel']}", ""]
    return lines


def verdict(result: dict) -> str:
    status = "✅ all checks passed" if result["passed"] else "❌ failed: " + "; ".join(
        c["check"] for c in result["checks"] if not c["passed"]
    )
    judge = result.get("judge")
    if judge:
        status += " · judge " + ", ".join(f"{k} {judge[k]}/5" for k in CRITERIA)
    return status


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    args = parser.parse_args()

    data = json.loads(args.run.read_text(encoding="utf-8"))
    runs = {model: {r["case"]: r for r in results} for model, results in data["runs"].items()}
    source = args.run.relative_to(ROOT).as_posix()
    EXAMPLES_DIR.mkdir(exist_ok=True)

    for filename, case, title in EXAMPLES:
        result = runs[MAIN_MODEL][case]
        model = MAIN_MODEL.split(":", 1)[1]
        lines = [
            f"# {title}",
            "",
            f"_Model: `{model}` · exported from the evaluation run `{source}` (case `{case}`) · {verdict(result)}_",
            "",
            *render_turns(result["turns"]),
        ]
        (EXAMPLES_DIR / f"{filename}.md").write_text("\n".join(lines), encoding="utf-8")

    lines = [
        "# Same questions, every model tested",
        "",
        f"Real answers exported from the evaluation run `{source}`. Each block is a fresh",
        "conversation; the line under each model gives the automatic checks and the LLM-judge scores.",
        "",
        "> Note: this run predates two fixes. The per-message language hint (decision #41) later",
        "> made Claude Haiku pass the English case, and the search fixes (#40) improved product",
        "> lookups for small models. In evaluation run 3 all three Claude models passed 16/16 checks.",
        "",
    ]
    for case in COMPARISON_CASES:
        lines += [f"## `{case}`", ""]
        for model, results in runs.items():
            result = results[case]
            lines += [f"### `{model}`", "", f"_{verdict(result)}_", "", *render_turns(result["turns"])]
        lines.append("---\n")
    (EXAMPLES_DIR / "model-comparison.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {len(EXAMPLES)} examples and model-comparison.md to {EXAMPLES_DIR}")


if __name__ == "__main__":
    main()
