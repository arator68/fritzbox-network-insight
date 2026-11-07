"""Safely migrate legacy status entity IDs to MAC-based IDs."""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def migrate_legacy_status_entity_id(
    hass: HomeAssistant,
    *,
    config_entry_id: str,
    unique_id: str,
    device_name: str,
    target_entity_id: str,
) -> None:
    """Rename only unchanged legacy IDs owned by this integration.

    Do not touch user-renamed entities or occupied target IDs.
    """
    registry = er.async_get(hass)
    current_entity_id = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
    if current_entity_id is None or current_entity_id == target_entity_id:
        return

    entry = registry.async_get(current_entity_id)
    if entry is None or entry.config_entry_id != config_entry_id:
        return

    # A user-provided entity name is a customization, not a migration target.
    if entry.name is not None:
        return

    old_base = f"sensor.{slugify(device_name)}_status"
    if current_entity_id not in (old_base, f"{old_base}_2"):
        return

    if registry.async_get(target_entity_id) is not None:
        _LOGGER.warning(
            "Skipping status entity ID migration for %s: target %s is registered",
            current_entity_id,
            target_entity_id,
        )
        return

    if hass.states.get(target_entity_id) is not None:
        _LOGGER.warning(
            "Skipping status entity ID migration for %s: target %s has a state",
            current_entity_id,
            target_entity_id,
        )
        return

    try:
        registry.async_update_entity(
            current_entity_id, new_entity_id=target_entity_id
        )
    except ValueError:
        _LOGGER.exception(
            "Could not migrate status entity ID %s to %s",
            current_entity_id,
            target_entity_id,
        )
        return

    _LOGGER.info(
        "Migrated FRITZ!Box Network Insight status entity ID: %s -> %s",
        current_entity_id,
        target_entity_id,
    )
