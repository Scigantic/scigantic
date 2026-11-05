# Changelog

## 0.2.0 (2026-11-05)

- Retries: network errors and 502/503/504 answers are retried three times with a short backoff; 4xx answers are not.
- `SciganticError.retry_after` and `.huggingface_url`; a 429 maps to `rate_limited` even without a body.
- `SCIGANTIC_API_URL` and `SCIGANTIC_SITE_URL` (and `--api-url` / `--site-url`) point the client at another deployment.
- `scigantic.open()` shows a clickable link inside a Jupyter kernel instead of trying to open a browser.
- `scigantic.hf.files()`, `.open()` and the new `.info()` take `revision` and `token`; Hub errors map to `gated` / `not_found`.
- New `scigantic files` command, `scigantic search --json`, `--timeout`, and `python -m scigantic`.
- Reference parsing accepts `hf://datasets/owner/repo`, query strings and blob URLs, and rejects `..`, leading dots or dashes, and over-long segments, matching the server.
- Lint (ruff), types (mypy strict), coverage gate, a 3 OS x 3 Python CI matrix, a wheel install smoke test, a daily live smoke test and a tag-to-version check before publishing.

## 0.1.0 (2026-11-05)

- First release: `scigantic open`, `search`, `info`; `url_for`, `resolve`, `open`; `scigantic.hf` streaming over hf://.
