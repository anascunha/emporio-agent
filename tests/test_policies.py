import pytest

from emporio.config import DATA_DIR
from emporio.policies import TOPICS, PolicyManual


@pytest.fixture(scope="module")
def manual() -> PolicyManual:
    return PolicyManual(DATA_DIR / "politicas_da_loja.md")


def test_manual_has_all_ten_sections(manual):
    assert sorted(manual.sections, key=int) == [str(n) for n in range(1, 11)]


def test_every_topic_resolves(manual):
    for topic in TOPICS:
        assert manual.get(topic)


def test_topic_returns_whole_section_with_exceptions(manual):
    text = manual.get("returns_exchanges")
    assert "7 (sete) dias corridos" in text  # 4.1 regret
    assert "30 (trinta) dias" in text  # 4.2 defects
    assert "venda final" in text  # 4.4 non-eligible items


def test_contradictions_come_with_a_clarification(manual):
    assert "item 3.1 is more specific" in manual.get("payment")
    store_info = manual.get("store_info")
    assert "3341-4444" in store_info and "3321-4500" in store_info


def test_unknown_topic_lists_valid_ones(manual):
    with pytest.raises(KeyError, match="opening_hours"):
        manual.get("refunds")
