from emporio.store import installment_plans
from emporio.text import brl


def product_named(store, name):
    return next(p for p in store.products.values() if p.name.startswith(name))


# ----- availability ------------------------------------------------------------------


def test_availability_combines_status_and_stock(store):
    assert product_named(store, "Giannini GF-3D").availability == "out_of_stock"
    assert product_named(store, "Shelby SN-7C").availability == "discontinued"
    # Discontinued wins even with units left in stock.
    assert product_named(store, "Ibanez Bass 2X").availability == "discontinued"
    # Coming soon wins even with units in stock.
    assert product_named(store, "Kala KA-ABP-CTG").availability == "coming_soon"
    assert product_named(store, "Yamaha C40").availability == "available"


# ----- pricing -----------------------------------------------------------------------


def test_inactive_promotion_is_ignored(store):
    # Takamine GD20 has promotion rows, but none is active.
    pricing = store.pricing(product_named(store, "Takamine GD20"))
    assert pricing["promotion"] is None
    assert pricing["final_price"] == pricing["list_price"]


def test_active_promotion_applies_and_disables_pix(store):
    pricing = store.pricing(product_named(store, "Crafter HT-100"))  # 18% off R$ 2.399
    assert pricing["promotion"]["discount_percent"] == 18
    assert pricing["final_price"] == 1967.18
    assert pricing["pix_price"] is None  # manual 6.2: discounts do not stack


def test_pix_discount_without_promotion(store):
    pricing = store.pricing(product_named(store, "Yamaha C40"))  # R$ 599,90
    assert pricing["pix_price"] == 569.9


def test_only_four_promotions_are_active(store):
    assert len(store.promotions) == 4


# ----- installments (manual item 3.1) ------------------------------------------------


def test_installments_respect_tier_minimums():
    plans = {p["installments"]: p["installment_value"] for p in installment_plans(159.90)}
    # 3x of R$ 53,30 is allowed (>= R$ 50); 4x of R$ 39,98 is not (< R$ 80).
    assert max(plans) == 3


def test_installments_up_to_twelve_for_expensive_items():
    plans = installment_plans(2199.00)
    assert plans[-1] == {"installments": 12, "installment_value": 183.25}


def test_installments_middle_tier():
    # R$ 599,90: 6x = R$ 99,98 (>= 80) is allowed, 7x = R$ 85,70 (< 100) is not.
    assert installment_plans(599.90)[-1]["installments"] == 6


# ----- search ------------------------------------------------------------------------


def test_search_by_category_and_max_price_excludes_unavailable(store):
    results = store.search_products(category="Violões", max_price=1000, limit=100)
    assert results
    assert all(p.category == "Violões" for p in results)
    assert all(store.pricing(p)["final_price"] <= 1000 for p in results)
    names = [p.name for p in results]
    assert not any(n.startswith("Giannini GF-3D") for n in names)  # out of stock
    assert not any(n.startswith("Shelby SN-7C") for n in names)  # discontinued


def test_search_by_name_ranks_exact_model_first(store):
    results = store.search_products(query="Takamine GD20")
    assert results[0].name.startswith("Takamine GD20")


def test_search_tolerates_accents_and_typos(store):
    assert store.search_products(query="takamini gd20")[0].name.startswith("Takamine GD20")
    assert store.search_products(query="ukulele tenor eletrico")


def test_search_can_include_unavailable_products(store):
    results = store.search_products(query="Giannini GF-3D", include_unavailable=True)
    assert results[0].availability == "out_of_stock"


def test_misleading_description_is_dropped(store):
    assert product_named(store, "Music Man Bass 1X").description is None  # says "Fender"
    assert product_named(store, "Yamaha C40").description


# ----- orders ------------------------------------------------------------------------


def test_order_requires_matching_email_or_phone(store):
    # Order 1 belongs to customer 3 (Pedro Henrique Oliveira).
    assert store.verify_order(1, "PEDRO.OLIVEIRA@jmail.com") is not None
    assert store.verify_order(1, "(67) 98432-1098") is not None
    assert store.verify_order(1, "98432-1098") is not None
    assert store.verify_order(1, "+55 67 98432-1098") is not None
    assert store.verify_order(1, "lucas.mendes@jmail.com") is None
    assert store.verify_order(1, "1098") is None  # too short to identify anyone


def test_unknown_order_and_wrong_contact_look_the_same(store):
    assert store.verify_order(999, "pedro.oliveira@jmail.com") is None


def test_order_items_are_loaded(store):
    assert store.orders[15].items == [(82, 1), (106, 1)]


def test_brl_formatting():
    assert brl(1967.18) == "R$ 1.967,18"
    assert brl(599.9) == "R$ 599,90"


# ----- Portuguese morphology and English vocabulary (data is Portuguese only) --------


def test_singular_plural_and_accents_match_the_same_products(store):
    expected = {p.id for p in store.search_products(query="violões", limit=100)}
    assert expected
    for query in ["violão", "violao", "violoes", "VIOLÃO"]:
        assert {p.id for p in store.search_products(query=query, limit=100)} == expected


def test_english_terms_map_to_portuguese_categories(store):
    def categories(query):
        return {p.category for p in store.search_products(query=query, limit=100)}

    assert categories("acoustic guitar") == {"Violões"}
    assert categories("bass") == {"Baixos"}
    assert categories("drums") == {"Baterias e Percussão"}
    assert categories("keyboard") == {"Teclados e Pianos"}


def test_short_words_do_not_match_as_prefixes(store):
    # "aço" must not match "acoustic"; "bass" must not match "basswood" (a guitar body).
    assert all("Aço" in p.name for p in store.search_products(query="violão aço", limit=100))
    assert all(p.category == "Baixos" for p in store.search_products(query="bass", limit=100))


def test_partial_model_names_still_match(store):
    assert store.search_products(query="strat")[0].name.startswith("Fender Stratocaster")
