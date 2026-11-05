# scigantic

`scigantic` turns a dataset name into a notebook. Give it a Hugging Face dataset
(`owner/repo`) or a Scigantic archive id and it opens a page on scigantic.com where
the dataset is mounted read-only inside a hosted JupyterLab, with a starter notebook
that already knows the file layout. The same package can list and stream the files
of a Hugging Face dataset locally over `hf://`, so you can look before you launch.

## Install

```
pip install scigantic
```

Local streaming needs `huggingface_hub`:

```
pip install "scigantic[hf]"
```

Python 3.9 or newer. The base package has no dependencies.

## Open a dataset in the browser

Command line:

```
scigantic open hf:openadmet/cyp-challenge-train-test
```

This prints `https://scigantic.com/hf/openadmet/cyp-challenge-train-test` and opens it
in your default browser. Add `--no-browser` to print the URL only, or `--json` to call the
resolve API and print its reply (the archive id, and whether this request created it).

Python:

```python
import scigantic

url = scigantic.url_for("openadmet/cyp-challenge-train-test")   # no network
scigantic.open("openadmet/cyp-challenge-train-test")             # opens the browser
info = scigantic.resolve("openadmet/cyp-challenge-train-test")  # {"archiveId": ..., "created": ...}
```

Accepted references: `hf:owner/repo`, `owner/repo`, a `https://huggingface.co/datasets/...`
URL, a Scigantic archive id, or a `https://scigantic.com/archive/<id>` URL.

The first request for a dataset creates its catalog entry. Later requests return the
existing one. If the dataset cannot be served, `resolve` raises `SciganticError` whose
`reason` is one of `private`, `gated`, `disabled`, `not_found`, `license`, `too_large`,
`invalid_repo` or `rate_limited`.

## Stream files locally with hf://

```python
from scigantic import hf

hf.files("openadmet/cyp-challenge-train-test")
# ['README.md', 'cyp-challenge-TRAIN_inhibition.csv', ...]

with hf.open("openadmet/cyp-challenge-train-test", "cyp-challenge-TRAIN_inhibition.csv") as f:
    head = f.read(4096)
```

Reads go through `huggingface_hub.HfFileSystem` as HTTP range requests, so nothing is
downloaded in full. Hugging Face rate limits apply.

## Catalog search

```
scigantic search "mass spectrometry"
scigantic info 15b4d4e6-d24e-5344-9789-9501cded9c3c
```

`scigantic.catalog.search(query, limit=10)` and `scigantic.catalog.get(archive_id)` expose
the same read-only API from Python.

## What the hosted notebook requires

The landing page and the catalog API need no account. Running the notebook needs a free
Scigantic account. Only public Hugging Face datasets with a permissive licence are served
(for example MIT, Apache-2.0, CC BY, CC0, ODC). Private, gated and disabled repositories,
and datasets whose card carries no recognised licence, are refused with the reason above
and a link back to the source.

## Licence

MIT. See LICENSE.
