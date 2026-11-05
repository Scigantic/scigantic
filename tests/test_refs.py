import pytest

from scigantic import url_for
from scigantic.refs import InvalidReference, parse

CYP = "openadmet/cyp-challenge-train-test"
UUID = "15b4d4e6-d24e-5344-9789-9501cded9c3c"


@pytest.mark.parametrize(
    "ref",
    [
        f"hf:{CYP}",
        f"HF:{CYP}",
        f"hf://{CYP}",
        CYP,
        f"https://huggingface.co/datasets/{CYP}",
        f"https://huggingface.co/datasets/{CYP}/tree/main",
        f"https://hf.co/datasets/{CYP}",
        f"https://scigantic.com/hf/{CYP}",
        f"  hf:{CYP}  ",
        f"hf://datasets/{CYP}",
        f"hf:{CYP}?x=1",
        f"https://huggingface.co/datasets/{CYP}?library=datasets",
        f"https://huggingface.co/datasets/{CYP}/blob/main/README.md",
    ],
)
def test_hf_forms_parse_to_the_same_ref(ref):
    r = parse(ref)
    assert r.kind == "hf"
    assert r.hf_repo == CYP
    assert r.landing_url == f"https://scigantic.com/hf/{CYP}"
    assert r.resolve_url == f"https://api.scigantic.com/api/hf/{CYP}"
    assert r.huggingface_url == f"https://huggingface.co/datasets/{CYP}"


@pytest.mark.parametrize(
    "ref",
    [UUID, UUID.upper(), f"https://scigantic.com/archive/{UUID}", f"https://scigantic.com/archive/{UUID}/sample"],
)
def test_archive_forms(ref):
    r = parse(ref)
    assert r.kind == "archive"
    assert r.archive_id == UUID
    assert r.landing_url == f"https://scigantic.com/archive/{UUID}"
    assert r.resolve_url == f"https://api.scigantic.com/api/archives/{UUID}"
    assert r.hf_repo == ""


@pytest.mark.parametrize(
    "ref",
    [
        "",
        "   ",
        "hf:",
        "hf:onlyowner",
        "owner/repo/extra",
        "owner//repo",
        "/owner/repo",
        "https://huggingface.co/openadmet",
        "https://huggingface.co/spaces/openadmet/cyp-challenge",
        "https://scigantic.com/explore",
        "https://example.com/datasets/a/b",
        "not a ref",
        "a../b",
        "a/..b",
        ".hidden/repo",
        "-dash/repo",
        "o/" + "x" * 97,
        "hf:",
        "hf://datasets/onlyowner",
    ],
)
def test_rejects_garbage(ref):
    with pytest.raises(InvalidReference):
        parse(ref)


def test_url_for_is_offline_string_work():
    assert url_for(f"hf:{CYP}") == f"https://scigantic.com/hf/{CYP}"
    assert url_for(UUID) == f"https://scigantic.com/archive/{UUID}"


def test_str_of_ref():
    assert str(parse(f"hf:{CYP}")) == CYP
    assert str(parse(UUID)) == UUID
