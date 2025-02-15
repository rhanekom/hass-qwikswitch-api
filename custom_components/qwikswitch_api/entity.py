"""QwikSwitch API entities for Home Assistant."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import QwikSwitchDataUpdateCoordinator

if TYPE_CHECKING:
    from qwikswitchapi.entities import DeviceStatus

    from .command_queue import QwikSwitchCommandQueue

_LOGGER = logging.getLogger(__name__)


class QwikSwitchBaseEntity(CoordinatorEntity[QwikSwitchDataUpdateCoordinator]):
    """Base Entity using a DataUpdateCoordinator and optimistic updates."""

    def __init__(
        self,
        coordinator: QwikSwitchDataUpdateCoordinator,
        command_queue: QwikSwitchCommandQueue,
        device_id: str,
        name: str,
        entity_suffix: str = "",
    ) -> None:
        """
        Initialize the entity.

        :param coordinator: The QwikSwitchDataUpdateCoordinator handling updates
        :param command_queue: The QwikSwitchCommandQueue for sending commands
        :param device_id: Unique ID of the device
        :param name: Friendly name
        :param entity_suffix: Optional suffix (e.g., "light_", "switch_") for unique_id
        """
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_name = name
        self._command_queue = command_queue

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

    def control_device_optimistic(self, level: int) -> None:
        """Send a command to the device and set an optimistic value so the UI reflects the change immediately."""  # noqa: E501
        self.hass.create_task(
            self._command_queue.enqueue_set_device(self._device_id, level)
        )

        # Optimistically store this level and update the HA state
        self._optimistic_value = level
        self.schedule_update_ha_state()

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
