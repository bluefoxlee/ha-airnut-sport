"""Sensor entities for AirNut Sport."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    PERCENTAGE,
    UnitOfTemperature,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_MAC, DOMAIN

SENSOR_NAMES = {
    "temperature": "溫度",
    "humidity": "濕度",
    "pm25": "PM2.5",
    "battery": "電量",
    "firmware_version": "韌體版本",
    "hardware_revision": "硬體版本",
    "software_version": "軟體版本",
}


async def async_setup_entry(hass, config_entry, async_add_entities) -> None:
    """Create AirNut Sport sensor entities."""

    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            AirNutSensor(coordinator, config_entry.data[CONF_MAC], sensor_type)
            for sensor_type in SENSOR_NAMES
        ]
    )


class AirNutSensor(CoordinatorEntity, SensorEntity):
    """Represent one value reported by an AirNut Sport device."""

    def __init__(self, coordinator, address: str, sensor_type: str) -> None:
        super().__init__(coordinator)
        self._address = address
        self._sensor_type = sensor_type
        self._attr_has_entity_name = True
        self._attr_name = SENSOR_NAMES[sensor_type]
        self._attr_unique_id = f"airnut_sport_{address.replace(':', '').lower()}_{sensor_type}"

        if sensor_type == "temperature":
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif sensor_type == "humidity":
            self._attr_device_class = SensorDeviceClass.HUMIDITY
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif sensor_type == "pm25":
            self._attr_device_class = SensorDeviceClass.PM25
            self._attr_native_unit_of_measurement = (
                CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
            )
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif sensor_type == "battery":
            self._attr_device_class = SensorDeviceClass.BATTERY
            self._attr_native_unit_of_measurement = PERCENTAGE
        else:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            self._attr_icon = "mdi:chip"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the shared AirNut Sport device."""

        return DeviceInfo(
            identifiers={(DOMAIN, self._address)},
            name="空氣果 Sport",
            manufacturer="AirNut / 墨跡",
            model="Sport",
        )
    @property
    def native_value(self):
        """Return the latest decoded value."""

        return (
            self.coordinator.data.get(self._sensor_type)
            if self.coordinator.data
            else None
        )
