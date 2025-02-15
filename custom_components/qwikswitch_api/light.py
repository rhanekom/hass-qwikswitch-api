"""Sensor platform for qwikswitch_api."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.light import LightEntity
from homeassistant.components.light.const import ColorMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from qwikswitchapi.constants import DeviceClass

from .command_queue import QwikSwitchCommandQueue
from .const import (
    DATA_COMMAND_QUEUE,
    DATA_QS_COORDINATOR,
    DOMAIN,
    MANUFACTURER,
    MODEL_DIMMER,
)
from .entity import QwikSwitchBaseEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .command_queue import QwikSwitchCommandQueue
    from .coordinator import QwikSwitchDataUpdateCoordinator


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
    queue: QwikSwitchCommandQueue = hass.data[DOMAIN][DATA_COMMAND_QUEUE]

    devices: list[QwikSwitchLight] = [
        QwikSwitchLight(
            coordinator=coordinator,
            command_queue=queue,
            device_id=dev_status.device_id,
            name=f"QwikSwitch Dimmer {dev_status.device_id}",
        )
        for dev_status in coordinator.data
        if dev_status.device_class == DeviceClass.dimmer
    ]

    if devices:
        async_add_entities(devices)


class QwikSwitchLight(QwikSwitchBaseEntity, LightEntity):
    """Representation of a QwikSwitch Light (dimmer)."""

    def __init__(
        self,
        coordinator: QwikSwitchDataUpdateCoordinator,
        command_queue: QwikSwitchCommandQueue,
        device_id: str,
        name: str,
    ) -> None:
        """
        Initialize the QwikSwitch light entity.

        :param coordinator: DataUpdateCoordinator for QwikSwitch
        :param command_queue: CommandQueue for sending commands
        :param device_id: ID of the device
        :param name: Friendly name
        """
        super().__init__(
            coordinator, command_queue, device_id, name, entity_suffix="light_"
        )

        self._attr_color_mode = ColorMode.BRIGHTNESS
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    @property
    def is_on(self) -> bool:
        """
        Determine if the dimmer is on (value > 0).

        :return: True if value > 0, else False
        """
        if self._optimistic_value is not None:
            return self._optimistic_value > 0

        dev_status = self._find_status()
        return dev_status.value > 0 if dev_status else False

    @property
    def brightness(self) -> int | None:
        """
        Convert 0..100 value to 0..255 range for HA brightness.

        :return: brightness in 0..255, or None if unavailable
        """
        level = self._optimistic_value

        if level is None:
            dev_status = self._find_status()
            if not dev_status:
                return None
            level = dev_status.value

        # Convert from [0..100] to [0..255]
        return int((level / 100) * 255)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information so this entity is associated with a device in Home Assistant."""  # noqa: E501
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._attr_name,
            manufacturer=MANUFACTURER,
            model=MODEL_DIMMER,
        )

    def turn_on(self, **kwargs) -> None:  # noqa: ANN003
        """
        Turn on the light.

        If brightness specified, use it; else default to 255 (~100%).
        """
        brightness: int = kwargs.get("brightness", 255)
        level = int((brightness / 255) * 100)
        self.control_device_optimistic(level)

    def turn_off(self, **kwargs) -> None:  # noqa: ANN003, ARG002
        """Turn off the light (set value to 0)."""
        self.control_device_optimistic(0)
