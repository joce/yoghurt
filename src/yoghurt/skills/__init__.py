"""Agent Skills packaging for yoghurt: skill content plus its installer.

``content/`` holds the Agent Skills-standard skill (``SKILL.md`` router plus
five markdown domains) that ships inside the yoghurt wheel as package data.
The installer that copies it into named agent skill directories lands here
in a later change.
"""

from __future__ import annotations

from yoghurt.skills._install import (
    AGENT_TARGETS,
    TargetReport,
    install,
    resolve_roots,
    status,
    uninstall,
)

__all__ = [
    "AGENT_TARGETS",
    "TargetReport",
    "install",
    "resolve_roots",
    "status",
    "uninstall",
]
