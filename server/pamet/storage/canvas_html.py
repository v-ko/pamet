"""Read/write .canvas files as HTML with embedded JSON.

Uses Jinja2-style template (template.j2) with simple string replace.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_RESOURCES_DIR = Path(__file__).resolve().parent.parent / "resources" / "mini_viewer"
_template_cache: str | None = None
_viewer_js_cache: str | None = None
_viewer_css_cache: str | None = None


def _get_template() -> str:
    global _template_cache
    if _template_cache is None:
        _template_cache = (_RESOURCES_DIR / "template.j2").read_text(encoding="utf-8")
    return _template_cache


def _get_viewer_js() -> str:
    global _viewer_js_cache
    if _viewer_js_cache is None:
        _viewer_js_cache = (_RESOURCES_DIR / "viewer.js").read_text(encoding="utf-8")
    return _viewer_js_cache


def _get_viewer_css() -> str:
    global _viewer_css_cache
    if _viewer_css_cache is None:
        _viewer_css_cache = (_RESOURCES_DIR / "viewer.css").read_text(encoding="utf-8")
    return _viewer_css_cache


def dump_canvas_html(page_data: dict[str, Any], *, indent: int = 2) -> str:
    schema_version = str(page_data.get("schema_version", 5))
    json_payload = json.dumps(page_data, indent=indent, ensure_ascii=False)
    html = _get_template()
    html = html.replace("{{ schema_version }}", schema_version)
    html = html.replace("{{ data }}", json_payload)
    html = html.replace("{{ style }}", _get_viewer_css())
    html = html.replace("{{ script }}", _get_viewer_js())
    return html


def write_canvas_file(
    path: Path, page_data: dict[str, Any], *, indent: int = 2
) -> None:
    path.write_text(dump_canvas_html(page_data, indent=indent), encoding="utf-8")


def load_canvas_json(html: str) -> dict[str, Any]:
    """Extract and parse the JSON payload from an HTML canvas string."""
    open_tag = '<script type="application/json" id="pamet-data">'
    start = html.find(open_tag)
    if start == -1:
        raise ValueError('No <script id="pamet-data"> tag found')
    start += len(open_tag)
    end = html.find("</script>", start)
    if end == -1:
        raise ValueError("No closing </script> for pamet-data")
    return json.loads(html[start:end])


def read_canvas_file(path: Path) -> dict[str, Any]:
    """Read a .canvas file (HTML or legacy plain-JSON) and return the data dict."""
    text = path.read_text(encoding="utf-8")
    if text.lstrip().startswith("{"):
        return json.loads(text)
    return load_canvas_json(text)
