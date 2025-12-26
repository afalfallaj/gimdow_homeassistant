"""Diagnostics support for Gimdow."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_ACCESS_ID, CONF_ACCESS_SECRET
from .coordinator import GimdowCoordinator

TO_REDACT = {CONF_ACCESS_ID, CONF_ACCESS_SECRET, "access_token", "refresh_token"}

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: GimdowCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Gather data
    diagnostics_data = {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "coordinator_data": coordinator.data,
        "device_id": coordinator.device_id,
        "last_log_timestamp": coordinator._last_log_timestamp,
    }

    return diagnostics_data
