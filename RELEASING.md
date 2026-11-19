# Releasing yoghurt

yoghurt publishes to [PyPI](https://pypi.org/project/yoghurt/) from GitHub
Actions (`.github/workflows/publish.yml`) using **Trusted Publishing** (OIDC) —
no API tokens. **Pushing a `vX.Y.Z` tag starts the whole release**; the only
manual step is approving the PyPI deployment.

> The trusted publisher and the `pypi` environment (with required-reviewer
> approval) are already configured. No per-release infrastructure setup is needed.

## Cutting a release

The version is derived from the git tag by `hatch-vcs` — there is **no manual
version bump**. `src/yoghurt/__init__.py` reads it from a generated `_version.py`
at build time. Tagging `vX.Y.Z` makes the build `X.Y.Z`; commits after a tag get
a `X.Y.(Z+1).devN` version automatically.

1. Move the `## [Unreleased]` notes in `CHANGELOG.md` under a new `## [X.Y.Z]`
   heading and update the compare links at the bottom. Draft the release notes
   (overview + highlights, not a one-liner) in `docs/release_next.md` and move
   them to `docs/release_vX.Y.Z.md`. Commit and push to `main`; wait for CI to
   go green.
2. Tag the commit on `main` and push the tag:

   ```bash
   git tag vX.Y.Z
   ```

   ```bash
   git push origin vX.Y.Z
   ```

3. The tag push runs `publish.yml`:
   - **validate** — the tag must be exactly `vX.Y.Z` (no prefixes, suffixes or
     leading zeros) and point at a commit on `main`;
   - **checks** — the full CI suite (`ci.yml`) on the tagged commit;
   - **build** — `uv build`, `twine check`, and a check that the built version
     equals the tag;
   - **publish** — pauses on the `pypi` environment;
   - **github-release** — after PyPI accepts the upload, creates the GitHub
     Release `vX.Y.Z` with the wheel and sdist attached.
4. **Approve the deployment** (the one manual step): the run page shows
   *"Review pending deployments"* → tick `pypi` → *Approve and deploy*.
5. Verify: <https://pypi.org/project/yoghurt/> shows the new version and the
   GitHub Release exists.

Release notes come from `docs/release_vX.Y.Z.md` when it exists, otherwise from
the `## [X.Y.Z]` section of `CHANGELOG.md`, otherwise from GitHub's generated
notes (with a warning on the run). If a release for the tag already exists, the
distribution files are uploaded to it instead.

If a step fails before publishing (a red check, a version mismatch), fix it on
`main`, delete the tag (`git push origin :refs/tags/vX.Y.Z`, then
`git tag -d vX.Y.Z`) and tag again. If only a later step failed, use *Re-run
failed jobs* on the run. A version that reached PyPI can never be uploaded
again: release the fix as the next patch version.

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
