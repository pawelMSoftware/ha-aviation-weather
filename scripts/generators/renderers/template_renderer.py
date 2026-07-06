from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader


def py_string(value: str) -> str:
    """Render Python string literal."""

    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )

    if len(escaped) <= 60:
        return f'"{escaped}"'

    parts = textwrap.wrap(
        escaped,
        width=60,
        break_long_words=False,
        break_on_hyphens=False,
    )

    body = "\n".join(f'    "{part}"' for part in parts)

    return f"(\n{body}\n)"


class TemplateRenderer:
    """Base renderer for Jinja templates."""

    def __init__(self) -> None:
        templates = Path(__file__).parent.parent.parent / "templates"

        self._environment = Environment(
            loader=FileSystemLoader(
                templates,
            ),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

        self._environment.filters["py_string"] = py_string

    def render_template(
        self,
        template: str,
        **context: Any,
    ) -> str:
        """Render template."""

        return self._environment.get_template(
            template,
        ).render(
            **context,
        )
