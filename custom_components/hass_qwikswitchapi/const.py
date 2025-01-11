"""Constants for qwikswitch_api."""

from logging import Logger, getLogger
from typing import Final

LOGGER: Logger = getLogger(__package__)

DOMAIN: Final = "qwikswitch_api"
CONF_MASTER_KEY: Final = "master_key"
