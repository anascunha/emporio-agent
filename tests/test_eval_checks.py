from emporio.agent import Reply, ToolEvent
from evals.checks import check_turn, detect_language


def reply(text, *tools):
    return Reply(text, [ToolEvent(name, {}, {}) for name in tools])


def test_checks_ignore_accents_and_case():
    spec = {"expect_tools": ["search_products"], "contains_any": ["esgotad", "indisponi"], "language": "pt"}
    results = check_turn(spec, reply("Poxa, o GF-3D está ESGOTADO no momento.", "search_products"))
    assert all(r["passed"] for r in results)


def test_forbidden_tool_and_forbidden_term_fail():
    spec = {"forbid_tools": ["get_order_status"], "not_contains": ["2x"]}
    results = check_turn(spec, reply("A derivada é 2x.", "get_order_status"))
    assert [r["passed"] for r in results] == [False, False]


def test_min_any_counts_distinct_terms():
    spec = {"contains_any": ["Yamaha C40", "Tagima Memphis", "Rozini"], "min_any": 2}
    assert not check_turn(spec, reply("Temos o Yamaha C40."))[0]["passed"]
    assert check_turn(spec, reply("Yamaha C40 ou Rozini RC-104."))[0]["passed"]


def test_language_detection():
    assert detect_language("Hi! The Yamaha F310 costs R$ 699,90 and you can pay in 6 installments.") == "en"
    assert detect_language("Oi! O Yamaha F310 está por R$ 699,90 e você pode parcelar em 6x.") == "pt"
