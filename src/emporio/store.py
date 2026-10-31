"""Read-only access to the store's operational data (CSV files) and its business rules.

Everything the agent states as a fact (price, discount, stock, installments, order
status) is computed here, in plain code, so it can be tested and never depends on the
LLM doing arithmetic or remembering rules.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

from .text import digits, fold, stem, tokens

PIX_DISCOUNT = 0.05
COMBINED_PAYMENT_MIN = 2000.00

# Manual item 3.1: (max installments in the tier, minimum installment value).
# The summary table says "minimum R$ 100" for everything; the detailed rule wins
# (docs/decisions.md #11).
INSTALLMENT_TIERS = [(3, 50.00), (6, 80.00), (12, 100.00)]

ORDER_STATUS = {
    "pending": "Order received, waiting for payment confirmation.",
    "confirmed": "Payment confirmed; the order is being prepared for shipping.",
    "shipped": "Order dispatched; it can be tracked with the tracking code.",
    "delivered": "Order delivered.",
    "cancelled": "Order cancelled.",
}

PAYMENT_METHODS = {
    "pix": "PIX",
    "debit": "debit card",
    "boleto": "bank slip (boleto)",
}

# Brands that appear in the catalog, plus Tama (only mentioned in a description).
# Used to detect descriptions that talk about a different product.
# Extra words a customer may use for each category, in Portuguese and English. The data
# is in Portuguese only, so without these "acoustic guitar" would match electric guitars.
CATEGORY_SYNONYMS = {
    "Guitarras": "guitarra eletrica electric guitar",
    "Baixos": "baixo contrabaixo bass",
    "Baterias e Percussão": "bateria percussao drum drums kit",
    "Teclados e Pianos": "teclado piano sintetizador keyboard synth synthesizer",
    "Violões": "violao acustico acoustic classical folk guitar",
    "Instrumentos de Sopro (Madeiras)": "sopro madeira flauta clarinete saxofone wind woodwind flute sax",
    "Instrumentos de Sopro (Metais)": "sopro metal trompete trombone tuba wind brass trumpet",
    "Cordas Orquestrais": "violino viola violoncelo cello violin orchestral",
    "Ukuleles": "ukulele uke",
}

# Results scoring below this fraction of the best match are dropped, so "acoustic
# guitar" returns acoustic guitars and not every product that matches only "guitar".
RELATIVE_SCORE_CUTOFF = 0.6

KNOWN_BRANDS = {
    "yamaha", "tagima", "giannini", "rozini", "shelby", "crafter", "takamine",
    "martin", "taylor", "kala", "ohana", "kalani", "fender", "gibson", "ibanez",
    "prs", "music man", "pearl", "korg", "nord", "roland", "tama",
}


@dataclass(frozen=True)
class Product:
    id: int
    name: str
    category: str
    price: float
    description: str | None
    stock: int
    status: str
    specs: dict

    @property
    def availability(self) -> str:
        """One of: available, out_of_stock, discontinued, coming_soon."""
        if self.status == "discontinued":
            return "discontinued"
        if self.status == "coming_soon":
            return "coming_soon"
        return "available" if self.stock > 0 else "out_of_stock"


@dataclass(frozen=True)
class Promotion:
    product_id: int
    discount_percent: float
    name: str


@dataclass(frozen=True)
class Customer:
    id: int
    name: str
    phone: str
    email: str
    city: str


@dataclass(frozen=True)
class Order:
    id: int
    customer_id: int
    order_date: date
    status: str
    total: float
    payment_method: str
    tracking_code: str | None
    estimated_delivery: date | None
    notes: str | None
    items: list[tuple[int, int]] = field(default_factory=list)  # (product_id, quantity)


def describe_payment(code: str) -> str:
    if code.startswith("credit_"):
        n = code.removeprefix("credit_").rstrip("x")
        return f"credit card in {n} installments"
    return PAYMENT_METHODS.get(code, code)


def installment_plans(amount: float) -> list[dict]:
    """Interest-free credit-card plans allowed for an amount, following manual item 3.1."""
    plans = []
    for n in range(1, 13):
        value = amount / n
        minimum = next(m for limit, m in INSTALLMENT_TIERS if n <= limit)
        if value >= minimum:
            plans.append({"installments": n, "installment_value": round(value, 2)})
    return plans


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _optional(value: str) -> str | None:
    value = value.strip()
    return value or None


def _clean_description(name: str, description: str) -> str | None:
    """Drop descriptions that mention a brand absent from the product name.

    Some rows describe a different instrument (e.g. "Music Man Bass 1X" described as
    a Fender Jazz Bass). Showing them would mislead the customer, so the agent relies
    only on name and specs for those products.
    """
    folded_name, folded_desc = fold(name), fold(description)
    for brand in KNOWN_BRANDS:
        if brand in folded_desc and brand not in folded_name:
            return None
    return description


class Store:
    def __init__(self, data_dir: Path, today: date):
        self.today = today
        self.categories = {
            int(r["category_id"]): r["name"] for r in _read_csv(data_dir / "categories.csv")
        }
        self.products: dict[int, Product] = {}
        for r in _read_csv(data_dir / "products.csv"):
            product = Product(
                id=int(r["product_id"]),
                name=r["name"].strip(),
                category=self.categories[int(r["category_id"])],
                price=float(r["price_brl"]),
                description=_clean_description(r["name"], r["description"]),
                stock=int(r["stock_quantity"]),
                status=r["status"].strip(),
                specs=json.loads(r["specs"]) if r["specs"] else {},
            )
            self.products[product.id] = product

        # Only active promotions count; if a product ever had two, the bigger discount wins.
        self.promotions: dict[int, Promotion] = {}
        for r in _read_csv(data_dir / "promotions.csv"):
            if r["is_active"].strip() != "1":
                continue
            promo = Promotion(int(r["product_id"]), float(r["discount_percent"]), r["description"])
            current = self.promotions.get(promo.product_id)
            if current is None or promo.discount_percent > current.discount_percent:
                self.promotions[promo.product_id] = promo

        self.customers = {
            int(r["customer_id"]): Customer(
                int(r["customer_id"]), r["name"], r["phone"], r["email"], r["city"]
            )
            for r in _read_csv(data_dir / "customers.csv")
        }

        items: dict[int, list[tuple[int, int]]] = {}
        for r in _read_csv(data_dir / "order_items.csv"):
            items.setdefault(int(r["order_id"]), []).append(
                (int(r["product_id"]), int(r["quantity"]))
            )
        self.orders: dict[int, Order] = {}
        for r in _read_csv(data_dir / "orders.csv"):
            order_id = int(r["order_id"])
            delivery = _optional(r["estimated_delivery"])
            self.orders[order_id] = Order(
                id=order_id,
                customer_id=int(r["customer_id"]),
                order_date=date.fromisoformat(r["order_date"]),
                status=r["status"].strip(),
                total=float(r["total_brl"]),
                payment_method=r["payment_method"].strip(),
                tracking_code=_optional(r["tracking_code"]),
                estimated_delivery=date.fromisoformat(delivery) if delivery else None,
                notes=_optional(r["notes"]),
                items=items.get(order_id, []),
            )

    # ----- pricing -------------------------------------------------------------------

    def pricing(self, product: Product) -> dict:
        """Current price with active promotion, PIX price and the longest installment plan.

        Manual 6.2: promotions and the 5% PIX discount do not stack, and a promotional
        price must always be shown next to the original price and the discount.
        """
        promo = self.promotions.get(product.id)
        if promo:
            final = round(product.price * (1 - promo.discount_percent / 100), 2)
            pix = None
        else:
            final = product.price
            pix = round(product.price * (1 - PIX_DISCOUNT), 2)
        plans = installment_plans(final)
        return {
            "list_price": product.price,
            "promotion": (
                {"name": promo.name, "discount_percent": promo.discount_percent} if promo else None
            ),
            "final_price": final,
            "pix_price": pix,
            "max_installments": plans[-1] if plans else None,
        }

    # ----- catalog search ------------------------------------------------------------

    def search_products(
        self,
        query: str | None = None,
        category: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        include_unavailable: bool = False,
        limit: int = 10,
    ) -> list[Product]:
        """Filter the catalog. Price filters use the final (promotional) price.

        With a text query, results are ranked by how well the query matches the
        product name and specs; products that match nothing are left out.
        """
        results: list[tuple[float, Product]] = []
        for product in self.products.values():
            if category and fold(product.category) != fold(category):
                continue
            if not include_unavailable and product.availability != "available":
                continue
            price = self.pricing(product)["final_price"]
            if min_price is not None and price < min_price:
                continue
            if max_price is not None and price > max_price:
                continue
            score = _match_score(query, product) if query else 1.0
            if score > 0:
                results.append((score, product))
        if results:
            best = max(score for score, _ in results)
            results = [(s, p) for s, p in results if s >= best * RELATIVE_SCORE_CUTOFF]
        results.sort(key=lambda sp: (-sp[0], self.pricing(sp[1])["final_price"]))
        return [p for _, p in results[:limit]]

    # ----- orders --------------------------------------------------------------------

    def verify_order(self, order_id: int, contact: str) -> Order | None:
        """Return the order only if `contact` matches the buyer's e-mail or phone.

        The same `None` is returned for "order not found" and "contact does not
        match", so the answer does not reveal which order numbers exist.
        """
        order = self.orders.get(order_id)
        if order is None:
            return None
        customer = self.customers[order.customer_id]
        contact = contact.strip()
        if "@" in contact:
            return order if contact.casefold() == customer.email.casefold() else None
        given, registered = digits(contact), digits(customer.phone)
        # Accept the number with or without area code / country code.
        if len(given) >= 8 and (registered.endswith(given) or given.endswith(registered)):
            return order
        return None


def _match_score(query: str, product: Product) -> float:
    """Fraction of query words found in the product's name, category or specs.

    Words are compared without accents and in singular form, so "violão", "violao" and
    "violões" all match the category "Violões".
    """
    text = " ".join(
        [product.name, product.category, CATEGORY_SYNONYMS.get(product.category, ""),
         *map(str, product.specs.values())]
    )
    haystack = {stem(t) for t in tokens(text)}
    words = [stem(w) for w in tokens(query) if len(w) > 1]
    if not words:
        return 1.0
    hits = 0.0
    for word in words:
        if any(h == word or _is_prefix(word, h) for h in haystack):
            hits += 1
        elif len(word) >= 4 and any(
            len(h) >= 4 and SequenceMatcher(None, word, h).ratio() >= 0.8 for h in haystack
        ):
            hits += 0.8  # tolerate small typos ("takamini", "yamha")
    return hits / len(words)


def _is_prefix(word: str, candidate: str) -> bool:
    """Partial words count ("guitar" -> "guitarra", "strat" -> "stratocaster"), but short
    ones must nearly complete the word: "aco" must not match "acoustic", "bass" not "basswood"."""
    if len(word) < 4 or not candidate.startswith(word):
        return False
    return len(word) >= 5 or len(candidate) - len(word) <= 3
