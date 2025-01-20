"""Switch platform for qwikswitch_api."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from qwikswitchapi.constants import DeviceClass

from custom_components.hass_qwikswitchapi.const import (
    DATA_QS_CLIENT,
    DATA_QS_COORDINATOR,
    DOMAIN,
)
from custom_components.hass_qwikswitchapi.entity import QwikSwitchBaseEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from qwikswitchapi.client import QSClient
    from qwikswitchapi.entities import DeviceStatus

    from .coordinator import QwikSwitchDataUpdateCoordinator

ENTITY_DESCRIPTIONS = (
    SwitchEntityDescription(
        key="qwikswitch_api",
        name="Integration Switch",
        icon="mdi:format-quote-close",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,  # noqa: ARG001
    async_add_entities: AddEntitiesCallback,
) -> None:
    """
    Set up QwikSwitch Switch entities from a config entry.

    :param hass: HomeAssistant instance
    :param entry: Config entry
    :param async_add_entities: Callback to add entities.
    """
    coordinator: QwikSwitchDataUpdateCoordinator = hass.data[DOMAIN][
        DATA_QS_COORDINATOR
    ]
    qs_client: QSClient = hass.data[DOMAIN][DATA_QS_CLIENT]

    all_statuses: list[DeviceStatus] = coordinator.data

    switches: list[QwikSwitchRelay] = [
        QwikSwitchRelay(
            coordinator=coordinator,
            qs_client=qs_client,
            device_id=dev_status.device_id,
            name=f"QwikSwitch Relay {dev_status.device_id}",
        )
        for dev_status in all_statuses
        if dev_status.device_class == DeviceClass.relay
    ]

    if switches:
        async_add_entities(switches)


class QwikSwitchRelay(QwikSwitchBaseEntity, SwitchEntity):
    """A QwikSwitch relay (on/off) entity with optimistic updates."""

    def __init__(
        self,
        coordinator: QwikSwitchDataUpdateCoordinator,
        qs_client: QSClient,
        device_id: str,
        name: str,
    ) -> None:
        """
        Initialize the QwikSwitch relay entity.

        :param coordinator: DataUpdateCoordinator for QwikSwitch
        :param qs_client: QSClient instance
        :param device_id: ID of the device
        :param name: Friendly name
        """
        super().__init__(
            coordinator,
            qs_client,
            device_id,
            name,
            entity_suffix="switch_",
        )

    @property
    def is_on(self) -> bool:
        """
        Return True if relay is on (value > 0).

        :return: True if value > 0, else False
        """
        if self._optimistic_value is not None:
            return self._optimistic_value > 0

        dev_status = self._find_status()
        return dev_status.value > 0 if dev_status else False

    def turn_on(self, **kwargs) -> None:  # noqa: ANN003, ARG002
        """Turn the relay on (value=100)."""
        self.control_device_optimistic(100)

    def turn_off(self, **kwargs) -> None:  # noqa: ANN003, ARG002
        """Turn the relay off (value=0)."""
        self.control_device_optimistic(0)
