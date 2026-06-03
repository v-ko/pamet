from __future__ import annotations

import importlib.metadata
from importlib import resources
from pathlib import Path

from pamet.services.desktop_storage_service import DesktopStorageService

__version__ = importlib.metadata.version(__package__)

import logging

from sivkit.extensions_loader import ExtensionsLoader

log = logging.getLogger(__name__)

pamet_root = Path(str(resources.files("pamet")))
entity_types_loader = ExtensionsLoader(pamet_root)
entity_types_loader.load_all_recursively(pamet_root / "model")

_desktop_storage_service = None  # Desktop project session service


def desktop_storage_service() -> DesktopStorageService:
    if _desktop_storage_service is None:
        raise Exception(
            "Desktop storage service not set. Instantiate it in desktop main and set via set_desktop_storage_service()."
        )
    return _desktop_storage_service


def set_desktop_storage_service(service):
    global _desktop_storage_service
    _desktop_storage_service = service
