"""METAR sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..entity import airport_device_info, enum_value
from .coordinator import MetarCoordinator
from .models import MetarData


@dataclass(frozen=True, kw_only=True)
class MetarSensorEntityDescription(
    SensorEntityDescription,
):
    """METAR sensor description."""

    value_fn: Callable[[MetarData], object | None]
    icon: str | None = None


def format_visibility(meters: int | None) -> str | None:
    """Format visibility in metres for display.

    Converts the stored metre value to a human-readable string,
    switching to kilometres when the value is ≥ 1000 m. The special
    sentinel value 10000 (CAVOK / 9999) is always rendered as "10+ km"
    because it means "at least 10 km", not exactly 10 km.

    Returns None when meters is None (not reported / not parseable),
    so the sensor shows as unavailable rather than an empty string.

    Examples:
        500   → "500 m"
        800   → "800 m"
        1500  → "1.5 km"
        3500  → "3.5 km"
        7000  → "7 km"
        10000 → "10+ km"
    """
    if meters is None:
        return None

    if meters == 10000:
        return "10+ km"

    if meters < 1000:
        return f"{meters} m"

    km = meters / 1000
    # Remove trailing zero: 7.0 → "7", 1.5 → "1.5"
    km_str = f"{km:.1f}".rstrip("0").rstrip(".")
    return f"{km_str} km"


METAR_SENSORS: tuple[
    MetarSensorEntityDescription,
    ...,
] = (
    MetarSensorEntityDescription(
        key="temperature",
        name="Temperature",
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement="°C",
        value_fn=lambda data: data.temperature,
    ),
    MetarSensorEntityDescription(
        key="dewpoint",
        name="Dew Point",
        icon="mdi:thermometer-water",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement="°C",
        value_fn=lambda data: data.dewpoint,
    ),
    MetarSensorEntityDescription(
        key="pressure",
        name="Pressure",
        icon="mdi:gauge",
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        native_unit_of_measurement="hPa",
        value_fn=lambda data: data.pressure,
    ),
    MetarSensorEntityDescription(
        key="sea_level_pressure",
        name="Sea Level Pressure",
        icon="mdi:gauge",
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        native_unit_of_measurement="hPa",
        value_fn=lambda data: data.sea_level_pressure,
    ),
    MetarSensorEntityDescription(
        key="wind_speed",
        name="Wind Speed",
        icon="mdi:weather-windy",
        native_unit_of_measurement="kt",
        value_fn=lambda data: data.wind_speed,
    ),
    MetarSensorEntityDescription(
        key="wind_gust",
        name="Wind Gust",
        icon="mdi:weather-windy-variant",
        native_unit_of_measurement="kt",
        value_fn=lambda data: data.wind_gust,
    ),
    MetarSensorEntityDescription(
        key="wind_direction",
        name="Wind Direction",
        icon="mdi:compass",
        value_fn=lambda data: data.wind_direction,
    ),
    MetarSensorEntityDescription(
        key="visibility",
        name="Visibility",
        icon="mdi:eye",
        value_fn=lambda data: format_visibility(data.visibility_meters),
    ),
    MetarSensorEntityDescription(
        key="metar_type",
        name="METAR Type",
        icon="mdi:file-document-outline",
        value_fn=lambda data: data.metar_type,
    ),
    MetarSensorEntityDescription(
        key="snow_depth",
        name="Snow Depth",
        icon="mdi:snowflake",
        native_unit_of_measurement="in",
        value_fn=lambda data: data.snow_depth,
    ),
    MetarSensorEntityDescription(
        key="vertical_visibility",
        name="Vertical Visibility",
        icon="mdi:image-filter-hdr",
        native_unit_of_measurement="ft",
        value_fn=lambda data: data.vertical_visibility,
    ),
    MetarSensorEntityDescription(
        key="observation_time",
        name="Observation Time",
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data.observation_time,
    ),
    MetarSensorEntityDescription(
        key="weather",
        name="Weather",
        icon="mdi:weather-partly-rainy",
        value_fn=lambda data: data.weather.raw if data.weather else None,
    ),
)


class MetarSummarySensor(
    CoordinatorEntity[MetarCoordinator],
    SensorEntity,
):
    """METAR summary sensor."""

    _attr_has_entity_name = True
    # No _attr_icon here on purpose: this entity's icon varies by flight
    # category (state) via icons.json's per-state overrides, keyed on
    # this translation_key. A static _attr_icon would take priority over
    # icons.json and silently defeat that.
    _attr_translation_key = "metar_summary"

    def __init__(
        self,
        coordinator: MetarCoordinator,
        airport_icao: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_name = "METAR"
        self._airport_icao = airport_icao

        # unique_id must not depend on coordinator.data: the first
        # refresh may fail (e.g. no current report for this airport
        # yet), in which case coordinator.data is still None when this
        # entity is constructed.
        self._attr_unique_id = f"{airport_icao}_metar_summary"

    @property
    def airport_data(
        self,
    ) -> MetarData | None:
        return self.coordinator.data

    @property
    def available(
        self,
    ) -> bool:
        return super().available and self.airport_data is not None

    @property
    def native_value(
        self,
    ) -> str | None:
        if self.airport_data is None:
            return None

        return enum_value(
            self.airport_data.flight_category,
        )

    @property
    def device_info(
        self,
    ) -> DeviceInfo:
        airport_name = self.airport_data.airport_name if self.airport_data else None

        return airport_device_info(
            airport_icao=self._airport_icao,
            airport_name=airport_name,
        )

    @property
    def extra_state_attributes(
        self,
    ) -> dict[str, object]:
        if self.airport_data is None:
            return {}

        weather = self.airport_data.weather

        return {
            "airport": self.airport_data.airport,
            "airport_name": self.airport_data.airport_name,
            "temperature": self.airport_data.temperature,
            "dewpoint": self.airport_data.dewpoint,
            "pressure": self.airport_data.pressure,
            "sea_level_pressure": (self.airport_data.sea_level_pressure),
            "wind_speed": self.airport_data.wind_speed,
            "wind_gust": self.airport_data.wind_gust,
            "wind_direction": (self.airport_data.wind_direction),
            "visibility": format_visibility(self.airport_data.visibility_meters),
            "weather": weather.raw if weather else None,
            "weather_intensity": (
                weather.intensity.value if weather and weather.intensity else None
            ),
            "weather_phenomena": (
                [phenomenon.value for phenomenon in weather.phenomena]
                if weather
                else []
            ),
            "metar_type": enum_value(
                self.airport_data.metar_type,
            ),
            "observation_time": (self.airport_data.observation_time),
            "snow_depth": self.airport_data.snow_depth,
            "vertical_visibility": (self.airport_data.vertical_visibility),
            "cloud_layers": [
                {
                    "cover": enum_value(layer.cover),
                    "base": layer.base,
                }
                for layer in self.airport_data.cloud_layers
            ],
            "raw_metar": self.airport_data.raw_metar,
        }


class MetarSensor(
    CoordinatorEntity[MetarCoordinator],
    SensorEntity,
):
    """METAR detail sensor."""

    entity_description: MetarSensorEntityDescription

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MetarCoordinator,
        description: MetarSensorEntityDescription,
        airport_icao: str,
    ) -> None:
        super().__init__(coordinator)

        self.entity_description = description
        self._airport_icao = airport_icao

        # unique_id must not depend on coordinator.data; see
        # MetarSummarySensor.__init__ for why.
        self._attr_unique_id = f"{airport_icao}_{description.key}"

    @property
    def airport_data(
        self,
    ) -> MetarData | None:
        return self.coordinator.data

    @property
    def available(
        self,
    ) -> bool:
        return super().available and self.airport_data is not None

    @property
    def native_value(
        self,
    ) -> object | None:
        if self.airport_data is None:
            return None

        return self.entity_description.value_fn(
            self.airport_data,
        )

    @property
    def device_info(
        self,
    ) -> DeviceInfo:
        airport_name = self.airport_data.airport_name if self.airport_data else None

        return airport_device_info(
            airport_icao=self._airport_icao,
            airport_name=airport_name,
        )
