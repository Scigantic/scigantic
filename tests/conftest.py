import pytest

import scigantic.catalog as catalog


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Retries back off with time.sleep; tests must not wait for it."""
    slept = []
    monkeypatch.setattr(catalog.time, "sleep", lambda s: slept.append(s))
    return slept


@pytest.fixture(autouse=True)
def default_hosts(monkeypatch):
    monkeypatch.delenv("SCIGANTIC_API_URL", raising=False)
    monkeypatch.delenv("SCIGANTIC_SITE_URL", raising=False)
