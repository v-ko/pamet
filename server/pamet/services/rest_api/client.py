"""Lightweight REST client for sending commands to a running desktop server."""

from __future__ import annotations

import logging

import requests

log = logging.getLogger(__name__)

LOCALHOST = "http://localhost"


def send_command(port: int, command_name: str, payload: dict | None = None):
    """Send a public command to the running desktop server instance."""
    try:
        reply = requests.post(
            f"{LOCALHOST}:{port}/desktop/commands/{command_name}/",
            json=payload,
        )
        if not reply.ok:
            log.error(
                "Command %s failed with status %s: %s",
                command_name,
                reply.status_code,
                reply.text,
            )
    except requests.ConnectionError:
        log.error(
            "Failed to send command %s to running instance on port %s",
            command_name,
            port,
        )
