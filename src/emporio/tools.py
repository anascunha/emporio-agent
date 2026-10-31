"""Tools the LLM can call, their JSON schemas, and a per-conversation executor.

The schemas are provider-neutral (name, description, JSON Schema parameters); each LLM
client adapts them to its own wire format. Tool results are JSON with prices already
formatted, so the model only has to explain them, never compute them.
"""

from __future__ import annotations

import json
import secrets
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .policies import TOPICS, PolicyManual
from .store import ORDER_STATUS, Order, Product, Store, describe_payment, installment_plans
from .text import brl

MAX_FAILED_VERIFICATIONS = 5
REGRET_DAYS = 7
DEFECT_EXCHANGE_DAYS = 30
LEGAL_WARRANTY_DAYS = 90

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "search_products",
        "description": (
            "Search the store catalog. Use it for any question about which instruments the "
            "store has, prices, promotions or availability. Returns only products that can "
            "be bought now, plus any unavailable product whose name matches the query. "
            "Price filters apply to the final (promotional) price."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Words from the product name, brand, model or specs, e.g. 'Takamine GD20', 'nylon', 'tenor elétrico'. Omit to list a category.",
                },
                "category": {
                    "type": "string",
                    "description": "Catalog category (Portuguese name). Violões = acoustic/classical guitars; Guitarras = electric guitars.",
                    "enum": [],  # filled from the data at runtime
                },
                "min_price": {"type": "number", "description": "Minimum price in BRL."},
                "max_price": {"type": "number", "description": "Maximum price in BRL."},
            },
        },
    },
    {
        "name": "get_product_details",
        "description": (
            "Full details of one product: specs, price, every installment option, availability "
            "and, if it cannot be bought, similar available alternatives."
        ),
        "parameters": {
            "type": "object",
            "properties": {"product_id": {"type": "integer"}},
            "required": ["product_id"],
        },
    },
    {
        "name": "get_order_status",
        "description": (
            "Status, items, tracking code and estimated delivery of an order. Requires the "
            "order number AND the e-mail or phone registered by the buyer; ask the customer "
            "for both before calling. Never guess them."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "integer"},
                "contact": {"type": "string", "description": "Buyer's registered e-mail or phone."},
            },
            "required": ["order_id", "contact"],
        },
    },
    {
        "name": "check_return_options",
        "description": (
            "Check which return, exchange or warranty options apply to an order today, "
            "computing the deadlines from the store policy. Same verification as "
            "get_order_status."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "integer"},
                "contact": {"type": "string", "description": "Buyer's registered e-mail or phone."},
                "reason": {
                    "type": "string",
                    "enum": ["regret", "defect", "preference"],
                    "description": "regret = changed their mind; defect = manufacturing defect; preference = exchange for another color/model/size.",
                },
            },
            "required": ["order_id", "contact", "reason"],
        },
    },
    {
        "name": "get_policy",
        "description": (
            "Read a section of the store policy manual. Use it for questions about the store "
            "itself (address, contacts, hours) and its rules (payment, returns, shipping, "
            "promotions, warranty, privacy, complaints). Topics: "
            + "; ".join(f"{t} = {desc}" for t, (_, desc) in TOPICS.items())
        ),
        "parameters": {
            "type": "object",
            "properties": {"topic": {"type": "string", "enum": list(TOPICS)}},
            "required": ["topic"],
        },
    },
    {
        "name": "escalate_to_human",
        "description": (
            "Register a case for the human team: complaints, return/exchange requests, "
            "shipping quotes, or anything you cannot resolve. Returns a protocol number. "
            "The team replies within 24 business hours."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": ["complaint", "return_request", "shipping_quote", "other"]},
                "summary": {"type": "string", "description": "What the customer needs, in one or two sentences."},
                "order_id": {"type": "integer"},
                "contact": {"type": "string", "description": "How the team can reach the customer, if given."},
            },
            "required": ["category", "summary"],
        },
    },
]


