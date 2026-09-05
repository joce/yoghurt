# Releasing yoghurt

yoghurt publishes to [PyPI](https://pypi.org/project/yoghurt/) from GitHub
Actions (`.github/workflows/publish.yml`) using **Trusted Publishing** (OIDC) —
no API tokens. The workflow runs when a **GitHub Release is published**; a bare
`git push` of a tag does *not* trigger it.

> The trusted publisher and the `pypi` environment (with required-reviewer
> approval) are already configured. No per-release infrastructure setup is needed.

## Cutting a release

The version is derived from the git tag by `hatch-vcs` — there is **no manual
version bump**. `src/yoghurt/__init__.py` reads it from a generated `_version.py`
at build time. Tagging `vX.Y.Z` makes the build `X.Y.Z`; commits after a tag get
a `X.Y.(Z+1).devN` version automatically.

1. Move the `## [Unreleased]` notes in `CHANGELOG.md` under a new `## [X.Y.Z]`
   heading and update the compare links at the bottom. Commit and push to `main`.
   Wait for CI to go green.
2. Create the release — this creates the `vX.Y.Z` tag *and* triggers publishing:

   ```bash
   gh release create vX.Y.Z --title "vX.Y.Z" --notes-file path/to/notes.md
   ```

   Write real notes (overview + highlights), not a one-liner.
3. The `publish` job pauses on the `pypi` environment. **Approve the deployment**:
   the run page shows *"Review pending deployments"* → tick `pypi` → *Approve and
   deploy*. After approval it uploads to PyPI.
4. Verify: <https://pypi.org/project/yoghurt/> shows the new version.

## Verify locally before releasing

```bash
uv build
uvx twine check dist/*
```

The built filenames carry the version `hatch-vcs` derived from git
(`yoghurt-X.Y.Z...`). A clean checkout *at* the tag yields exactly `X.Y.Z`; a
dirty tree or post-tag commit yields a `.devN`/`+g<sha>` suffix.

## Product release checks

Run the same offline product checks as CI before release:

```bash
uv run tox -m release
```

The `release` label composes `product`, `pandas`, and `wheel`: generated
Python signatures must be current; corpus-backed workflows and help
completeness must pass; optional conversions must run without skips; and
the installed wheel must include the reference and workflow resources.
This complements the full `uv run tox` code checks. CI runs the release
label without contacting Yahoo. Regenerate stale signatures with
`uv run python tools/generate_python_reference.py`, then review the diff.

## Refresh live claims separately

When releasing a change affecting the documented earnings limitation, run
this opt-in check with network access:

```bash
uv run python -m tools.probe --claims --report .tox/claims-report.json
```

It repeats four named requests: AAPL and SPY, each requesting
`spEarningsReleaseEvents` alone and with `quarterlyTotalRevenue`, over
2026-01-01 through 2026-09-05. The dated baseline is the observed
2026-09-05 response: three AAPL earnings observations and two revenue
observations; SPY returned metadata only for both families. Each family is
compared separately, including counts, missing data, malformed JSON, and
Yahoo/transport errors. Exit 0 means unchanged; exit 1 means changed.
The JSON report contains exact arguments, baseline date, check time,
expected/actual classifications, and change flags, without raw bodies.

Yahoo is not deterministic. Review changed results before updating a
claim or baseline; an empty instrument result is different from rejection
or an untested combination. This mode never updates documentation or the
historical corpus. The default probe command remains a full corpus
refresh, so use `--claims --report` for this focused check. Other claims
still need their own recorded symbol/date/parameter scope; these four
requests do not certify every instrument or endpoint combination.
