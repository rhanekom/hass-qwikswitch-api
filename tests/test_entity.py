"""Unit tests for the shared base entity (optimistic update logic)."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.qwikswitch_api.light import QwikSwitchLight

from .conftest import DIMMER_TYPE, make_device_status


def _make_entity(*statuses) -> QwikSwitchLight:
    """Build a light entity backed by a mock coordinator holding `statuses`."""
    coordinator = MagicMock()
    coordinator.data = list(statuses)
    command_queue = MagicMock()
    return QwikSwitchLight(
        coordinator=coordinator,
        command_queue=command_queue,
        device_id="dimmer-1",
        name="QwikSwitch Dimmer dimmer-1",
    )


def test_unique_id_uses_suffix() -> None:
    """The unique id combines the entity suffix and the device id."""
    entity = _make_entity()
    assert entity.unique_id == "qwikswitch_light_dimmer-1"


def test_find_status_matches_device() -> None:
    """_find_status returns the status matching this entity's device id."""
    status = make_device_status("dimmer-1", 40, DIMMER_TYPE)
    entity = _make_entity(status, make_device_status("other", 10, DIMMER_TYPE))
    assert entity._find_status() is status


def test_find_status_returns_none_when_absent() -> None:
    """_find_status returns None when the device is not in coordinator data."""
    entity = _make_entity(make_device_status("other", 10, DIMMER_TYPE))
    assert entity._find_status() is None


def test_find_status_returns_none_when_no_data() -> None:
    """_find_status returns None when the coordinator has no data yet."""
    coordinator = MagicMock()
    coordinator.data = None
    entity = QwikSwitchLight(coordinator, MagicMock(), "dimmer-1", "name")
    assert entity._find_status() is None


def test_control_device_optimistic_enqueues_and_updates() -> None:
    """Sending a level enqueues the command and stores the optimistic value."""
    entity = _make_entity()
    entity.hass = MagicMock()
    entity.schedule_update_ha_state = MagicMock()

    entity.control_device_optimistic(75)

    assert entity._optimistic_value == 75
    entity._command_queue.enqueue_set_device.assert_called_once_with("dimmer-1", 75)
    entity.hass.create_task.assert_called_once()
    entity.schedule_update_ha_state.assert_called_once()


def test_coordinator_update_discards_stale_optimistic() -> None:
    """A polled value disagreeing with the optimistic value clears it."""
    entity = _make_entity(make_device_status("dimmer-1", 40, DIMMER_TYPE))
    entity.async_write_ha_state = MagicMock()
    entity._optimistic_value = 100

    entity._handle_coordinator_update()

    assert entity._optimistic_value is None
    entity.async_write_ha_state.assert_called_once()


def test_coordinator_update_keeps_matching_optimistic() -> None:
    """A polled value equal to the optimistic value keeps the assumption."""
    entity = _make_entity(make_device_status("dimmer-1", 40, DIMMER_TYPE))
    entity.async_write_ha_state = MagicMock()
    entity._optimistic_value = 40

    entity._handle_coordinator_update()

    assert entity._optimistic_value == 40


def test_coordinator_update_keeps_optimistic_when_status_missing() -> None:
    """With no matching status, the optimistic value is retained."""
    entity = _make_entity(make_device_status("other", 10, DIMMER_TYPE))
    entity.async_write_ha_state = MagicMock()
    entity._optimistic_value = 100

    entity._handle_coordinator_update()

    assert entity._optimistic_value == 100
