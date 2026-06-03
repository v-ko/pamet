"""Lock-file based single-instance check for the desktop server."""

from __future__ import annotations

import logging
from pathlib import Path

import requests

log = logging.getLogger(__name__)

LOCALHOST = "http://localhost"


def lock_path(config_dir: Path) -> Path:
    return config_dir / ".local_server.lock"


def get_port_from_lock_file(config_dir: Path) -> int | None:
    lp = lock_path(config_dir)
    if lp.exists():
        return int(lp.read_text())
    return None


def write_port_to_lock_file(config_dir: Path, port: int):
    lp = lock_path(config_dir)
    lp.parent.mkdir(parents=True, exist_ok=True)
    lp.write_text(str(port))


def remove_lock_file(config_dir: Path):
    lock_path(config_dir).unlink(missing_ok=True)


def get_running_instance_port(config_dir: Path) -> int | None:
    """Return the port of an already-running instance, or None."""
    port = get_port_from_lock_file(config_dir)
    if port is None:
        return None

    try:
        reply = requests.get(f"{LOCALHOST}:{port}/version")  # @IgnoreException
        if reply.ok and "data" in reply.json():
            return port
    except requests.ConnectionError:
        pass
    return None
