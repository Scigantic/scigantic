# Contributing

```
git clone https://github.com/Scigantic/scigantic
cd scigantic
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
ruff check . && ruff format --check . && mypy && pytest
```

Tests do not touch the network. The live tests in `tests/test_live.py` run only
with `SCIGANTIC_LIVE_TESTS=1` and hit the real API; CI runs them once a day.

The CLI contract (commands, exit codes, JSON shapes) is covered by
`tests/test_cli.py`; change the tests in the same pull request as the behaviour.

Releases: bump `scigantic/_version.py`, add a section to `CHANGELOG.md`, tag
`vX.Y.Z`. The publish workflow refuses a tag that does not match the version.
