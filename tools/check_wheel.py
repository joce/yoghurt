"""Verify installed-wheel imports and resources without contacting Yahoo.

Run through ``uv run tox -e wheel``; isolated Python must load the installed
package rather than the source checkout.
"""

# ruff: file-ignore[assert] - assertions are the executable artifact checks.

from __future__ import annotations

import sys
from importlib.resources import files
from pathlib import Path

import yoghurt

assert Path(yoghurt.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
assert not Path.cwd().joinpath("pyproject.toml").exists()
for name in yoghurt.__all__:
    assert getattr(yoghurt, name) is not None, name
assert yoghurt.Ticker("AAPL").symbol == "AAPL"
assert files("yoghurt").joinpath("py.typed").is_file()
for name in (
    "QUERY_DSL.md",
    "QUOTE_FIELDS.md",
    "QUOTE_SUMMARY_MODULES.md",
    "TIMESERIES_TYPES.md",
):
    assert files("yoghurt.docs").joinpath(name).read_text(encoding="utf-8")
content = files("yoghurt.skills").joinpath("content")
assert content.joinpath("SKILL.md").read_text(encoding="utf-8")
for domain in ("analysis", "dataframes", "fundamentals", "market-data", "queries"):
    for name in ("README.md", "SHARP-EDGES.md"):
        assert content.joinpath(domain).joinpath(name).read_text(encoding="utf-8")
print("Installed wheel imports and bundled resources verified.")
