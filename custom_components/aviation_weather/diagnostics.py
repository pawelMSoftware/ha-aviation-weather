from __future__ import annotations

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, ENTRY_TYPE_AIRPORT, ENTRY_TYPE_FIR

#
# Add sensitive keys here in the future, e.g.
# "api_key", "token", "webhook_url"
#
TO_REDACT: set[str] = set()


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, object]:
    """Return diagnostics for a config entry."""

    entry_data = hass.data[DOMAIN][entry.entry_id]
    entry_type = entry_data.get("entry_type", ENTRY_TYPE_AIRPORT)

    coordinators: dict[str, object] = {}

    if entry_type == ENTRY_TYPE_AIRPORT:
        metar = entry_data["metar_coordinator"]
        taf = entry_data["taf_coordinator"]

        coordinators = {
            "metar": {
                "last_update_success": metar.last_update_success,
                "last_exception": repr(metar.last_exception)
                if metar.last_exception
                else None,
                "update_interval": str(metar.update_interval),
            },
            "taf": {
                "last_update_success": taf.last_update_success,
                "last_exception": repr(taf.last_exception)
                if taf.last_exception
                else None,
                "update_interval": str(taf.update_interval),
            },
        }
    elif entry_type == ENTRY_TYPE_FIR:
        sigmet = entry_data["sigmet_coordinator"]

        coordinators = {
            "sigmet": {
                "last_update_success": sigmet.last_update_success,
                "last_exception": repr(sigmet.last_exception)
                if sigmet.last_exception
                else None,
                "update_interval": str(sigmet.update_interval),
                "active_sigmet_count": len(sigmet.active_sigmets),
            },
        }

    return async_redact_data(
        {
            "config_entry": {
                "entry_id": entry.entry_id,
                "title": entry.title,
                "version": entry.version,
                "minor_version": entry.minor_version,
                "data": dict(entry.data),
                "options": dict(entry.options),
                "entry_type": entry_type,
            },
            "coordinators": coordinators,
            "home_assistant": {
                "latitude": hass.config.latitude,
                "longitude": hass.config.longitude,
                "elevation": hass.config.elevation,
                "country": hass.config.country,
                "language": hass.config.language,
                "time_zone": hass.config.time_zone,
            },
        },
        TO_REDACT,
    )
