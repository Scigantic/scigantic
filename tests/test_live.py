"""Smoke tests against the real API. Opt in with SCIGANTIC_LIVE_TESTS=1."""

import os

import pytest

import scigantic
from scigantic import catalog
from scigantic.catalog import SciganticError

pytestmark = pytest.mark.skipif(not os.environ.get("SCIGANTIC_LIVE_TESTS"), reason="set SCIGANTIC_LIVE_TESTS=1")

CYP = "openadmet/cyp-challenge-train-test"
CYP_ID = "15b4d4e6-d24e-5344-9789-9501cded9c3c"


@pytest.mark.live
def test_known_dataset_resolves_to_its_stable_row():
    out = scigantic.resolve(f"hf:{CYP}")
    assert out["success"] is True
    assert out["archiveId"] == CYP_ID
    assert out["created"] is False


@pytest.mark.live
def test_gated_dataset_is_refused_with_reason():
    with pytest.raises(SciganticError) as ei:
        scigantic.resolve("hf:nvidia/Nemotron-Pretraining-Code-v1")
    assert ei.value.reason == "gated"
    assert ei.value.huggingface_url.endswith("nvidia/Nemotron-Pretraining-Code-v1")


@pytest.mark.live
def test_search_and_get_round_trip():
    rows = catalog.search("CYP inhibition blind challenge", limit=5)
    assert any(r.get("id") == CYP_ID for r in rows)
    assert catalog.get(CYP_ID)["bucketName"] == CYP
