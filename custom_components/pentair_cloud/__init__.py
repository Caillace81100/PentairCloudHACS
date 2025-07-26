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
from .entity import PentairDataUpdateCoordinator

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

    coordinator = PentairDataUpdateCoordinator(hass, client=client)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id]["pypentair_coordinator"] = coordinator
    hass.data[DOMAIN][entry.entry_id]["pypentair_api_client"] = client # Stockez le client API si besoin direct

    # =================================================
    # 2. Configuration du deuxième système PentairCloud 
    # =================================================

    try:
        hub = PentairCloudHub(_LOGGER)
        if not await hass.async_add_executor_job(
            hub.authenticate, entry.data["username"], entry.data["password"]
        ):
            return False

        await hass.async_add_executor_job(hub.populate_AWS_and_data_fields)
    except Exception as err:
        _LOGGER.error("Exception while setting up Pentair Cloud. Will retry. %s", err)
        raise ConfigEntryNotReady(
            f"Exception while setting up Pentair Cloud. Will retry. {err}"
        )

    #hass.data[DOMAIN][entry.entry_id] = {"pentair_cloud_hub": hub}
    hass.data[DOMAIN][entry.entry_id]["pentair_cloud_hub"] = hub

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True



#async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
#    """Configure Pentair Cloud à partir d'une entrée de configuration."""
#    _LOGGER.debug("Démarrage de la configuration de l'intégration Pentair Cloud pour l'entrée : %s", entry.entry_id)

#    # 1. Initialiser votre PentairCloudHub
#    # Passez _LOGGER au constructeur du hub comme vu dans son __init__
#    pentair_hub = PentairCloudHub(_LOGGER)

#    # Extraire les identifiants de l'entrée de configuration
#    #username = entry.data.get(CONF_USERNAME)
#    #password = entry.data.get(CONF_PASSWORD)
#    username = entry.data["username"]
#    password = entry.data["password"]
    

#    # Valider que le nom d'utilisateur et le mot de passe sont fournis
#    if not username or not password:
#        _LOGGER.error("Nom d'utilisateur ou mot de passe introuvable dans les données de l'entrée de configuration.")
#        raise ConfigEntryAuthFailed("Nom d'utilisateur ou mot de passe manquant.")

#    try:
#        # 2. Authentifier en utilisant PentairCloudHub
#        _LOGGER.debug("Tentative d'authentification avec Pentair Cloud en utilisant le nom d'utilisateur : %s", username)
#        if not await hass.async_add_executor_job(
#            pentair_hub.authenticate, username, password
#        ):
#            # Si authenticate renvoie False (selon votre PentairCloudHub.authenticate)
#            _LOGGER.error("L'authentification Pentair Cloud a échoué pour l'utilisateur : %s", username)
#            raise ConfigEntryAuthFailed("Nom d'utilisateur ou mot de passe invalide pour Pentair Cloud.")

#        # 3. Remplir les données AWS et des appareils
#        # Ceci est crucial pour que le hub collecte les informations initiales des appareils
#        _LOGGER.debug("Remplissage des données AWS et des appareils pour Pentair Cloud.")
#        await hass.async_add_executor_job(pentair_hub.populate_AWS_and_data_fields)
#        _LOGGER.info("Authentification et remplissage des données réussis pour Pentair Cloud.")

#    except PentairAuthenticationError as err:
#        # Attraper les erreurs d'authentification spécifiques de pypentair si elles remontent
#        _LOGGER.error("Erreur d'authentification API Pentair : %s", err)
#        raise ConfigEntryAuthFailed(err) from err
#    except Exception as ex:
#        # Attraper toute autre erreur inattendue pendant la configuration
#        _LOGGER.error("Erreur inattendue pendant la configuration de Pentair Cloud : %s", ex, exc_info=True)
#        raise ConfigEntryNotReady(f"Échec de la configuration de Pentair Cloud : {ex}") from ex

#    # 4. Initialiser le DataUpdateCoordinator avec le PentairCloudHub authentifié
#    # Le coordinateur utilisera cette instance 'pentair_hub' pour récupérer les mises à jour
#    _LOGGER.debug("Initialisation de PentairDataUpdateCoordinator.")
#    coordinator = PentairDataUpdateCoordinator(hass, client=pentair_hub)
#    await coordinator.async_config_entry_first_refresh() # Forcer un premier rafraîchissement des données

#    # 5. Stocker le coordinateur dans hass.data
#    # Nous stockons le coordinateur directement, car il contient le hub et les données
#    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

#    # 6. Transférer la configuration aux plateformes (sensor, light, etc.)
#    _LOGGER.debug("Transfert de la configuration aux plateformes : %s", PLATFORMS)
#    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

#    # 7. Ajouter un écouteur de mise à jour pour les changements d'entrée de configuration
#    entry.add_update_listener(update_listener)

#    _LOGGER.info("Configuration de l'intégration Pentair Cloud terminée avec succès pour l'entrée : %s", entry.entry_id)
#    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Décharger une entrée de configuration."""
    _LOGGER.debug("Déchargement de l'intégration Pentair Cloud pour l'entrée : %s", entry.entry_id)
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.info("L'intégration Pentair Cloud a été déchargée avec succès pour l'entrée : %s", entry.entry_id)
    return unload_ok

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Gérer la mise à jour des options."""
    _LOGGER.debug("Options de l'entrée de configuration mises à jour pour l'entrée : %s. Rechargement.", entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)


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
    coordinator: PentairDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    return not any(
        identifier
        for identifier in device_entry.identifiers
        if identifier[0] == DOMAIN
        for device in coordinator.get_devices()
        if identifier[1] == device["deviceId"]
    )




