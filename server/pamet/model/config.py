"""Config entity types matching the TypeScript counterparts in pamet/web-app/src/model/config/."""

from __future__ import annotations

from typing import Any

import attrs
from fusion import Entity, entity_type


@entity_type
class UserSettings(Entity):
    userId: str = ""
    userName: str = ""
    projects: list[dict[str, Any]] = attrs.Factory(list)


@entity_type
class MiscProperties(Entity):
    deviceId: str = ""
    recentProjects: list[dict[str, Any]] = attrs.Factory(list)


@entity_type
class ProjectProperties(Entity):
    projectId: str = ""
    title: str = ""
    description: str = ""
    created: str = ""
    default_page_id: str | None = None

    @staticmethod
    def id_for_project(project_id: str) -> str:
        return f"project-props-{project_id}"
