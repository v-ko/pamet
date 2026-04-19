from __future__ import annotations

import secrets

# Generated once per desktop process lifetime; imported by server and app window.
DESKTOP_ACCESS_TOKEN = secrets.token_urlsafe(32)
