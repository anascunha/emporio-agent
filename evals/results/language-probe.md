# Language drift experiment — 2026-10-31

`python -m evals.language_probe --model claude-haiku-5-5 --runs 5`

**Question:** evaluation case 16 failed because Claude Haiku 5.5 answered an English-speaking
customer in Portuguese. Is that caused by the Portuguese data the tools return?

**Finding:** yes, but not only the long manual sections. Even a one-line catalog result
(Portuguese product name, R$ prices) is enough for Haiku to switch to Portuguese.
Reinforcing the rule at the end of the system prompt helped little; a short
per-message system instruction, added in code after each customer message with the
detected language, removed the drift entirely.

| Question type | Variant | Answered in Portuguese | Called get_policy |
|---|---|---|---|
| catalog (short PT product data) | prompt rule only | 5/5 | 0/5 |
| policy (long PT manual text) | prompt rule only | 4/5 | 5/5 |
| catalog + policy | prompt rule only | 4/5 | 5/5 |
| catalog (short PT product data) | per-message language hint | **0/5** | 0/5 |
| policy (long PT manual text) | per-message language hint | **0/5** | 5/5 |
| catalog + policy | per-message language hint | **0/5** | 5/5 |

Earlier run with an extra reminder at the end of the system prompt instead of the
per-message hint: 9/15 answers still in Portuguese (vs. 13/15 without it).
