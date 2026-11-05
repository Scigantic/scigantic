# scigantic

[![PyPI](https://img.shields.io/pypi/v/scigantic.svg)](https://pypi.org/project/scigantic/) [![CI](https://github.com/Scigantic/scigantic/actions/workflows/ci.yml/badge.svg)](https://github.com/Scigantic/scigantic/actions/workflows/ci.yml)

`scigantic` turns a dataset name into a notebook. Give it a Hugging Face dataset
(`owner/repo`) or a Scigantic archive id and it opens a page on scigantic.com where
the dataset is mounted read-only inside a hosted JupyterLab with a starter notebook. The same package can list and stream the files
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

`python -m scigantic` works the same as the `scigantic` command.

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

url = scigantic.url_for("openadmet/cyp-challenge-train-test")  # no network
scigantic.open("openadmet/cyp-challenge-train-test")  # opens the browser
info = scigantic.resolve("openadmet/cyp-challenge-train-test")  # {"archiveId": ..., "created": ...}
```

Accepted references: `hf:owner/repo`, `hf://datasets/owner/repo`, `owner/repo`, a
`https://huggingface.co/datasets/...` URL (with or without a file path), a Scigantic archive
id, or a `https://scigantic.com/archive/<id>` URL.

Inside a Jupyter kernel `scigantic.open()` shows the URL as a clickable link instead of
trying to open a browser on the kernel's machine.

The first request for a dataset creates its catalog entry. Later requests return the
existing one. If the dataset cannot be served, `resolve` raises `SciganticError` whose
`reason` is one of `private`, `gated`, `disabled`, `not_found`, `license`, `too_large`,
`invalid_repo`, `rate_limited` or `upstream_error`. Network errors and 502/503/504 answers
are retried three times before `reason` is `network` or `error`; a 429 carries `retry_after`
in seconds when the API sent one.

## Stream files locally with hf://

```
scigantic files hf:openadmet/cyp-challenge-train-test
```

```python
from scigantic import hf

hf.files("openadmet/cyp-challenge-train-test")
# ['README.md', 'cyp-challenge-TRAIN_inhibition.csv', ...]

with hf.open("openadmet/cyp-challenge-train-test", "cyp-challenge-TRAIN_inhibition.csv") as f:
    head = f.read(4096)
```

Reads go through `huggingface_hub.HfFileSystem` as HTTP range requests, so nothing is
downloaded in full. Hugging Face rate limits apply. `files`, `open` and `info` take `revision=`
and `token=`. A gated or missing repository raises `SciganticError` with `reason` `gated`
or `not_found`, the same codes the hosted path uses.

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

## Configuration and exit codes

| Setting | Effect |
| --- | --- |
| `SCIGANTIC_API_URL`, `--api-url` | catalog API base, default `https://api.scigantic.com` |
| `SCIGANTIC_SITE_URL`, `--site-url` | landing page base, default `https://scigantic.com` |
| `--timeout` | seconds per API request, default 10 |

Exit codes: 0 success; 1 the catalog refused or could not be reached (the reason is printed
to stderr); 2 the reference could not be parsed.

## Licence

MIT. See LICENSE.
