import io
import json
import urllib.error

import pytest

import scigantic
import scigantic.catalog as catalog
from scigantic.catalog import SciganticError

CYP = "openadmet/cyp-challenge-train-test"


class FakeResponse(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def scripted(replies):
    """A urlopen that answers from a queue: dict -> 200 body, (status, dict, headers) -> HTTPError, Exception -> raised."""
    calls = []

    def _open(req, timeout=None):
        calls.append(req.full_url)
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        if isinstance(reply, tuple):
            status, payload, headers = (reply + ({},))[:3]
            raise urllib.error.HTTPError(req.full_url, status, "err", headers, io.BytesIO(json.dumps(payload).encode()))
        if isinstance(reply, bytes):
            return FakeResponse(reply)
        return FakeResponse(json.dumps(reply).encode())

    _open.calls = calls
    return _open


def test_retries_5xx_then_succeeds(monkeypatch, no_sleep):
    fake = scripted([(503, {}), (502, {}), {"success": True, "archiveId": "x"}])
    monkeypatch.setattr(catalog.urllib.request, "urlopen", fake)
    assert catalog.resolve_hf("openadmet", "cyp-challenge-train-test")["archiveId"] == "x"
    assert len(fake.calls) == 3
    assert no_sleep == [0.5, 1.0]


def test_gives_up_after_retries(monkeypatch):
    fake = scripted([(503, {})] * 4)
    monkeypatch.setattr(catalog.urllib.request, "urlopen", fake)
    with pytest.raises(SciganticError) as ei:
        catalog.resolve_hf("o", "r")
    assert ei.value.status == 503 and ei.value.reason == "error"
    assert len(fake.calls) == 4


def test_network_errors_retry_then_report(monkeypatch):
    fake = scripted([urllib.error.URLError("dns")] * 4)
    monkeypatch.setattr(catalog.urllib.request, "urlopen", fake)
    with pytest.raises(SciganticError) as ei:
        catalog.get("abc")
    assert ei.value.reason == "network"
    assert len(fake.calls) == 4


def test_4xx_is_not_retried_and_carries_reason_and_retry_after(monkeypatch):
    fake = scripted(
        [
            (
                429,
                {
                    "success": False,
                    "reason": "rate_limited",
                    "message": "slow down",
                    "huggingFaceUrl": "https://huggingface.co/datasets/o/r",
                },
                {"Retry-After": "120"},
            )
        ]
    )
    monkeypatch.setattr(catalog.urllib.request, "urlopen", fake)
    with pytest.raises(SciganticError) as ei:
        catalog.resolve_hf("o", "r")
    e = ei.value
    assert (e.reason, e.status, e.retry_after, e.huggingface_url) == (
        "rate_limited",
        429,
        120.0,
        "https://huggingface.co/datasets/o/r",
    )
    assert str(e) == "slow down"
    assert len(fake.calls) == 1


def test_bodiless_429_maps_to_rate_limited(monkeypatch):
    monkeypatch.setattr(catalog.urllib.request, "urlopen", scripted([(429, {})]))
    with pytest.raises(SciganticError) as ei:
        catalog.get("abc")
    assert ei.value.reason == "rate_limited" and ei.value.retry_after is None


def test_nested_error_message_shape(monkeypatch):
    monkeypatch.setattr(
        catalog.urllib.request,
        "urlopen",
        scripted([(403, {"success": False, "error": {"status": 403, "message": "nope"}})]),
    )
    with pytest.raises(SciganticError) as ei:
        catalog.get("abc")
    assert str(ei.value) == "nope" and ei.value.reason == "error"


def test_non_json_body_is_an_error(monkeypatch):
    monkeypatch.setattr(catalog.urllib.request, "urlopen", scripted([b"<html>maintenance</html>"]))
    with pytest.raises(SciganticError) as ei:
        catalog.get("abc")
    assert "did not return JSON" in str(ei.value)


def test_search_wraps_bare_list_and_clamps_limit(monkeypatch):
    fake = scripted([[{"id": "a"}, "junk", {"id": "b"}]])
    monkeypatch.setattr(catalog.urllib.request, "urlopen", fake)
    rows = catalog.search("iris", limit=500)
    assert [r["id"] for r in rows] == ["a", "b"]
    assert "limit=100" in fake.calls[0]


def test_search_blank_query_is_local_empty(monkeypatch):
    monkeypatch.setattr(catalog.urllib.request, "urlopen", scripted([]))
    assert catalog.search("   ") == []


def test_get_rejects_empty_item(monkeypatch):
    monkeypatch.setattr(catalog.urllib.request, "urlopen", scripted([{"data": {}}]))
    with pytest.raises(SciganticError):
        catalog.get("abc")


def test_api_url_env_override(monkeypatch):
    monkeypatch.setenv("SCIGANTIC_API_URL", "https://staging-api.scigantic.com/")
    fake = scripted([{"success": True, "archiveId": "x"}])
    monkeypatch.setattr(catalog.urllib.request, "urlopen", fake)
    catalog.resolve_hf("o", "r")
    assert fake.calls == ["https://staging-api.scigantic.com/api/hf/o/r"]


def test_site_url_env_override_changes_landing_and_parsing(monkeypatch):
    monkeypatch.setenv("SCIGANTIC_SITE_URL", "https://staging.scigantic.com")
    assert scigantic.url_for(f"hf:{CYP}") == f"https://staging.scigantic.com/hf/{CYP}"
    assert scigantic.parse(f"https://staging.scigantic.com/hf/{CYP}").hf_repo == CYP


def test_resolve_archive_id_shapes_payload(monkeypatch):
    uuid = "15b4d4e6-d24e-5344-9789-9501cded9c3c"
    monkeypatch.setattr(
        catalog.urllib.request,
        "urlopen",
        scripted([{"data": {"id": uuid, "title": "T", "license": "mit", "unlisted": True}}]),
    )
    out = scigantic.resolve(uuid)
    assert out == {
        "success": True,
        "archiveId": uuid,
        "created": False,
        "archiveUrl": f"https://scigantic.com/archive/{uuid}",
        "title": "T",
        "license": "mit",
        "unlisted": True,
    }


def test_open_in_notebook_displays_link(monkeypatch):
    shown = []
    monkeypatch.setattr(scigantic, "_in_notebook", lambda: True)
    import sys
    import types

    display_mod = types.SimpleNamespace(HTML=lambda s: ("html", s), display=lambda x: shown.append(x))
    monkeypatch.setitem(sys.modules, "IPython", types.SimpleNamespace(display=display_mod))
    monkeypatch.setitem(sys.modules, "IPython.display", display_mod)
    monkeypatch.setattr(scigantic.webbrowser, "open", lambda url: pytest.fail("browser must not open in a notebook"))
    url = scigantic.open(f"hf:{CYP}")
    assert shown == [("html", f'<a href="{url}" target="_blank" rel="noopener">{url}</a>')]


def test_in_notebook_false_without_ipython(monkeypatch):
    import sys

    monkeypatch.setitem(sys.modules, "IPython", None)
    assert scigantic._in_notebook() is False
