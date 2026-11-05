import io
import json
import urllib.error

import pytest

import scigantic
import scigantic.catalog as catalog
import scigantic.cli as cli
from scigantic.catalog import SciganticError

CYP = "openadmet/cyp-challenge-train-test"


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def fake_urlopen(replies):
    """replies: {url_substring: dict | (status, dict)}"""

    def _open(req, timeout=None):
        url = req.full_url
        assert timeout == catalog.TIMEOUT
        assert req.get_header("User-agent") == catalog.USER_AGENT
        for key, reply in replies.items():
            if key in url:
                if isinstance(reply, tuple):
                    status, payload = reply
                    raise urllib.error.HTTPError(url, status, "err", {}, io.BytesIO(json.dumps(payload).encode()))
                return FakeResponse(json.dumps(reply).encode())
        raise AssertionError(f"unexpected url {url}")

    return _open


@pytest.fixture
def no_browser(monkeypatch):
    opened = []
    monkeypatch.setattr(cli.webbrowser, "open", lambda url: opened.append(url) or True)
    monkeypatch.setattr(scigantic.webbrowser, "open", lambda url: opened.append(url) or True)
    return opened


def test_open_prints_landing_url_without_network(capsys, no_browser, monkeypatch):
    monkeypatch.setattr(catalog.urllib.request, "urlopen", fake_urlopen({}))
    rc = cli.main(["open", f"hf:{CYP}", "--no-browser"])
    assert rc == 0
    assert capsys.readouterr().out.strip() == f"https://scigantic.com/hf/{CYP}"
    assert no_browser == []


def test_open_opens_browser_by_default(capsys, no_browser):
    rc = cli.main(["open", CYP])
    assert rc == 0
    assert no_browser == [f"https://scigantic.com/hf/{CYP}"]


def test_open_json_calls_resolve_api(capsys, no_browser, monkeypatch):
    reply = {
        "success": True,
        "archiveId": "15b4d4e6-d24e-5344-9789-9501cded9c3c",
        "created": False,
        "archiveUrl": "https://scigantic.com/archive/15b4d4e6-d24e-5344-9789-9501cded9c3c",
        "title": "CYP challenge",
    }
    monkeypatch.setattr(catalog.urllib.request, "urlopen", fake_urlopen({f"/api/hf/{CYP}": reply}))
    rc = cli.main(["open", f"hf:{CYP}", "--json", "--no-browser"])
    assert rc == 0
    assert json.loads(capsys.readouterr().out) == reply


@pytest.mark.parametrize(
    "reason,status",
    [
        ("gated", 403),
        ("private", 403),
        ("license", 403),
        ("too_large", 413),
        ("not_found", 404),
        ("rate_limited", 429),
        ("invalid_repo", 400),
        ("disabled", 403),
    ],
)
def test_resolve_errors_carry_the_api_reason(capsys, no_browser, monkeypatch, reason, status):
    payload = {
        "success": False,
        "reason": reason,
        "message": f"refused: {reason}",
        "huggingFaceUrl": f"https://huggingface.co/datasets/{CYP}",
    }
    monkeypatch.setattr(catalog.urllib.request, "urlopen", fake_urlopen({f"/api/hf/{CYP}": (status, payload)}))
    with pytest.raises(SciganticError) as ei:
        scigantic.resolve(f"hf:{CYP}")
    assert ei.value.reason == reason
    assert ei.value.status == status
    assert "refused" in str(ei.value)

    rc = cli.main(["open", CYP, "--json", "--no-browser"])
    assert rc == 1
    err = capsys.readouterr().err
    assert f"scigantic: {reason}: refused: {reason}" in err
    assert f"source: https://huggingface.co/datasets/{CYP}" in err


def test_404_without_body_maps_to_not_found(monkeypatch):
    def _open(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 404, "nf", {}, io.BytesIO(b"<html>"))

    monkeypatch.setattr(catalog.urllib.request, "urlopen", _open)
    with pytest.raises(SciganticError) as ei:
        scigantic.resolve("nobody/nothing")
    assert ei.value.reason == "not_found"


def test_network_failure_is_a_scigantic_error(monkeypatch):
    def _open(req, timeout=None):
        raise urllib.error.URLError("dns down")

    monkeypatch.setattr(catalog.urllib.request, "urlopen", _open)
    with pytest.raises(SciganticError) as ei:
        catalog.search("anything")
    assert ei.value.reason == "network"


def test_invalid_ref_exit_code_2(capsys, no_browser):
    rc = cli.main(["open", "not a ref", "--no-browser"])
    assert rc == 2
    assert "could not parse" in capsys.readouterr().err


