"""Copy-only installer for the yoghurt agent skill (spec: agent-skills design)."""

from __future__ import annotations

import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from yoghurt import __version__

SKILL_DIR_NAME = "yoghurt"
CONTENT_DIR = Path(__file__).parent / "content"
_BASE_HEADER_LINES = 2
_VERSIONED_HEADER_LINES = 4

AGENT_TARGETS: dict[str, tuple[str, str]] = {
    # name -> (user-level root relative to home, project-level root relative
    # to cwd). Each pair is the agent's DOCUMENTED skill-discovery location,
    # not a name-derived guess: Codex discovers only `.agents/skills` roots
    # (developers.openai.com/codex/skills), and Copilot's project-level
    # discovery is `.github/skills` (its user level is `~/.copilot/skills`;
    # a project `.copilot/skills` is not scanned — docs.github.com Copilot
    # CLI "add skills"). Verified 2026-07-06.
    "claude": (".claude/skills", ".claude/skills"),
    "codex": (".agents/skills", ".agents/skills"),
    "copilot": (".copilot/skills", ".github/skills"),
    "cursor": (".cursor/skills", ".cursor/skills"),
    "gemini": (".gemini/skills", ".gemini/skills"),
    "pi": (".pi/agent/skills", ".pi/skills"),
}


@dataclass(frozen=True)
class TargetReport:
    """Outcome of one install/uninstall/status operation on one skills root."""

    root: Path
    action: str  # installed | removed | absent | refused | stale | current
    detail: str = ""


def resolve_roots(agents: list[str], *, project: bool, to: Path | None) -> list[Path]:
    """Turn --agent names (+ optional --to) into skills-root paths.

    Returns:
        list[Path]: One resolved skills root per named agent, plus ``to``
        appended if given.

    Raises:
        ValueError: For an unrecognized agent name.
    """
    roots: list[Path] = []
    for name in agents:
        try:
            user_rel, project_rel = AGENT_TARGETS[name]
        except KeyError:
            known = ", ".join(sorted(AGENT_TARGETS))
            message = f"unknown agent {name!r} (known: {known})"
            raise ValueError(message) from None
        base = Path.cwd() / project_rel if project else Path.home() / user_rel
        roots.append(base)
    if to is not None:
        roots.append(to)
    return roots


def _installed_name(skill_dir: Path) -> str | None:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return None
    frontmatter = _frontmatter(skill_md)
    if frontmatter is None:
        return None
    matches = re.findall(r"^name:[ \t]+(\S+)[ \t]*$", frontmatter, re.MULTILINE)
    return matches[0] if len(matches) == 1 else None


def _installed_version(skill_dir: Path) -> str | None:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return None
    frontmatter = _frontmatter(skill_md)
    if frontmatter is None:
        return None
    matches = re.findall(
        r"^[ \t]+version:[ \t]+(\S+)[ \t]*$",
        frontmatter,
        flags=re.MULTILINE,
    )
    return matches[0] if len(matches) == 1 else None


def _frontmatter(skill_md: Path) -> str | None:
    """Return the conservative frontmatter subset written by this installer."""

    try:
        text = skill_md.read_text(encoding="utf-8")
    except UnicodeError:
        return None
    match = re.match(
        r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)",
        text,
        flags=re.DOTALL,
    )
    if match is None or not _is_supported_frontmatter(match.group(1)):
        return None
    return match.group(1)


def _is_supported_frontmatter(frontmatter: str) -> bool:
    """Accept only the two header shapes emitted by yoghurt releases.

    Returns:
        Whether the complete block matches an unstamped or stamped header.
    """

    if any(
        character != "\n" and not character.isprintable() for character in frontmatter
    ):
        return False
    lines = frontmatter.split("\n")
    if len(lines) not in {_BASE_HEADER_LINES, _VERSIONED_HEADER_LINES}:
        return False
    if _plain_scalar(lines[0], "name") is None:
        return False
    if _plain_scalar(lines[1], "description") is None:
        return False
    return len(lines) == _BASE_HEADER_LINES or (
        lines[2] == "metadata:" and _plain_scalar(lines[3], "  version") is not None
    )


