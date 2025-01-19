"""Switch platform for qwikswitch_api."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from qwikswitchapi.constants import DeviceClass
from qwikswitchapi.qs_exception import QSException

from custom_components.hass_qwikswitchapi.const import (
    DATA_QS_CLIENT,
    DATA_QS_COORDINATOR,
    DOMAIN,
)

from .coordinator import QwikSwitchDataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from qwikswitchapi.entities.device_status import DeviceStatus
    from qwikswitchapi.qs_client import QSClient


_LOGGER = logging.getLogger(__name__)

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


class QwikSwitchRelay(CoordinatorEntity[QwikSwitchDataUpdateCoordinator], SwitchEntity):
    """Representation of a QwikSwitch relay (on/off)."""

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
        super().__init__(coordinator)
        self._qs_client = qs_client
        self._device_id = device_id
        self._attr_name = name
        self._attr_unique_id = f"qwikswitch_switch_{device_id}"

        # Store an "optimistic" level (0..100) after toggling.
        # If None, we rely on the polled data from coordinator.data.
        self._optimistic_level: int | None = None

    @property
    def is_on(self) -> bool:
        """
        Return True if relay is on (value > 0).

        :return: True if value > 0, else False
        """
        if self._optimistic_level is not None:
            return self._optimistic_level > 0

        dev_status = self._find_status()
        return dev_status.value > 0 if dev_status else False

    def turn_on(self, **kwargs) -> None:  # noqa: ANN003, ARG002
        """Turn the relay on (value=100)."""
        try:
            self._qs_client.control_device(self._device_id, 100)
            # Optimistically set our local assumption
            self._optimistic_level = 100
            # Immediately tell HA to update this entity's state in the UI
            self.schedule_update_ha_state()
        except QSException:
            self._optimistic_level = None
            _LOGGER.exception("Failed to turn on relay %s:", self._device_id)

    def turn_off(self, **kwargs) -> None:  # noqa: ANN003, ARG002
        """Turn the relay off (value=0)."""
        try:
            self._qs_client.control_device(self._device_id, 0)
            self._optimistic_level = 0
            self.schedule_update_ha_state()
        except QSException:
            self._optimistic_level = None
            _LOGGER.exception("Failed to turn off relay %s:", self._device_id)

    def _find_status(self) -> DeviceStatus | None:
        """
        Retrieve the matching DeviceStatus from the coordinator data.

        :return: The DeviceStatus for this device, or None if not found
        """
        for status in self.coordinator.data:
            if status.device_id == self._device_id:
                return status
        return None

    def _handle_coordinator_update(self) -> None:
        """
        Override to reconcile polled data with optimistic state.

        If the new polled data for this device doesn't match our optimistic assumption,
        we reset the assumption to None, letting the real data take over.
        """
        dev_status = self._find_status()
        if (
            dev_status is not None
            and self._optimistic_level is not None
            and dev_status.value != self._optimistic_level
        ):
            # The device reported a different value than our optimistic guess
            self._optimistic_level = None

        # Call the parent method so the entity is updated normally
        super()._handle_coordinator_update()
