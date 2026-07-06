"""Weather entity for Aviation Weather, based on current METAR data."""

from __future__ import annotations

import math

from homeassistant.components.weather import WeatherEntity
from homeassistant.const import UnitOfPressure, UnitOfSpeed, UnitOfTemperature
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.sun import is_up
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..entity import airport_device_info
from ..metar.coordinator import MetarCoordinator
from ..metar.models import MetarData
from .cloud_coverage_mapper import map_cloud_coverage
from .condition_mapper import map_condition


class AviationWeatherEntity(
    CoordinatorEntity[MetarCoordinator],
    WeatherEntity,
):
    """Weather entity showing current conditions from the airport's METAR.

    This complements the existing sensor entities rather than replacing
    them: it exists so Home Assistant's native weather card / forecast
    UI can display this airport, while the detailed sensors remain
    available for automations and dashboards that want individual
    values.

    Forecast support (based on TAF data) is not implemented yet; this
    entity reports current conditions only.
    """

    _attr_has_entity_name = True
    _attr_name = None
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_native_wind_speed_unit = UnitOfSpeed.KNOTS

    def __init__(
        self,
        coordinator: MetarCoordinator,
        airport_icao: str,
    ) -> None:
        super().__init__(coordinator)

        self._airport_icao = airport_icao

        # unique_id must not depend on coordinator.data: the airport may
        # have no current METAR report when this entity is constructed
        # (see MetarSummarySensor for the same reasoning).
        self._attr_unique_id = f"{airport_icao}_weather"

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
    def condition(
        self,
    ) -> str | None:
        if self.airport_data is None:
            return None

        return map_condition(
            self.airport_data,
            is_daytime=is_up(
                self.hass,
            ),
        )

    @property
    def native_temperature(
        self,
    ) -> float | None:
        if self.airport_data is None:
            return None

        return self.airport_data.temperature

    @property
    def native_pressure(
        self,
    ) -> float | None:
        if self.airport_data is None:
            return None

        return self.airport_data.pressure

    @property
    def native_dew_point(
        self,
    ) -> float | None:
        if self.airport_data is None:
            return None

        return self.airport_data.dewpoint

    @property
    def native_wind_speed(
        self,
    ) -> float | None:
        if self.airport_data is None:
            return None

        return self.airport_data.wind_speed

    @property
    def native_wind_gust_speed(
        self,
    ) -> float | None:
        if self.airport_data is None:
            return None

        return self.airport_data.wind_gust

    @property
    def wind_bearing(
        self,
    ) -> float | str | None:
        if self.airport_data is None:
            return None

        wind_direction = self.airport_data.wind_direction

        if wind_direction is None:
            return None

        try:
            return float(
                wind_direction,
            )
        except ValueError:
            # METAR sometimes reports "VRB" (variable wind direction)
            # instead of a numeric bearing.
            return None

    @property
    def humidity(
        self,
    ) -> float | None:
        if self.airport_data is None:
            return None

        temperature = self.airport_data.temperature
        dewpoint = self.airport_data.dewpoint

        if temperature is None or dewpoint is None:
            return None

        return _relative_humidity_percent(
            temperature,
            dewpoint,
        )

    @property
    def cloud_coverage(
        self,
    ) -> float | None:
        if self.airport_data is None:
            return None

        return map_cloud_coverage(
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


def _relative_humidity_percent(
    temperature_celsius: float,
    dewpoint_celsius: float,
) -> float:
    """Approximate relative humidity from temperature and dew point.

    Uses the August-Roche-Magnus approximation, the same formula
    commonly used to derive RH from METAR temperature/dew point pairs.
    Accurate to within about 0.1-0.5% RH for typical atmospheric
    conditions.
    """

    def saturation_vapor_pressure(
        celsius: float,
    ) -> float:
        return 6.1094 * math.exp(
            (17.625 * celsius) / (celsius + 243.04),
        )

    actual_vapor_pressure = saturation_vapor_pressure(
        dewpoint_celsius,
    )
    saturation_pressure = saturation_vapor_pressure(
        temperature_celsius,
    )

    return round(
        100 * (actual_vapor_pressure / saturation_pressure),
        1,
    )
