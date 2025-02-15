"""Constants for qwikswitch_api."""

from logging import Logger, getLogger
from typing import Final

LOGGER: Logger = getLogger(__package__)

DOMAIN: Final = "qwikswitch_api"

MANUFACTURER: Final = "QwikSwitch"
MODEL_DIMMER = "Dimmer"
MODEL_RELAY = "Relay"

CONF_MASTER_KEY: Final = "master_key"
CONF_POLL_FREQUENCY: Final = "poll_frequency"
CONF_COMMAND_DELAY: Final = "command_delay"

DEFAULT_POLL_FREQUENCY: int = 5  # seconds
DEFAULT_COMMAND_DELAY: int = 2

DATA_QS_CLIENT: str = "qs_api_client"
DATA_QS_COORDINATOR: str = "qs__api_coordinator"
DATA_COMMAND_QUEUE: str = "qs_command_queue"

CONF_VERSION: int = 2
