from __future__ import annotations

from .template_renderer import TemplateRenderer


class RegistryRenderer(TemplateRenderer):
    """Render airport registry."""

    def render(
        self,
        countries: list[str],
    ) -> str:
        """Render registry."""

        return self.render_template(
            "registry.py.j2",
            countries=countries,
        )