def test_search_prints_id_and_title(capsys, monkeypatch):
    rows = {"data": [{"id": "abc", "title": "First"}, {"id": "def", "title": "Second"}]}
    monkeypatch.setattr(
        catalog.urllib.request, "urlopen", fake_urlopen({"/api/archives?search=quercetin&limit=2": rows})
    )
    rc = cli.main(["search", "quercetin", "--limit", "2"])
    assert rc == 0
    assert capsys.readouterr().out.splitlines() == ["abc  First", "def  Second"]


def test_search_with_no_results_exits_1(capsys, monkeypatch):
    monkeypatch.setattr(catalog.urllib.request, "urlopen", fake_urlopen({"/api/archives?": {"data": []}}))
    assert cli.main(["search", "zzz"]) == 1


ARCHIVE = "15b4d4e6-d24e-5344-9789-9501cded9c3c"


@pytest.mark.parametrize("wrap", [True, False])
def test_info_handles_wrapped_and_bare_item(capsys, monkeypatch, wrap):
    item = {"id": ARCHIVE, "title": "T", "license": "mit", "extra": 1}
    reply = {"data": item} if wrap else item
    monkeypatch.setattr(catalog.urllib.request, "urlopen", fake_urlopen({f"/api/archives/{ARCHIVE}": reply}))
    rc = cli.main(["info", f"https://scigantic.com/archive/{ARCHIVE}"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out == {"id": ARCHIVE, "title": "T", "license": "mit"}


def test_info_on_hf_ref_resolves_then_fetches(capsys, monkeypatch):
    item = {"id": ARCHIVE, "title": "CYP", "huggingFaceUrl": f"https://huggingface.co/datasets/{CYP}"}
    replies = {f"/api/hf/{CYP}": {"success": True, "archiveId": ARCHIVE}, f"/api/archives/{ARCHIVE}": {"data": item}}
    monkeypatch.setattr(catalog.urllib.request, "urlopen", fake_urlopen(replies))
    assert cli.main(["info", f"hf:{CYP}"]) == 0
    assert json.loads(capsys.readouterr().out)["id"] == ARCHIVE


def test_resolve_of_archive_id_uses_catalog_get(monkeypatch):
    item = {"id": "15b4d4e6-d24e-5344-9789-9501cded9c3c", "title": "CYP"}
    monkeypatch.setattr(catalog.urllib.request, "urlopen", fake_urlopen({"/api/archives/15b4d4e6": {"data": item}}))
    out = scigantic.resolve("15b4d4e6-d24e-5344-9789-9501cded9c3c")
    assert out["archiveId"] == item["id"]
    assert out["title"] == "CYP"
    assert out["archiveUrl"] == "https://scigantic.com/archive/15b4d4e6-d24e-5344-9789-9501cded9c3c"


def test_search_json_and_api_url_flag(capsys, monkeypatch):
    seen = []

    def _open(req, timeout=None):
        seen.append(req.full_url)
        return FakeResponse(json.dumps({"data": [{"id": "a", "title": "A"}]}).encode())

    monkeypatch.setattr(catalog.urllib.request, "urlopen", _open)
    rc = cli.main(["--api-url", "https://staging-api.scigantic.com", "search", "iris", "--json", "--limit", "3"])
    assert rc == 0
    assert json.loads(capsys.readouterr().out) == [{"id": "a", "title": "A"}]
    assert seen == ["https://staging-api.scigantic.com/api/archives?search=iris&limit=3"]


def test_files_command_lists_paths(capsys, monkeypatch):
    import scigantic.hf as hf

    monkeypatch.setattr(hf, "files", lambda ref, revision=None: ["README.md", "data/x.csv"])
    rc = cli.main(["files", f"hf:{CYP}", "--revision", "main"])
    assert rc == 0
    assert capsys.readouterr().out.split() == ["README.md", "data/x.csv"]


def test_files_command_without_extra_is_exit_1(capsys, monkeypatch):
    import scigantic.hf as hf

    def _raise(ref, revision=None):
        raise ImportError("huggingface_hub is not installed")

    monkeypatch.setattr(hf, "files", _raise)
    assert cli.main(["files", f"hf:{CYP}"]) == 1
    assert "huggingface_hub is not installed" in capsys.readouterr().err


def test_rate_limited_prints_retry_after(capsys, monkeypatch, no_browser):
    def _open(req, timeout=None):
        raise urllib.error.HTTPError(
            req.full_url,
            429,
            "err",
            {"Retry-After": "60"},
            io.BytesIO(b'{"success":false,"reason":"rate_limited","message":"slow"}'),
        )

    monkeypatch.setattr(catalog.urllib.request, "urlopen", _open)
    assert cli.main(["open", f"hf:{CYP}", "--json", "--no-browser"]) == 1
    err = capsys.readouterr().err
    assert "rate_limited: slow" in err and "retry after: 60 s" in err


def test_module_entry_point():
    import runpy

    with pytest.raises(SystemExit) as ei:
        runpy.run_module("scigantic", run_name="__main__", alter_sys=True)
    assert ei.value.code == 2  # no command given -> argparse error
