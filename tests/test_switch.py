"""Tests for the switch (relay) platform."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from custom_components.qwikswitch_api.const import (
    DATA_COMMAND_QUEUE,
    DATA_QS_COORDINATOR,
    DOMAIN,
    MANUFACTURER,
    MODEL_RELAY,
)
from custom_components.qwikswitch_api.switch import QwikSwitchRelay, async_setup_entry

from .conftest import DIMMER_TYPE, RELAY_TYPE, make_device_status

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

RELAY_ENTITY_ID = "switch.qwikswitch_relay_relay_1"


def _make_relay(optimistic: int | None = None, *statuses) -> QwikSwitchRelay:
    """Build a relay entity with an optional optimistic value."""
    coordinator = MagicMock()
    coordinator.data = list(statuses)
    relay = QwikSwitchRelay(coordinator, MagicMock(), "relay-1", "name")
    relay._optimistic_value = optimistic
    return relay


@pytest.mark.parametrize(
    ("optimistic", "value", "expected"),
    [
        (None, 100, True),
        (None, 0, False),
        (100, None, True),
        (0, None, False),
    ],
)
def test_is_on(optimistic: int | None, value: int | None, expected: bool) -> None:
    """is_on reflects the optimistic value first, else the polled value."""
    statuses = (
        [make_device_status("relay-1", value, RELAY_TYPE)] if value is not None else []
    )
    relay = _make_relay(optimistic, *statuses)
    assert relay.is_on is expected


def test_is_on_false_without_status() -> None:
    """is_on is False when there is neither optimistic nor polled data."""
    assert _make_relay(None).is_on is False


def test_device_info() -> None:
    """Device info identifies the relay with the right model and manufacturer."""
    info = _make_relay().device_info
    assert info["identifiers"] == {(DOMAIN, "relay-1")}
    assert info["manufacturer"] == MANUFACTURER
    assert info["model"] == MODEL_RELAY


def test_turn_on() -> None:
    """turn_on requests level 100."""
    relay = _make_relay()
    relay.control_device_optimistic = MagicMock()
    relay.turn_on()
    relay.control_device_optimistic.assert_called_once_with(100)


def test_turn_off() -> None:
    """turn_off requests level 0."""
    relay = _make_relay()
    relay.control_device_optimistic = MagicMock()
    relay.turn_off()
    relay.control_device_optimistic.assert_called_once_with(0)


async def test_async_setup_entry_creates_only_relays() -> None:
    """Only relay-class devices become switch entities."""
    coordinator = MagicMock()
    coordinator.data = [
        make_device_status("dimmer-1", 40, DIMMER_TYPE),
        make_device_status("relay-1", 100, RELAY_TYPE),
    ]
    hass = MagicMock()
    hass.data = {
        DOMAIN: {
            DATA_QS_COORDINATOR: coordinator,
            DATA_COMMAND_QUEUE: MagicMock(),
        }
    }
    added: list[QwikSwitchRelay] = []

    await async_setup_entry(hass, MagicMock(), added.extend)

    assert len(added) == 1
    assert added[0].unique_id == "qwikswitch_switch_relay-1"


async def test_async_setup_entry_no_relays_adds_nothing() -> None:
    """With no relays present, no entities are added."""
    coordinator = MagicMock()
    coordinator.data = [make_device_status("dimmer-1", 40, DIMMER_TYPE)]
    hass = MagicMock()
    hass.data = {
        DOMAIN: {
            DATA_QS_COORDINATOR: coordinator,
            DATA_COMMAND_QUEUE: MagicMock(),
        }
    }
    add_entities = MagicMock()

    await async_setup_entry(hass, MagicMock(), add_entities)

    add_entities.assert_not_called()


async def test_turn_on_service_calls_client(
    hass: HomeAssistant,
    setup_integration: tuple[MagicMock, MockConfigEntry],
) -> None:
    """Calling switch.turn_on drives the API with level 100."""
    mock_client, _ = setup_integration

    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": RELAY_ENTITY_ID},
        blocking=True,
    )
    await hass.async_block_till_done()
    await hass.data[DOMAIN][DATA_COMMAND_QUEUE]._queue.join()

    mock_client.control_device.assert_any_call("relay-1", 100)


async def test_turn_off_service_calls_client(
    hass: HomeAssistant,
    setup_integration: tuple[MagicMock, MockConfigEntry],
) -> None:
    """Calling switch.turn_off drives the API with level 0."""
    mock_client, _ = setup_integration

    await hass.services.async_call(
        "switch",
        "turn_off",
        {"entity_id": RELAY_ENTITY_ID},
        blocking=True,
    )
    await hass.async_block_till_done()
    await hass.data[DOMAIN][DATA_COMMAND_QUEUE]._queue.join()

    mock_client.control_device.assert_any_call("relay-1", 0)
