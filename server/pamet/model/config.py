"""Config entity types matching the TypeScript counterparts in pamet/web-app/src/model/config/."""

from __future__ import annotations

from typing import Any, TypedDict

import attrs
from fusion import Entity, entity_type


class TerminalPrefixSettings(TypedDict, total=False):
    """`{cmd}`-templates used to wrap an assembled argv when run_in_terminal is true."""

    posix: str
    windows: str


class ScriptLimitSettings(TypedDict, total=False):
    max_concurrent_jobs_per_project: int
    output_ring_buffer_bytes: int
    kill_grace_seconds: int


class ScriptSettings(TypedDict, total=False):
    """v5 script-execution settings stored on UserSettings."""

    # Per-path/per-folder allowlist. Key = canonicalized absolute path
    # (file or directory). Value = ISO timestamp of when "Always allow"
    # was clicked. Folder entries grant trust to all scripts under them.
    accepted_paths: dict[str, str]
    run_in_terminal_prefix: TerminalPrefixSettings
    limits: ScriptLimitSettings


def default_script_settings() -> ScriptSettings:
    """v5 defaults — single source of truth for fresh installs."""
    return {
        "accepted_paths": {},
        "run_in_terminal_prefix": {
            "posix": "gnome-terminal -- bash -c {cmd}",
            "windows": "powershell -noexit {cmd}",
        },
        "limits": {
            "max_concurrent_jobs_per_project": 16,
            "output_ring_buffer_bytes": 65536,
            "kill_grace_seconds": 5,
        },
    }


@entity_type
class UserSettings(Entity):
    userId: str = ""
    userName: str = ""
    projects: list[dict[str, Any]] = attrs.Factory(list)
    scripts: ScriptSettings = attrs.Factory(default_script_settings)


@entity_type
class DeviceState(Entity):
    deviceId: str = ""
    recentProjects: list[dict[str, Any]] = attrs.Factory(list)


@entity_type
class ProjectProperties(Entity):
    project_id: str = ""
    title: str = ""
    description: str = ""
    created: str = ""
    home_page_id: str | None = None
    backups_enabled: bool = True
    record_all_changes: bool = False

    @staticmethod
    def id_for_project(project_id: str) -> str:
        return f"project-props-{project_id}"
