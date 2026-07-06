"""TAF sensors."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..entity import airport_device_info, enum_value
from .coordinator import TafCoordinator
from .models import TafData


class TafSummarySensor(
    CoordinatorEntity[TafCoordinator],
    SensorEntity,
):
    """TAF summary sensor."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:weather-cloudy-clock"

    def __init__(
        self,
        coordinator: TafCoordinator,
        airport_icao: str,
    ) -> None:
        super().__init__(coordinator)

        self._attr_name = "TAF"
        self._airport_icao = airport_icao

        # unique_id must not depend on coordinator.data: many airports
        # have no TAF data at all, so coordinator.data may permanently
        # stay None for this entity.
        self._attr_unique_id = f"{airport_icao}_taf_summary"

    @property
    def airport_data(
        self,
    ) -> TafData | None:
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

        return "Forecast"

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

        return {
            "airport": self.airport_data.airport,
            "issue_time": self.airport_data.issue_time,
            "valid_from": self.airport_data.valid_from,
            "valid_to": self.airport_data.valid_to,
            "raw_taf": self.airport_data.raw_taf,
            "forecast_count": len(
                self.airport_data.forecasts,
            ),
            "forecasts": [
                {
                    "time_from": forecast.time_from,
                    "time_to": forecast.time_to,
                    "change_type": enum_value(forecast.change_type),
                    "wind_direction": forecast.wind_direction,
                    "wind_speed": forecast.wind_speed,
                    "wind_gust": forecast.wind_gust,
                    "visibility": forecast.visibility,
                    "weather": forecast.weather,
                    "clouds": [
                        {
                            "cover": cloud.cover,
                            "base": cloud.base,
                            "type": cloud.cloud_type,
                        }
                        for cloud in forecast.clouds
                    ],
                }
                for forecast in self.airport_data.forecasts
            ],
        }
