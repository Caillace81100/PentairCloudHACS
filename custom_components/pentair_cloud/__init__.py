"""The Pentair integration."""

from __future__ import annotations

import logging
import voluptuous as vol
from pypentair import Pentair, PentairAuthenticationError

from homeassistant.config_entries import ConfigEntry, SOURCE_IMPORT
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_USERNAME, Platform, CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.device_registry import DeviceEntry
from .pentaircloud import PentairCloudHub
from .const import CONF_ID_TOKEN, CONF_REFRESH_TOKEN, DOMAIN

from .coordinator import (
    PentairDataUpdateCoordinator,
    PentairDeviceDataUpdateCoordinator,
)

import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.LIGHT]

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_EMAIL): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


#async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
#    """Set up Pentair from a config entry."""
#    entry.add_update_listener(update_listener)

#    client = Pentair(
#        username=entry.data.get(CONF_USERNAME),
#        access_token=entry.data.get(CONF_ACCESS_TOKEN),
#        id_token=entry.data.get(CONF_ID_TOKEN),
#        refresh_token=entry.data.get(CONF_REFRESH_TOKEN),
#    )

#    try:
#        await hass.async_add_executor_job(client.get_auth)
#    except PentairAuthenticationError as err:
#        raise ConfigEntryAuthFailed(err) from err
#    except Exception as ex:
#        raise ConfigEntryNotReady(ex) from ex

#    coordinator = PentairDataUpdateCoordinator(hass, client=client)
#    hub = PentairCloudHub(_LOGGER)
#    await coordinator.async_config_entry_first_refresh()

#    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

#    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

#    return True

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the PentairCloud component."""
    hass.data.setdefault(DOMAIN, {})
    conf = config.get(DOMAIN)
    if not conf:
        return True

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data={CONF_EMAIL: conf[CONF_EMAIL], CONF_PASSWORD: conf[CONF_PASSWORD]},
        )
    )
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Pentair from a config entry."""

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {} # Initialisez un dictionnaire vide pour stocker les deux configs

    entry.add_update_listener(update_listener)

    # ===================================================
    # 1. Configuration du premier système de hacs-pentair
    # ===================================================

    client = Pentair(
        username=entry.data.get(CONF_USERNAME),
        access_token=entry.data.get(CONF_ACCESS_TOKEN),
        id_token=entry.data.get(CONF_ID_TOKEN),
        refresh_token=entry.data.get(CONF_REFRESH_TOKEN),
    )

    try:
        await hass.async_add_executor_job(client.get_auth)
        _LOGGER.info("Authentification pypentair réussie.")
    except PentairAuthenticationError as err:
        raise ConfigEntryAuthFailed(err) from err
    except Exception as ex:
        raise ConfigEntryNotReady(ex) from ex

    #coordinator = PentairDataUpdateCoordinator(hass, client=client)
    coordinator = PentairDataUpdateCoordinator(
        hass=hass, config_entry=entry, client=client
    )  

    await coordinator.async_config_entry_first_refresh()

    device_coordinators_map: dict[str, PentairDeviceDataUpdateCoordinator] = {}
    
    for device in coordinator.get_devices():
        device_coordinator = PentairDeviceDataUpdateCoordinator(
            hass=hass, config_entry=entry, client=client, device_id=device["deviceId"]
        )
        await device_coordinator.async_config_entry_first_refresh()
        coordinator.device_coordinators.append(device_coordinator)
        device_coordinators_map[device["deviceId"]] = device_coordinator

    hass.data[DOMAIN][entry.entry_id]["pypentair_coordinator"] = coordinator
    hass.data[DOMAIN][entry.entry_id]["device_coordinators_map"] = device_coordinators_map
    hass.data[DOMAIN][entry.entry_id]["pypentair_api_client"] = client # Stockez le client API si besoin direct
    

    # =================================================
    # 2. Configuration du deuxième système PentairCloud 
    # =================================================
    username_cloud = entry.data.get(CONF_USERNAME) 
    password_cloud = entry.data.get(CONF_PASSWORD) 

    try:
        hub = PentairCloudHub(_LOGGER)
        if not await hass.async_add_executor_job(
            #hub.authenticate, entry.data["username"], entry.data["password"]
            hub.authenticate, username_cloud, password_cloud
        ):
            return False

        await hass.async_add_executor_job(hub.populate_AWS_and_data_fields)
    except Exception as err:
        _LOGGER.error("Exception while setting up Pentair Cloud. Will retry. %s", err)
        raise ConfigEntryNotReady(
            f"Exception while setting up Pentair Cloud. Will retry. {err}"
        )

    hass.data[DOMAIN][entry.entry_id]["pentair_cloud_hub"] = hub

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of an entry."""
    hass.data[DOMAIN].pop(entry.entry_id)

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Remove a config entry from a device."""
    coordinator: PentairDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]["pypentair_coordinator"] 
    return not any(                        
        identifier
        for identifier in device_entry.identifiers
        if identifier[0] == DOMAIN
        for device in coordinator.get_devices()
        if identifier[1] == device["deviceId"]
    )




