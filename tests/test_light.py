"""Tests for the light (dimmer) platform."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from homeassistant.components.light import ColorMode

from custom_components.qwikswitch_api.const import (
    DATA_COMMAND_QUEUE,
    DATA_QS_COORDINATOR,
    DOMAIN,
    MANUFACTURER,
    MODEL_DIMMER,
)
from custom_components.qwikswitch_api.light import QwikSwitchLight, async_setup_entry

from .conftest import DIMMER_TYPE, RELAY_TYPE, make_device_status

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

DIMMER_ENTITY_ID = "light.qwikswitch_dimmer_dimmer_1"


def _make_light(optimistic: int | None = None, *statuses) -> QwikSwitchLight:
    """Build a dimmer entity with an optional optimistic value."""
    coordinator = MagicMock()
    coordinator.data = list(statuses)
    light = QwikSwitchLight(coordinator, MagicMock(), "dimmer-1", "name")
    light._optimistic_value = optimistic
    return light


def test_color_mode_is_brightness() -> None:
    """The dimmer advertises brightness colour mode."""
    light = _make_light()
    assert light.color_mode is ColorMode.BRIGHTNESS
    assert light.supported_color_modes == {ColorMode.BRIGHTNESS}


@pytest.mark.parametrize(
    ("optimistic", "value", "expected"),
    [
        (None, 40, True),
        (None, 0, False),
        (50, None, True),
        (0, None, False),
    ],
)
def test_is_on(optimistic: int | None, value: int | None, expected: bool) -> None:
    """is_on reflects the optimistic value first, else the polled value."""
    statuses = (
        [make_device_status("dimmer-1", value, DIMMER_TYPE)]
        if value is not None
        else []
    )
    light = _make_light(optimistic, *statuses)
    assert light.is_on is expected


def test_is_on_false_without_status() -> None:
    """is_on is False when there is neither optimistic nor polled data."""
    assert _make_light(None).is_on is False


@pytest.mark.parametrize(
    ("optimistic", "value", "expected"),
    [
        (None, 100, 255),
        (None, 40, 102),
        (100, None, 255),
        (0, None, 0),
    ],
)
def test_brightness_conversion(
    optimistic: int | None, value: int | None, expected: int
) -> None:
    """Brightness converts the 0-100 device level to the 0-255 HA scale."""
    statuses = (
        [make_device_status("dimmer-1", value, DIMMER_TYPE)]
        if value is not None
        else []
    )
    light = _make_light(optimistic, *statuses)
    assert light.brightness == expected


def test_brightness_none_without_status() -> None:
    """Brightness is None when the device has no known level."""
    assert _make_light(None).brightness is None


def test_device_info() -> None:
    """Device info identifies the dimmer with the right model and manufacturer."""
    info = _make_light().device_info
    assert info["identifiers"] == {(DOMAIN, "dimmer-1")}
    assert info["manufacturer"] == MANUFACTURER
    assert info["model"] == MODEL_DIMMER


@pytest.mark.parametrize(
    ("kwargs", "expected_level"),
    [
        ({}, 100),
        ({"brightness": 255}, 100),
        ({"brightness": 128}, 50),
        ({"brightness": 0}, 0),
    ],
)
def test_turn_on_levels(kwargs: dict, expected_level: int) -> None:
    """turn_on converts brightness to a 0-100 level (defaulting to full)."""
    light = _make_light()
    light.control_device_optimistic = MagicMock()
    light.turn_on(**kwargs)
    light.control_device_optimistic.assert_called_once_with(expected_level)


def test_turn_off() -> None:
    """turn_off requests level 0."""
    light = _make_light()
    light.control_device_optimistic = MagicMock()
    light.turn_off()
    light.control_device_optimistic.assert_called_once_with(0)


async def test_async_setup_entry_creates_only_dimmers() -> None:
    """Only dimmer-class devices become light entities."""
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
    added: list[QwikSwitchLight] = []

    await async_setup_entry(hass, MagicMock(), added.extend)

    assert len(added) == 1
    assert added[0].unique_id == "qwikswitch_light_dimmer-1"


async def test_async_setup_entry_no_dimmers_adds_nothing() -> None:
    """With no dimmers present, no entities are added."""
    coordinator = MagicMock()
    coordinator.data = [make_device_status("relay-1", 100, RELAY_TYPE)]
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
    """Calling light.turn_on drives the API through the command queue."""
    mock_client, _ = setup_integration

    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": DIMMER_ENTITY_ID, "brightness": 255},
        blocking=True,
    )
    await hass.async_block_till_done()
    await hass.data[DOMAIN][DATA_COMMAND_QUEUE]._queue.join()

    mock_client.control_device.assert_any_call("dimmer-1", 100)


async def test_turn_off_service_calls_client(
    hass: HomeAssistant,
    setup_integration: tuple[MagicMock, MockConfigEntry],
) -> None:
    """Calling light.turn_off drives the API with level 0."""
    mock_client, _ = setup_integration

    await hass.services.async_call(
        "light",
        "turn_off",
        {"entity_id": DIMMER_ENTITY_ID},
        blocking=True,
    )
    await hass.async_block_till_done()
    await hass.data[DOMAIN][DATA_COMMAND_QUEUE]._queue.join()

    mock_client.control_device.assert_any_call("dimmer-1", 0)
