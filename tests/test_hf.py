import builtins
import io
import sys

import pytest

from scigantic import hf

CYP = "openadmet/cyp-challenge-train-test"


class FakeFS:
    def __init__(self):
        self.calls = []

    def find(self, root, detail=False):
        self.calls.append(("find", root, detail))
        paths = [f"{root}/README.md", f"{root}/data/train.csv"]
        if detail:
            return {p: {"name": p, "size": 1} for p in paths}
        return paths

    def open(self, path, mode="rb", **kw):
        self.calls.append(("open", path, mode))
        return io.BytesIO(b"hello")


@pytest.fixture
def fake_fs(monkeypatch):
    fs = FakeFS()
    monkeypatch.setattr(hf, "_fs", lambda token=None: fs)
    return fs


def test_files_strips_the_repo_prefix(fake_fs):
    assert hf.files(f"hf:{CYP}") == ["README.md", "data/train.csv"]
    assert fake_fs.calls == [("find", f"datasets/{CYP}", False)]


def test_files_detail_returns_entries(fake_fs):
    out = hf.files(CYP, detail=True)
    assert [e["size"] for e in out] == [1, 1]


def test_open_builds_the_hf_path(fake_fs):
    with hf.open(f"https://huggingface.co/datasets/{CYP}", "/data/train.csv") as f:
        assert f.read() == b"hello"
    assert fake_fs.calls[-1] == ("open", f"datasets/{CYP}/data/train.csv", "rb")


def test_open_refuses_write_modes(fake_fs):
    with pytest.raises(ValueError):
        hf.open(CYP, "x", mode="wb")


def test_archive_ids_are_rejected(fake_fs):
    with pytest.raises(ValueError):
        hf.files("15b4d4e6-d24e-5344-9789-9501cded9c3c")


def test_missing_huggingface_hub_names_the_extra(monkeypatch):
    real_import = builtins.__import__

    def _import(name, *a, **k):
        if name == "huggingface_hub":
            raise ImportError("no module")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", _import)
    monkeypatch.delitem(sys.modules, "huggingface_hub", raising=False)
    with pytest.raises(ImportError) as ei:
        hf._fs()
    assert 'pip install "scigantic[hf]"' in str(ei.value)


def test_revision_changes_the_root(fake_fs):
    hf.files(f"hf:{CYP}", revision="v2")
    assert fake_fs.calls[-1] == ("find", f"datasets/{CYP}@v2", False)
    hf.open(f"hf:{CYP}", "/data/x.csv", revision="abc123")
    assert fake_fs.calls[-1] == ("open", f"datasets/{CYP}@abc123/data/x.csv", "rb")


def test_info_returns_metadata(monkeypatch, fake_fs):
    fake_fs.info = lambda path: {"name": path, "size": 42}
    out = hf.info(f"hf:{CYP}", "README.md")
    assert out == {"name": f"datasets/{CYP}/README.md", "size": 42}


class GatedRepoError(Exception):
    pass


class RepositoryNotFoundError(Exception):
    pass


@pytest.mark.parametrize(
    "exc, reason",
    [
        (GatedRepoError("401 Client Error: gated repo"), "gated"),
        (RepositoryNotFoundError("404"), "not_found"),
        (FileNotFoundError("datasets/x/y/z.csv"), "not_found"),
        (RuntimeError("boom"), "error"),
    ],
)
def test_hub_errors_map_to_reasons(monkeypatch, fake_fs, exc, reason):
    def _raise(*a, **k):
        raise exc

    fake_fs.find = _raise
    fake_fs.open = _raise
    with pytest.raises(hf.SciganticError) as ei:
        hf.files(f"hf:{CYP}")
    assert ei.value.reason == reason
    with pytest.raises(hf.SciganticError) as ei2:
        hf.open(f"hf:{CYP}", "a.csv")
    assert ei2.value.reason == reason


def test_token_is_passed_to_the_filesystem(monkeypatch):
    seen = {}

    class FS(FakeFS):
        pass

    def _fs(token=None):
        seen["token"] = token
        return FS()

    monkeypatch.setattr(hf, "_fs", _fs)
    hf.files(f"hf:{CYP}", token="hf_abc")
    assert seen == {"token": "hf_abc"}


def test_archive_id_is_not_an_hf_dataset():
    with pytest.raises(ValueError):
        hf.files("15b4d4e6-d24e-5344-9789-9501cded9c3c")
