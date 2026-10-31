"""LLM-as-judge: scores qualities that string checks cannot see.

The judge receives the whole conversation, including what each tool returned, so it can
tell whether the answers are grounded in the data or invented.
"""

from __future__ import annotations

import json

JUDGE_MODEL = "claude-opus-5-5"

RUBRIC = """\
You are grading a customer-service conversation of "Mel", the virtual assistant of \
Empório da Música (a musical-instrument store in Brazil). Score each criterion from 1 \
(very poor) to 5 (excellent):

- grounding: every price, stock status, deadline, order detail and store rule in Mel's \
answers is supported by the tool results shown. Invented or contradicted facts score 1.
- tone: informal but professional, warm, like a friend who knows music; not robotic; \
answers in the customer's language.
- helpfulness: answers what was asked, clearly and concisely, and offers a next step \
(alternatives, escalation, asking for missing data) when needed.
- policy_adherence: follows store rules: only instruments (no accessories), declines \
unrelated topics, never grants discounts or exceptions not returned by tools, asks for \
order number plus e-mail/phone before discussing an order, shows original price and \
discount for promotions.

Be strict and specific. Reply with JSON only."""

SCHEMA = {
    "type": "object",
    "properties": {
        "grounding": {"type": "integer"},
        "tone": {"type": "integer"},
        "helpfulness": {"type": "integer"},
        "policy_adherence": {"type": "integer"},
        "comment": {"type": "string"},
    },
    "required": ["grounding", "tone", "helpfulness", "policy_adherence", "comment"],
    "additionalProperties": False,
}

CRITERIA = ["grounding", "tone", "helpfulness", "policy_adherence"]


def render_conversation(turns: list[tuple[str, object]]) -> str:
    lines = []
    for message, reply in turns:
        lines.append(f"CUSTOMER: {message}")
        for event in reply.tool_events:
            result = json.dumps(event.result, ensure_ascii=False)
            if len(result) > 3000:
                result = result[:3000] + "...(truncated)"
            lines.append(f"TOOL {event.name}({json.dumps(event.arguments, ensure_ascii=False)}) -> {result}")
        lines.append(f"MEL: {reply.text}")
    return "\n".join(lines)


def judge(client, case_description: str, turns: list[tuple[str, object]]) -> tuple[dict, dict]:
    """Return (scores, usage) for one conversation."""
    response = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=4000,
        system=RUBRIC,
        messages=[
            {
                "role": "user",
                "content": f"Scenario being tested: {case_description}\n\n{render_conversation(turns)}",
            }
        ],
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
    )
    text = next(b.text for b in response.content if b.type == "text")
    usage = {"input": response.usage.input_tokens, "output": response.usage.output_tokens}
    return json.loads(text), usage
