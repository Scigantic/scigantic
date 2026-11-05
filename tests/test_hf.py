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
    monkeypatch.setattr(hf, "_fs", lambda: fs)
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