class ToolExecutor:
    """Runs tool calls for one conversation (keeps per-conversation state)."""

    def __init__(self, store: Store, manual: PolicyManual, runtime_dir: Path):
        self.store = store
        self.manual = manual
        self.runtime_dir = runtime_dir
        self.failed_verifications = 0
        self.schemas = _with_categories(TOOL_SCHEMAS, list(store.categories.values()))

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        """Run a tool and return its JSON result. Errors are returned, not raised, so
        the model can read them and recover (e.g. ask the customer for missing data)."""
        handler = getattr(self, f"_tool_{name}", None)
        if handler is None:
            result: dict[str, Any] = {"error": f"Unknown tool {name!r}."}
        else:
            try:
                result = handler(**arguments)
            except TypeError as exc:
                result = {"error": f"Invalid arguments for {name}: {exc}"}
            except (KeyError, ValueError) as exc:
                result = {"error": str(exc)}
        return json.dumps(result, ensure_ascii=False)

    # ----- catalog -------------------------------------------------------------------

    def _tool_search_products(
        self,
        query: str | None = None,
        category: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
    ) -> dict:
        found = self.store.search_products(query, category, min_price, max_price)
        result: dict[str, Any] = {"products": [self._summary(p) for p in found]}
        if query:
            # Unavailable products named by the customer are reported, so the agent can
            # say "out of stock / discontinued" and suggest alternatives (manual 7.3).
            unavailable = [
                p
                for p in self.store.search_products(query, category, include_unavailable=True, limit=3)
                if p.availability != "available"
            ]
            if unavailable:
                result["unavailable_matches"] = [self._summary(p) for p in unavailable]
        if category and not any(p.category == category for p in self.store.products.values()):
            result["note"] = "No products in this category are listed in the system right now."
        if not found and "unavailable_matches" not in result:
            result.setdefault("note", "No matching products.")
        return result

    def _tool_get_product_details(self, product_id: int) -> dict:
        product = self.store.products.get(int(product_id))
        if product is None:
            return {"error": f"Product {product_id} not found."}
        pricing = self.store.pricing(product)
        details = self._summary(product)
        details["specs"] = product.specs
        if product.description:
            details["description"] = product.description
        details["installment_options"] = [
            f"{p['installments']}x {brl(p['installment_value'])} (no interest)"
            for p in installment_plans(pricing["final_price"])
        ]
        if product.availability != "available":
            details["alternatives"] = [self._summary(p) for p in self._alternatives(product)]
        return details

    def _summary(self, product: Product) -> dict:
        pricing = self.store.pricing(product)
        summary: dict[str, Any] = {
            "product_id": product.id,
            "name": product.name,
            "category": product.category,
            "availability": product.availability,
        }
        if product.availability == "available":
            summary["units_in_stock"] = product.stock
        if pricing["promotion"]:
            summary["list_price"] = brl(pricing["list_price"])
            summary["promotion"] = (
                f"{pricing['promotion']['name']}: {pricing['promotion']['discount_percent']:g}% off"
            )
            summary["price"] = brl(pricing["final_price"])
            summary["pix_price"] = "PIX 5% discount does not apply to promotional prices"
        else:
            summary["price"] = brl(pricing["final_price"])
            summary["pix_price"] = brl(pricing["pix_price"])
        best = pricing["max_installments"]
        if best:
            summary["max_installments"] = f"{best['installments']}x {brl(best['installment_value'])}"
        return summary

    def _alternatives(self, product: Product, limit: int = 3) -> list[Product]:
        candidates = self.store.search_products(
            category=product.category,
            min_price=product.price * 0.6,
            max_price=product.price * 1.4,
            limit=100,
        )
        candidates.sort(key=lambda p: abs(p.price - product.price))
        return candidates[:limit]

    # ----- orders --------------------------------------------------------------------

    def _verified_order(self, order_id: int, contact: str) -> Order | dict:
        if self.failed_verifications >= MAX_FAILED_VERIFICATIONS:
            return {"error": "Too many failed attempts in this conversation. Ask the customer to contact the store team directly."}
        order = self.store.verify_order(int(order_id), contact)
        if order is None:
            self.failed_verifications += 1
            return {"error": "Could not find an order with this number for this e-mail/phone. Ask the customer to double-check both."}
        return order

    def _tool_get_order_status(self, order_id: int, contact: str) -> dict:
        order = self._verified_order(order_id, contact)
        if isinstance(order, dict):
            return order
        customer = self.store.customers[order.customer_id]
        result: dict[str, Any] = {
            "order_id": order.id,
            "customer_first_name": customer.name.split()[0],
            "order_date": order.order_date.isoformat(),
            "status": order.status,
            "status_meaning": ORDER_STATUS.get(order.status, order.status),
            "items": [
                {"name": self.store.products[pid].name, "quantity": qty}
                for pid, qty in order.items
                if pid in self.store.products
            ],
            "total": brl(order.total),
            "payment": describe_payment(order.payment_method),
        }
        if order.tracking_code:
            result["tracking_code"] = order.tracking_code
        if order.estimated_delivery:
            result["estimated_delivery"] = order.estimated_delivery.isoformat()
            if order.status == "shipped" and order.estimated_delivery < self.store.today:
                late = (self.store.today - order.estimated_delivery).days
                result["delay_warning"] = (
                    f"Estimated delivery passed {late} days ago. Apologize, share the tracking "
                    "code and offer to register the case with escalate_to_human."
                )
        if order.notes:
            result["notes"] = order.notes
        return result

    def _tool_check_return_options(self, order_id: int, contact: str, reason: str) -> dict:
        order = self._verified_order(order_id, contact)
        if isinstance(order, dict):
            return order
        return assess_return(order, reason, self.store.today)

    # ----- policies and escalation ---------------------------------------------------

    def _tool_get_policy(self, topic: str) -> dict:
        return {"topic": topic, "text": self.manual.get(topic)}

    def _tool_escalate_to_human(
        self,
        category: str,
        summary: str,
        order_id: int | None = None,
        contact: str | None = None,
    ) -> dict:
        protocol = f"EM-{self.store.today:%Y%m%d}-{secrets.token_hex(2).upper()}"
        record = {
            "protocol": protocol,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "category": category,
            "summary": summary,
            "order_id": order_id,
            "contact": contact,
        }
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        with (self.runtime_dir / "escalations.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return {"protocol": protocol, "response_time": "within 24 business hours"}


def assess_return(order: Order, reason: str, today: date) -> dict:
    """Apply manual sections 4 and 8 to one order. Pure function, easy to test."""
    if reason not in ("regret", "defect", "preference"):
        raise ValueError("reason must be one of: regret, defect, preference")
    result: dict[str, Any] = {"order_id": order.id, "reason": reason, "status": order.status}
    if order.status == "cancelled":
        result["outcome"] = "not_applicable"
        result["explanation"] = "The order was cancelled, so there is nothing to return."
        return result
    if order.status != "delivered":
        result["outcome"] = "not_delivered_yet"
        result["explanation"] = (
            "The order has not been delivered yet, so return deadlines have not started. "
            "Cancelling an order in progress is not covered by the manual: offer escalate_to_human."
        )
        return result

    received = order.estimated_delivery or order.order_date
    days_since_receipt = (today - received).days
    days_since_purchase = (today - order.order_date).days
    result.update(
        {
            "purchase_date": order.order_date.isoformat(),
            "receipt_date_estimate": received.isoformat(),
            "days_since_receipt": days_since_receipt,
            "days_since_purchase": days_since_purchase,
            "note": "Receipt date is the estimated delivery date; the team confirms the final decision.",
            "not_eligible_items": "Customized/set-up instruments, 'final sale' items and wind-instrument mouthpieces cannot be exchanged (manual 4.4).",
        }
    )

    if reason in ("regret", "preference"):
        within = days_since_receipt <= REGRET_DAYS
        result["deadline"] = f"{REGRET_DAYS} days after receipt"
        result["outcome"] = "eligible" if within else "deadline_expired"
        if reason == "regret":
            result["conditions"] = (
                "Original packaging, no signs of use, all accessories and manuals. Refund to the "
                "original payment method within 10 business days; the store pays return shipping."
            )
        else:
            result["conditions"] = (
                "Product in perfect condition and original packaging, subject to availability of "
                "the desired item; price differences are charged or refunded."
            )
        if not within:
            result["still_possible"] = (
                "If the product has a manufacturing defect, the 90-day legal warranty from receipt "
                "may still apply: check with reason='defect'."
            )
        return result

    # Defect: store exchange within 30 days of purchase (4.2), then the 90-day legal
    # warranty from receipt (8.1), then the manufacturer's own warranty (8.2).
    if days_since_purchase <= DEFECT_EXCHANGE_DAYS:
        result["outcome"] = "store_exchange"
        result["explanation"] = "Within 30 days of purchase: the store exchanges the defective product."
    elif days_since_receipt <= LEGAL_WARRANTY_DAYS:
        result["outcome"] = "legal_warranty"
        result["explanation"] = (
            "More than 30 days since purchase, so no direct store exchange, but still within the "
            f"90-day legal warranty ({LEGAL_WARRANTY_DAYS - days_since_receipt} days left). The "
            "warranty is claimed with the manufacturer and the store can intermediate on request."
        )
    else:
        result["outcome"] = "manufacturer_warranty"
        result["explanation"] = (
            "Legal warranty expired. Most manufacturers offer 6 months to 2 years; see the "
            "warranty certificate. The store can intermediate on request."
        )
    result["not_covered"] = "Misuse, drops, humidity, unauthorized modifications, natural wear, cosmetic damage."
    return result


def _with_categories(schemas: list[dict], categories: list[str]) -> list[dict]:
    """Copy the schemas, filling the category enum from the data."""
    filled = json.loads(json.dumps(schemas))
    for schema in filled:
        props = schema["parameters"].get("properties", {})
        if "category" in props and schema["name"] == "search_products":
            props["category"]["enum"] = categories
    return filled
