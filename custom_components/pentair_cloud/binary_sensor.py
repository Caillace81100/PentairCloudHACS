"""Support for Pentair binary sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import logging

from .const import DOMAIN
from .coordinator import PentairDataUpdateCoordinator, PentairDeviceDataUpdateCoordinator
from .entity import PentairEntity
from .helpers import get_field_value

_LOGGER = logging.getLogger(__name__) # Initialisez le logger ici

@dataclass
class RequiredKeysMixin:
    """Required keys mixin."""

    is_on: Callable[[dict], bool]


@dataclass
class PentairBinarySensorEntityDescription(
    BinarySensorEntityDescription, RequiredKeysMixin
):
    """Pentair binary sensor entity description."""


SENSOR_MAP: dict[str | None, tuple[PentairBinarySensorEntityDescription, ...]] = {
    "IF31": (
        PentairBinarySensorEntityDescription(
            key="pump_enabled",
            translation_key="pump_enabled",
            is_on=lambda data: get_field_value("s25", data),
        ),
    ),
    "PPA0": (
        PentairBinarySensorEntityDescription(
            key="low_battery",
            device_class=BinarySensorDeviceClass.BATTERY,
            entity_category=EntityCategory.DIAGNOSTIC,
            translation_key="low_battery",
            is_on=lambda data: int(data["fields"]["bvl"]) < 3
            or data["fields"]["bft"] == "4",
        ),
        PentairBinarySensorEntityDescription(
            key="battery_charging",
            device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
            entity_category=EntityCategory.DIAGNOSTIC,
            is_on=lambda data: data["fields"]["bch"] != "2",
        ),
        PentairBinarySensorEntityDescription(
            key="online",
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
            entity_category=EntityCategory.DIAGNOSTIC,
            translation_key="online",
            is_on=lambda data: data["fields"]["online"],
        ),
        PentairBinarySensorEntityDescription(
            key="power",
            device_class=BinarySensorDeviceClass.POWER,
            entity_category=EntityCategory.DIAGNOSTIC,
            translation_key="power",
            is_on=lambda data: data["fields"]["acp"] == "1",
        ),
        PentairBinarySensorEntityDescription(
            key="primary_pump",
            device_class=BinarySensorDeviceClass.PROBLEM,
            translation_key="primary_pump",
            is_on=lambda data: data["fields"]["sts"] == "2",
        ),
        PentairBinarySensorEntityDescription(
            key="secondary_pump",
            device_class=BinarySensorDeviceClass.PROBLEM,
            translation_key="secondary_pump",
            is_on=lambda data: int(data["fields"]["sts"]) > 0,
        ),
        PentairBinarySensorEntityDescription(
            key="water_level",
            device_class=BinarySensorDeviceClass.PROBLEM,
            translation_key="water_level",
            is_on=lambda data: data["fields"]["sts"] == 5,
        ),
    ),
}


#async def async_setup_entry(
#    hass: HomeAssistant,
#    config_entry: ConfigEntry,
#    async_add_entities: AddEntitiesCallback,
#) -> None:
#    """Set up Pentair binary sensors using config entry."""
#    coordinator: PentairDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]["pypentair_coordinator"]  

#    entities = [
#        PentairBinarySensorEntity(
#            coordinator=coordinator.device_coordinators,
#            config_entry=config_entry,
#            description=description,
#            device_id=device["deviceId"],
#        )
#        for device in coordinator.get_devices()
#        for device_type, descriptions in SENSOR_MAP.items()
#        for description in descriptions
#        if device_type is None or device["deviceType"] == device_type
#    ]

#    if not entities:
#        return

#    async_add_entities(entities)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Pentair binary sensors using config entry."""

    coordinator: PentairDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]["pypentair_coordinator"]  
    device_coordinators_map: dict[str, PentairDeviceDataUpdateCoordinator] = hass.data[DOMAIN][config_entry.entry_id]["device_coordinators_map"] 
    entities = []

    for device_data in coordinator.get_devices(): 
        device_id = device_data.get("deviceId")
        device_type = device_data.get("deviceType")

        if not device_id:
            _LOGGER.warning("Appareil sans 'deviceId' trouvé, ignoré: %s", device_data)
            continue

        coordinator_for_this_device = device_coordinators_map.get(device_id)

        if not coordinator_for_this_device:
            _LOGGER.warning(
                "Coordinateur d'appareil non trouvé dans la map pour device_id: %s. "
                "Impossible de créer des entités pour cet appareil.", 
                device_id
            )
            continue 

       # 6. Parcourir la SENSOR_MAP en fonction du type d'appareil
        for map_device_type, descriptions in SENSOR_MAP.items():
            if map_device_type is None or device_type == map_device_type:
                for description in descriptions:
                    entities.append(
                        PentairBinarySensorEntity(
                            # C'est la LIGNE CRUCIALE : on passe le coordinateur spécifique à l'appareil
                            coordinator=coordinator_for_this_device, 
                            config_entry=config_entry,
                            description=description,
                            device_id=device_id,
                        )
                    )
    if not entities:
        _LOGGER.debug("Aucune entité de capteur binaire Pentair trouvée pour cette configuration.")
        return

    async_add_entities(entities)
    _LOGGER.debug("Ajouté %d entités de capteur binaire Pentair.", len(entities))


class PentairBinarySensorEntity(PentairEntity, BinarySensorEntity):
    """Pentair binary sensor entity."""

    entity_description: PentairBinarySensorEntityDescription

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self.entity_description.is_on(self.get_device())
