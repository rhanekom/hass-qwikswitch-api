"""Tests for the priority command queue."""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from qwikswitchapi.entities import DeviceStatuses
from qwikswitchapi.exceptions import QSError

from custom_components.qwikswitch_api.command_queue import (
    KEY_FUT,
    KEY_LEVEL,
    PRIORITY_POLL,
    Command,
    CommandType,
    QwikSwitchCommandQueue,
)

from .conftest import RELAY_TYPE, make_device_status

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from homeassistant.core import HomeAssistant


@pytest.fixture
def qs_client() -> MagicMock:
    """Return a mock QSClient whose poll yields a single relay."""
    client = MagicMock()
    client.get_all_device_status.return_value = DeviceStatuses(
        [make_device_status("relay-1", 100, RELAY_TYPE)]
    )
    return client


@pytest.fixture
async def queue(
    hass: HomeAssistant, qs_client: MagicMock
) -> AsyncGenerator[QwikSwitchCommandQueue]:
    """
    Build a command queue with zero delay (no sleeping between commands).

    On teardown the background processing task is stopped and awaited so it
    does not linger past the test.
    """
    command_queue = QwikSwitchCommandQueue(qs_client, hass, command_delay=0)
    yield command_queue

    task = command_queue._processing_task
    command_queue.stop()
    if task is not None:
        with contextlib.suppress(asyncio.CancelledError):
            await task


def test_start_is_idempotent(queue: QwikSwitchCommandQueue) -> None:
    """Calling start twice reuses the same processing task."""
    queue.start()
    task = queue._processing_task
    assert task is not None

    queue.start()
    assert queue._processing_task is task


def test_stop_without_start_is_safe(queue: QwikSwitchCommandQueue) -> None:
    """Stopping a queue that never started does nothing."""
    queue.stop()
    assert queue._processing_task is None


async def test_enqueue_set_device_debounces(
    queue: QwikSwitchCommandQueue,
) -> None:
    """A second command for the same device updates the pending one in place."""
    await queue.enqueue_set_device("relay-1", 50)
    await queue.enqueue_set_device("relay-1", 80)

    # Only one queued item; the pending command reflects the latest level.
    assert queue._queue.qsize() == 1
    pending = queue._pending_commands[(CommandType.SET_DEVICE, "relay-1")]
    assert pending.data[KEY_LEVEL] == 80


async def test_set_device_calls_client(
    queue: QwikSwitchCommandQueue,
    qs_client: MagicMock,
) -> None:
    """A processed set-device command calls the client and clears pending state."""
    queue.start()
    await queue.enqueue_set_device("relay-1", 42)
    await queue._queue.join()

    qs_client.control_device.assert_called_once_with("relay-1", 42)
    assert (CommandType.SET_DEVICE, "relay-1") not in queue._pending_commands


async def test_set_device_error_is_swallowed(
    queue: QwikSwitchCommandQueue,
    qs_client: MagicMock,
) -> None:
    """An error controlling a device is logged, not raised, and the loop survives."""
    qs_client.control_device.side_effect = QSError("boom")
    queue.start()

    await queue.enqueue_set_device("relay-1", 42)
    await queue._queue.join()

    qs_client.control_device.assert_called_once()
    # The processing task keeps running after a command error.
    assert not queue._processing_task.done()


async def test_enqueue_poll_returns_statuses(
    queue: QwikSwitchCommandQueue,
) -> None:
    """A poll returns the list of device statuses from the client."""
    queue.start()
    statuses = await queue.enqueue_poll()

    assert len(statuses) == 1
    assert statuses[0].device_id == "relay-1"


async def test_enqueue_poll_propagates_error(
    queue: QwikSwitchCommandQueue,
    qs_client: MagicMock,
) -> None:
    """A failing poll raises the error to the awaiting caller."""
    qs_client.get_all_device_status.side_effect = QSError("api down")
    queue.start()

    with pytest.raises(QSError):
        await queue.enqueue_poll()


async def test_duplicate_poll_reuses_pending_future(
    hass: HomeAssistant,
    queue: QwikSwitchCommandQueue,
) -> None:
    """A poll enqueued while one is pending reuses the existing future."""
    fut = hass.loop.create_future()
    key = (CommandType.POLL, None)
    queue._pending_commands[key] = Command(
        cmd_type=CommandType.POLL,
        device_id=None,
        data={KEY_FUT: fut},
        priority=PRIORITY_POLL,
    )

    hass.loop.call_soon(fut.set_result, ["sentinel"])
    result = await queue.enqueue_poll()

    assert result == ["sentinel"]
    # No new command was queued — the pending one was reused.
    assert queue._queue.qsize() == 0


async def test_duplicate_poll_recreates_missing_future(
    queue: QwikSwitchCommandQueue,
) -> None:
    """A pending poll with no stored future gets a fresh one created for it."""
    key = (CommandType.POLL, None)
    pending = Command(
        cmd_type=CommandType.POLL,
        device_id=None,
        data={},
        priority=PRIORITY_POLL,
    )
    queue._pending_commands[key] = pending

    task = asyncio.ensure_future(queue.enqueue_poll())
    await asyncio.sleep(0)  # let enqueue_poll create and store the future

    created = pending.data[KEY_FUT]
    created.set_result(["late"])
    assert await task == ["late"]


async def test_handle_set_device_with_none_id_does_not_call_client(
    queue: QwikSwitchCommandQueue,
    qs_client: MagicMock,
) -> None:
    """A set-device command with no device id is a no-op against the client."""
    await queue._handle_set_device(
        Command(cmd_type=CommandType.SET_DEVICE, device_id=None, data={}, priority=0)
    )

    qs_client.control_device.assert_not_called()