def _plain_scalar(line: str, key: str) -> str | None:
    """Extract the narrow YAML plain-scalar form written by the installer.

    Returns:
        The scalar value, or ``None`` when the line is outside the subset.
    """

    prefix = f"{key}:"
    if not line.startswith(prefix):
        return None
    remainder = line[len(prefix) :]
    if not remainder or remainder[0] != " ":
        return None
    value = remainder.strip(" ")
    invalid_start = "-?:,[]{}#&*!|>'\"%@`"
    if not value or value[0] in invalid_start:
        return None
    if ":" in value or "#" in value:
        return None
    return value


def _stamp_version(skill_md: Path) -> None:
    text = skill_md.read_text(encoding="utf-8")
    stamped = text.replace(
        "\n---\n", f"\nmetadata:\n  version: {__version__}\n---\n", 1
    )
    skill_md.write_text(stamped, encoding="utf-8", newline="\n")


def install(roots: list[Path]) -> list[TargetReport]:
    """Copy the skill into each root, replacing only installs we own.

    Returns:
        list[TargetReport]: One report per requested root.

    Raises:
        OSError: If staging or replacement fails.
        ValueError: If the staged skill is invalid.
    """
    reports: list[TargetReport] = []
    for root in roots:
        skill_dir = root / SKILL_DIR_NAME
        if skill_dir.is_symlink() or (
            skill_dir.exists() and _installed_name(skill_dir) != SKILL_DIR_NAME
        ):
            reports.append(
                TargetReport(
                    root, "refused", "existing directory is not the yoghurt skill"
                )
            )
            continue
        root.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(dir=root))
        stage = temporary / "new"
        backup = temporary / "previous"
        installed = False
        try:
            shutil.copytree(CONTENT_DIR, stage)
            _stamp_version(stage / "SKILL.md")
            if (
                _installed_name(stage) != SKILL_DIR_NAME
                or _installed_version(stage) != __version__
            ):
                message = "staged yoghurt skill is invalid"
                raise ValueError(message)
            if skill_dir.exists():
                skill_dir.rename(backup)
            try:
                stage.rename(skill_dir)
            except OSError:
                if backup.exists():
                    backup.rename(skill_dir)
                raise
            installed = True
        finally:
            # Preserve the old copy if restoring it also fails.
            if installed or not backup.exists():
                shutil.rmtree(temporary)
        reports.append(TargetReport(root, "installed", __version__))
    return reports


def uninstall(roots: list[Path]) -> list[TargetReport]:
    """Remove the skill from each root; only dirs we own.

    Returns:
        list[TargetReport]: One report per requested root.
    """
    reports: list[TargetReport] = []
    for root in roots:
        skill_dir = root / SKILL_DIR_NAME
        if not skill_dir.exists():
            reports.append(TargetReport(root, "absent"))
        elif _installed_name(skill_dir) != SKILL_DIR_NAME:
            reports.append(
                TargetReport(
                    root, "refused", "existing directory is not the yoghurt skill"
                )
            )
        else:
            shutil.rmtree(skill_dir)
            reports.append(TargetReport(root, "removed"))
    return reports


def status() -> list[TargetReport]:
    """Walk every named target x {user, project} and report install state.

    Returns:
        list[TargetReport]: One report per (agent, scope) pair.
    """
    reports: list[TargetReport] = []
    for name in sorted(AGENT_TARGETS):
        user_rel, project_rel = AGENT_TARGETS[name]
        for scope, base in (
            ("user", Path.home() / user_rel),
            ("project", Path.cwd() / project_rel),
        ):
            skill_dir = base / SKILL_DIR_NAME
            label = f"{name} {scope}"
            if _installed_name(skill_dir) != SKILL_DIR_NAME:
                reports.append(TargetReport(base, "absent", label))
                continue
            version = _installed_version(skill_dir) or "unknown"
            action = "current" if version == __version__ else "stale"
            reports.append(TargetReport(base, action, f"{label} {version}"))
    return reports
