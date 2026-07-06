from __future__ import annotations

from .template_renderer import TemplateRenderer


class CountryRegistryRenderer(TemplateRenderer):
    """Render country registry."""

    def render(
        self,
        countries: dict[str, str],
        continents: dict[str, str],
        continent_names: dict[str, str],
    ) -> str:
        """Render country registry."""

        return self.render_template(
            "country_registry.py.j2",
            countries=countries,
            continents=continents,
            continent_names=continent_names,
        )
