"""Sensor platform for qwikswitch_api."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from qwikswitchapi.constants import DeviceClass
from qwikswitchapi.qs_exception import QSException

from .const import DATA_QS_CLIENT, DATA_QS_COORDINATOR, DOMAIN
from .coordinator import QwikSwitchDataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from qwikswitchapi.entities.device_status import DeviceStatus
    from qwikswitchapi.qs_client import QSClient


_LOGGER = logging.getLogger(__name__)

ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="qwikswitch_api",
        name="Integration Sensor",
        icon="mdi:format-quote-close",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,  # noqa: ARG001
    async_add_entities: AddEntitiesCallback,
) -> None:
    """
    Set up QwikSwitch Light entities from a config entry.

    :param hass: HomeAssistant instance
    :param entry: Config entry
    :param async_add_entities: Callback to add entities
    """
    coordinator: QwikSwitchDataUpdateCoordinator = hass.data[DOMAIN][
        DATA_QS_COORDINATOR
    ]
    qs_client: QSClient = hass.data[DOMAIN][DATA_QS_CLIENT]

    devices: list[QwikSwitchLight] = [
        QwikSwitchLight(
            coordinator=coordinator,
            qs_client=qs_client,
            device_id=dev_status.device_id,
            name=f"QwikSwitch Dimmer {dev_status.device_id}",
        )
        for dev_status in coordinator.data
        if dev_status.device_class == DeviceClass.dimmer
    ]

    if devices:
        async_add_entities(devices)


class QwikSwitchLight(CoordinatorEntity[QwikSwitchDataUpdateCoordinator], LightEntity):
    """Representation of a QwikSwitch Light (dimmer)."""

    def __init__(
        self,
        coordinator: QwikSwitchDataUpdateCoordinator,
        qs_client: QSClient,
        device_id: str,
        name: str,
    ) -> None:
        """
        Initialize the QwikSwitch light entity.

        :param coordinator: DataUpdateCoordinator for QwikSwitch
        :param qs_client: QSClient instance
        :param device_id: ID of the device
        :param name: Friendly name
        """
        super().__init__(coordinator)
        self._qs_client = qs_client
        self._device_id = device_id
        self._attr_name = name
        self._attr_unique_id = f"qwikswitch_light_{device_id}"
        self._attr_color_mode = ColorMode.BRIGHTNESS
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    @property
    def is_on(self) -> bool:
        """
        Determine if the dimmer is on (value > 0).

        :return: True if value > 0, else False
        """
        dev_status = self._find_status()
        return dev_status.value > 0 if dev_status else False

    @property
    def brightness(self) -> int | None:
        """
        Convert 0..100 value to 0..255 range for HA brightness.

        :return: brightness in 0..255, or None if unavailable
        """
        dev_status = self._find_status()
        if not dev_status:
            return None
        return int((dev_status.value / 100) * 255)

    def turn_on(self, **kwargs) -> None:  # noqa: ANN003
        """
        Turn on the light.

        If brightness specified, use it; else default to 255 (~100%).
        """
        brightness: int = kwargs.get("brightness", 255)
        level = int((brightness / 255) * 100)
        try:
            self._qs_client.control_device(self._device_id, level)
        except QSException:
            _LOGGER.exception("Failed to turn on light %s:", self._device_id)

    def turn_off(self, **kwargs) -> None:  # noqa: ANN003, ARG002
        """Turn off the light (set value to 0)."""
        try:
            self._qs_client.control_device(self._device_id, 0)
        except QSException:
            _LOGGER.exception("Failed to turn off light %s", self._device_id)

    def _find_status(self) -> DeviceStatus | None:
        """
        Find this device's status in the coordinator data.

        :return: The matching DeviceStatus, or None if not found
        """
        for status in self.coordinator.data:
            if status.device_id == self._device_id:
                return status
        return None
