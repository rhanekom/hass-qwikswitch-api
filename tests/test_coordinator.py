"""Tests for the data update coordinator."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.qwikswitch_api.const import (
    DATA_COMMAND_QUEUE,
    DATA_QS_COORDINATOR,
    DOMAIN,
)

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_coordinator_first_refresh_populates_data(
    hass: HomeAssistant,
    setup_integration: tuple[MagicMock, MockConfigEntry],
) -> None:
    """The coordinator's data holds the polled device statuses after setup."""
    coordinator = hass.data[DOMAIN][DATA_QS_COORDINATOR]

    assert coordinator.last_update_success is True
    device_ids = {status.device_id for status in coordinator.data}
    assert device_ids == {"dimmer-1", "relay-1"}


async def test_coordinator_update_wraps_errors(
    hass: HomeAssistant,
    setup_integration: tuple[MagicMock, MockConfigEntry],
) -> None:
    """A poll failure is surfaced as UpdateFailed."""
    coordinator = hass.data[DOMAIN][DATA_QS_COORDINATOR]
    queue = hass.data[DOMAIN][DATA_COMMAND_QUEUE]
    queue.enqueue_poll = AsyncMock(side_effect=RuntimeError("api down"))

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
