"""QwikSwitch API entities for Home Assistant."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from qwikswitchapi.exceptions import QSError

from .coordinator import QwikSwitchDataUpdateCoordinator

if TYPE_CHECKING:
    from qwikswitchapi.client import QSClient
    from qwikswitchapi.entities import DeviceStatus

_LOGGER = logging.getLogger(__name__)


class QwikSwitchBaseEntity(CoordinatorEntity[QwikSwitchDataUpdateCoordinator]):
    """Base Entity using a DataUpdateCoordinator and optimistic updates."""

    def __init__(
        self,
        coordinator: QwikSwitchDataUpdateCoordinator,
        qs_client: QSClient,
        device_id: str,
        name: str,
        entity_suffix: str = "",
    ) -> None:
        """
        Initialize the entity.

        :param coordinator: The QwikSwitchDataUpdateCoordinator handling updates
        :param qs_client: QwikSwitch client for controlling devices
        :param device_id: Unique ID of the device
        :param name: Friendly name
        :param entity_suffix: Optional suffix (e.g., "light_", "switch_") for unique_id
        """
        super().__init__(coordinator)
        self._qs_client = qs_client
        self._device_id = device_id
        self._attr_name = name

        # A single place for your entity's unique ID
        self._attr_unique_id = f"qwikswitch_{entity_suffix}{device_id}"

        # We'll store an "optimistic" value (0..100 for dimmers/switches).
        # If None, we rely on the polled data from the coordinator.
        self._optimistic_value: int | None = None

    def _find_status(self) -> DeviceStatus | None:
        """
        Find this device's status in the coordinator data.

        :return: The matching DeviceStatus, or None if not found
        """
        if not self.coordinator.data:
            return None
        for status in self.coordinator.data:
            if status.device_id == self._device_id:
                return status
        return None

    def control_device_optimistic(self, new_value: int) -> None:
        """Send a command to the device and set an optimistic value so the UI reflects the change immediately."""  # noqa: E501
        try:
            self._qs_client.control_device(self._device_id, new_value)
            self._optimistic_value = new_value
            # Force immediate UI update
            self.schedule_update_ha_state()
        except QSError:
            self._optimistic_value = None
            _LOGGER.exception(
                "Failed to control device %s with value %s:", self._device_id, new_value
            )

    def _handle_coordinator_update(self) -> None:
        """Reconcile the polled device value with our optimistic assumption. If they differ, discard the assumption."""  # noqa: E501
        dev_status = self._find_status()
        if (
            dev_status
            and self._optimistic_value is not None
            and dev_status.value != self._optimistic_value
        ):
            # The real polled value disagrees with our assumption
            self._optimistic_value = None

        # Call the parent to do normal coordinator update tasks
        super()._handle_coordinator_update()
