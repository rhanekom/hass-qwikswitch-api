"""DataUpdateCoordinator for qwikswitch_api."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from qwikswitchapi.entities import DeviceStatus

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from qwikswitchapi.client import QSClient

_LOGGER = logging.getLogger(__name__)


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class QwikSwitchDataUpdateCoordinator(DataUpdateCoordinator[list[DeviceStatus]]):
    """
    Coordinator to fetch data from the QwikSwitch API at a specified interval.

    The `.data` property will be a list of DeviceStatus objects.
    """

    def __init__(
        self, hass: HomeAssistant, qs_client: QSClient, poll_frequency: int
    ) -> None:
        """
        Initialize the QwikSwitch coordinator.

        :param hass: HomeAssistant instance
        :param qs_client: QSClient instance
        :param poll_frequency: Poll interval in seconds.
        """
        self._qs_client = qs_client
        update_interval = timedelta(seconds=poll_frequency)

        super().__init__(
            hass,
            _LOGGER,
            name="qwikswitch_api_coordinator",
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> list[DeviceStatus]:
        """
        Fetch data from QwikSwitch.

        :return: A list of DeviceStatus objects.
        :raises UpdateFailed: if fetching data fails.
        """
        try:
            device_statuses = await self.hass.async_add_executor_job(
                self._qs_client.get_all_device_status
            )
        except Exception as err:
            message = f"Error fetching QwikSwitch data: {err}"
            raise UpdateFailed(message) from err
        else:
            # get_all_device_status() returns a DeviceStatuses object; use `.statuses`
            return device_statuses.statuses
