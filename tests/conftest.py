import pytest

from emporio.config import DATA_DIR, DEFAULT_TODAY
from emporio.store import Store


@pytest.fixture(scope="session")
def store() -> Store:
    return Store(DATA_DIR, DEFAULT_TODAY)
