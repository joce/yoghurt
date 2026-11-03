## Overview

Yoghurt 0.8.0 moves to polars 2.x on all supported Python versions and refreshes the development toolchain. Yoghurt's own API and behavior are unchanged.

## Highlights

- **polars 2.x is now required everywhere.** The polars dependency range is now `>=2.0,<3.0` on every supported Python version (3.11–3.15). 0.7.0 required polars 2.x only on Python 3.15 and accepted 1.42.1+ elsewhere.
- Internal dependency refresh: dev and CI tooling updates (ruff, black, pylint, isort, tox, coverage, and the setup-uv action), plus lockfile-only bumps of httpx2 and pydantic. None of these change yoghurt's published dependency ranges.

## Upgrade notes

- An environment pinned to polars 1.x cannot install this release; upgrade polars to 2.x first. Yoghurt's result types and Parquet output work the same under polars 2.x.

**Full Changelog:** https://github.com/joce/yoghurt/compare/v0.7.0...v0.8.0
