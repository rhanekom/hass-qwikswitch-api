"""Command Queue for queueing commands made to the Qwikswitch API."""

from __future__ import annotations

import asyncio
import logging
from enum import Enum
from typing import TYPE_CHECKING, Final

from attr import dataclass

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from qwikswitchapi.client import QSClient

_LOGGER = logging.getLogger(__name__)


class CommandType(Enum):
    """The type of command, used for prioritisation."""

    SET_DEVICE = "set_device"
    POLL = "poll"


@dataclass
class Command:
    """A command to be executed by the QwikSwitchCommandQueue."""

    cmd_type: CommandType
    device_id: str | None = None
    data: dict = {}  # e.g. {"level": 42}, or {"done_fut": <Future>}  # noqa: RUF012
    priority: int = 1


PRIORITY_COMMAND = 0  # device commands
PRIORITY_POLL = 1  # poll commands

KEY_FUT: Final = "done_fut"
KEY_LEVEL: Final = "level"


class QwikSwitchCommandQueue:
    """
    A central queue for API commands.

    A central queue that enforces:
      - Priority (device commands first, poll second).
      - A user-configurable delay (command_delay) between calls to avoid rate-limits.
      - Debouncing repeated commands.
      - No retries: if a call fails, it just logs an error.
    """

    def __init__(
        self, qs_client: QSClient, hass: HomeAssistant, command_delay: int = 2
    ) -> None:
        """
        Initialise the queue.

        :param qs_client: The Qwikswitch QSClient instance
        :param hass: HomeAssistant instance
        :param command_delay: The delay (in seconds) between commands (default=2)
        """
        self._qs_client = qs_client
        self._hass = hass
        self._command_delay = command_delay

        # Priority queue storing (priority, cmd_type, device_id, optional data/future)
        self._queue: asyncio.PriorityQueue[tuple[int, Command]] = (
            asyncio.PriorityQueue()
        )

        # Store pending commands in a dict so we can update or discard duplicates
        # Key: (cmd_type, device_id), Value: the Command
        self._pending_commands: dict[tuple[CommandType, str | None], Command] = {}

        self._processing_task: asyncio.Task | None = None

    def start(self) -> None:
        """Start the background task that processes items in this queue."""
        if not self._processing_task:
            self._processing_task = self._hass.loop.create_task(self._process_loop())

    def stop(self) -> None:
        """Stop the background queue processing."""
        if self._processing_task:
            self._processing_task.cancel()
            self._processing_task = None

    async def enqueue_set_device(self, device_id: str, level: int) -> None:
        """
        Enqueue or update a device command for (SET_DEVICE, device_id).

        Debounce by overwriting any pending command for that device.
        """
        cmd_key = (CommandType.SET_DEVICE, device_id)
        existing_cmd = self._pending_commands.get(cmd_key)
        if existing_cmd:
            # Debounce: just update the level in the existing command
            existing_cmd.data[KEY_LEVEL] = level

            _LOGGER.debug(
                "Debounce: updated SET_DEVICE for device=%s to level=%s",
                device_id,
                level,
            )
        else:
            # Create a new Command
            cmd = Command(
                cmd_type=CommandType.SET_DEVICE,
                device_id=device_id,
                data={KEY_LEVEL: level},
                priority=PRIORITY_COMMAND,
            )
            self._pending_commands[cmd_key] = cmd
            await self._queue.put((PRIORITY_COMMAND, cmd))

    async def enqueue_poll(self) -> list:
        """
        Enqueue or update a poll command.

        Debounce so multiple poll calls unify into one.
        Return the same future if we have one pending.
        """
        cmd_key = (CommandType.POLL, None)
        existing_cmd = self._pending_commands.get(cmd_key)
        if existing_cmd:
            # Already pending poll; reuse its future
            done_fut = existing_cmd.data.get(KEY_FUT)
            if done_fut is None:
                # Shouldn't happen if we always store a future
                done_fut = self._hass.loop.create_future()
                existing_cmd.data[KEY_FUT] = done_fut
            return await done_fut

        # Create a new poll command with a future
        done_fut = self._hass.loop.create_future()
        cmd = Command(
            cmd_type=CommandType.POLL,
            device_id=None,
            data={KEY_FUT: done_fut},
            priority=PRIORITY_POLL,
        )
        self._pending_commands[cmd_key] = cmd
        await self._queue.put((PRIORITY_POLL, cmd))
        return await done_fut

    async def _process_loop(self) -> None:
        """
        Process commands in priority order in this main loop.

        After each command, wait self._command_delay seconds.
        Debounced commands are updated in _pending_commands until removed here.
        """
        while True:
            _, cmd = await self._queue.get()
            cmd_key = (cmd.cmd_type, cmd.device_id)

            try:
                await self._handle_command(cmd)
                # Wait after each command to avoid rate-limit
                await asyncio.sleep(self._command_delay)

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                _LOGGER.exception(
                    "Error processing %s cmd (device=%s): %s",
                    cmd.cmd_type,
                    cmd.device_id,
                    exc,  # noqa: TRY401
                )
                # If it's a poll, set an exception so the caller sees a failure
                if cmd.cmd_type == CommandType.POLL:
                    done_fut = cmd.data.get(KEY_FUT)
                    if done_fut and not done_fut.done():
                        done_fut.set_exception(exc)

            finally:
                # Always remove this command from _pending_commands if it's still there
                pending_cmd = self._pending_commands.get(cmd_key)
                if pending_cmd is cmd:
                    del self._pending_commands[cmd_key]

                self._queue.task_done()

    async def _handle_command(self, cmd: Command) -> None:
        """Decide which specialized handler to call based on cmd_type."""
        if cmd.cmd_type == CommandType.SET_DEVICE and cmd.device_id is not None:
            await self._handle_set_device(cmd)
        elif cmd.cmd_type == CommandType.POLL:
            await self._handle_poll(cmd)
        # else: possibly handle more CommandTypes

    async def _handle_set_device(self, cmd: Command) -> None:
        """Handle a set-device command."""
        device_id = cmd.device_id
        level = cmd.data.get(KEY_LEVEL, 0)

        if device_id is not None:
            # Run in an executor to avoid blocking
            await self._hass.async_add_executor_job(
                self._qs_client.control_device, device_id, level
            )
        else:
            _LOGGER.error("Device ID is None for SET_DEVICE command")

    async def _handle_poll(self, cmd: Command) -> None:
        """Handle a poll command, returning data to done_fut if provided."""
        done_fut = cmd.data.get(KEY_FUT)
        statuses = await self._hass.async_add_executor_job(
            self._qs_client.get_all_device_status
        )
        if done_fut and not done_fut.done():
            done_fut.set_result(statuses.statuses)
