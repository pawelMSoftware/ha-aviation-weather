from __future__ import annotations

from ..models.airport import Airport
from .template_renderer import TemplateRenderer


class CountryRenderer(TemplateRenderer):
    """Render airport country file."""

    def render(
        self,
        airports: list[Airport],
    ) -> str:
        """Render airport file."""

        return self.render_template(
            "country.py.j2",
            airports=airports,
        )
