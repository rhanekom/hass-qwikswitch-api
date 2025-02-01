"""Constants for qwikswitch_api."""

from logging import Logger, getLogger
from typing import Final

LOGGER: Logger = getLogger(__package__)

DOMAIN: Final = "qwikswitch_api"

CONF_MASTER_KEY: Final = "master_key"
CONF_POLL_FREQUENCY = "poll_frequency"
DEFAULT_POLL_FREQUENCY: int = 5  # seconds

DATA_QS_CLIENT: str = "qs_api_client"
DATA_QS_COORDINATOR: str = "qs__api_coordinator"
