import json
from datetime import date

import pytest

from emporio.config import DATA_DIR, DEFAULT_TODAY
from emporio.policies import PolicyManual
from emporio.store import Order
from emporio.tools import MAX_FAILED_VERIFICATIONS, ToolExecutor, assess_return


@pytest.fixture
def tools(store, tmp_path) -> ToolExecutor:
    return ToolExecutor(store, PolicyManual(DATA_DIR / "politicas_da_loja.md"), tmp_path)


def call(tools, name, **arguments):
    return json.loads(tools.execute(name, arguments))


# ----- catalog -----------------------------------------------------------------------


def test_category_enum_comes_from_the_data(tools):
    search = next(s for s in tools.schemas if s["name"] == "search_products")
    assert "Violões" in search["parameters"]["properties"]["category"]["enum"]


def test_price_question_returns_formatted_full_price(tools):
    result = call(tools, "search_products", query="Takamine GD20")
    top = result["products"][0]
    assert top["name"].startswith("Takamine GD20")
    assert top["price"] == "R$ 2.199,00"
    assert "promotion" not in top  # the promotion rows for this product are inactive
    assert top["max_installments"] == "12x R$ 183,25"


def test_promotional_price_shows_original_price_and_discount(tools):
    top = call(tools, "search_products", query="Crafter HT-100")["products"][0]
    assert top["list_price"] == "R$ 2.399,00"
    assert top["promotion"].endswith("18% off")
    assert top["price"] == "R$ 1.967,18"


def test_out_of_stock_product_is_reported_separately(tools):
    result = call(tools, "search_products", query="Giannini GF-3D")
    assert result["unavailable_matches"][0]["availability"] == "out_of_stock"
    assert all(p["availability"] == "available" for p in result["products"])


def test_empty_category_explains_itself(tools):
    result = call(tools, "search_products", category="Cordas Orquestrais")
    assert result["products"] == []
    assert "No products in this category" in result["note"]


def test_details_of_unavailable_product_suggest_alternatives(tools, store):
    gf3d = next(p for p in store.products.values() if p.name.startswith("Giannini GF-3D"))
    details = call(tools, "get_product_details", product_id=gf3d.id)
    assert details["alternatives"]
    assert all(a["availability"] == "available" for a in details["alternatives"])


# ----- orders ------------------------------------------------------------------------


def test_order_status_needs_matching_contact(tools):
    ok = call(tools, "get_order_status", order_id=1, contact="pedro.oliveira@jmail.com")
    assert ok["status"] == "delivered" and ok["tracking_code"] == "BRAB1234567BR"
    denied = call(tools, "get_order_status", order_id=1, contact="someone@else.com")
    assert "error" in denied and "status" not in denied


def test_late_shipment_gets_a_warning(tools):
    # Order 8: shipped, estimated delivery 2026-02-28, "today" is 2026-03-23.
    result = call(tools, "get_order_status", order_id=8, contact="(67) 99654-7821")
    assert "23 days ago" in result["delay_warning"]


def test_verification_locks_after_repeated_failures(tools):
    for _ in range(MAX_FAILED_VERIFICATIONS):
        call(tools, "get_order_status", order_id=1, contact="wrong@mail.com")
    locked = call(tools, "get_order_status", order_id=1, contact="pedro.oliveira@jmail.com")
    assert "Too many failed attempts" in locked["error"]


def test_missing_arguments_return_an_error_instead_of_raising(tools):
    assert "Missing: contact" in call(tools, "get_order_status", order_id=1)["error"]


def test_null_arguments_are_treated_as_missing(tools):
    # Found by the evaluation: qwen2.5:3b sent contact=null and the executor crashed.
    assert "Missing: contact" in call(tools, "get_order_status", order_id=8, contact=None)["error"]


# ----- returns (manual sections 4 and 8) ---------------------------------------------


def delivered(order_date, delivery):
    return Order(1, 1, date.fromisoformat(order_date), "delivered", 100.0, "pix", None,
                 date.fromisoformat(delivery), None)


def test_regret_within_seven_days_of_receipt():
    result = assess_return(delivered("2026-03-10", "2026-03-18"), "regret", DEFAULT_TODAY)
    assert result["outcome"] == "eligible"


def test_regret_after_seven_days_points_to_warranty():
    result = assess_return(delivered("2026-02-03", "2026-02-17"), "regret", DEFAULT_TODAY)
    assert result["outcome"] == "deadline_expired"
    assert "legal warranty" in result["still_possible"]


def test_defect_exchange_counts_from_purchase_then_legal_warranty_from_receipt():
    # Bought 48 days ago (no store exchange), received 34 days ago (legal warranty).
    result = assess_return(delivered("2026-02-03", "2026-02-17"), "defect", DEFAULT_TODAY)
    assert result["outcome"] == "legal_warranty"
    assert "56 days left" in result["explanation"]


def test_defect_within_thirty_days_is_a_store_exchange():
    result = assess_return(delivered("2026-03-01", "2026-03-05"), "defect", DEFAULT_TODAY)
    assert result["outcome"] == "store_exchange"


def test_defect_after_legal_warranty_goes_to_manufacturer():
    result = assess_return(delivered("2025-10-15", "2025-10-25"), "defect", DEFAULT_TODAY)
    assert result["outcome"] == "manufacturer_warranty"


def test_return_on_undelivered_order(tools):
    # Order 13 is pending and belongs to customer 8.
    result = call(tools, "check_return_options", order_id=13, contact="fernanda.ribeiro@coldmail.com", reason="regret")
    assert result["outcome"] == "not_delivered_yet"


# ----- policies and escalation -------------------------------------------------------


def test_policy_tool_returns_section(tools):
    assert "09:00 às 18:00" in call(tools, "get_policy", topic="opening_hours")["text"]


def test_escalation_is_recorded_with_protocol(tools, tmp_path):
    result = call(tools, "escalate_to_human", category="complaint", summary="Late delivery", order_id=8)
    assert result["protocol"].startswith("EM-20260323-")
    lines = (tmp_path / "escalations.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[0])["protocol"] == result["protocol"]


def test_price_filter_is_spelled_out_and_impossible_range_rejected(tools):
    # Found in manual testing: qwen2.5:3b sent min_price=1000 for "under R$ 1,000".
    result = call(tools, "search_products", category="Violões", min_price=1000)
    assert result["price_filter_applied"] == "from R$ 1.000,00"
    assert "up to R$ 1.000,00" == call(tools, "search_products", category="Violões", max_price=1000)["price_filter_applied"]
    assert "min_price is greater" in call(tools, "search_products", min_price=1000, max_price=999.99)["error"]
