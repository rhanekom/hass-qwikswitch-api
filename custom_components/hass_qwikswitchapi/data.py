"""Custom types for qwikswitch_api."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration
    from qwikswitchapi.qsapi import QSApi

    from .coordinator import QSDataUpdateCoordinator


type QSConfigEntry = ConfigEntry[QSData]


@dataclass
class QSData:
    """Data for the QwikSwitch integration."""

    client: QSApi
    coordinator: QSDataUpdateCoordinator
    integration: Integration
