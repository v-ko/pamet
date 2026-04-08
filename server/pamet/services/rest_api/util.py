from typing import Any, Mapping


def envelope(data: Mapping[str, Any] | list[Any]) -> dict[str, Any]:
    return dict(data=data)
