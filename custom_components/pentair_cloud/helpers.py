"""Helpers."""

from __future__ import annotations

from datetime import datetime
import logging
from time import time
from typing import Any

#from pypentair.utils import get_api_field_name_and_value  #  BPH Mise en commentaire, et récupération du code qui nous interessedans le fichier pypentair directement afin de modifier le traitement qui pose pb.
from typing import Any, Final, TypeVar, cast, overload
from collections.abc import Callable, Mapping


from homeassistant.util.dt import UTC

_LOGGER = logging.getLogger(__name__)


def convert_timestamp(_ts: float) -> datetime:
    """Convert a timestamp to a datetime."""
    return datetime.fromtimestamp(_ts / (1000 if _ts > time() else 1), UTC)


#def get_field_value(key: str, data: dict) -> Any:
#    """Get field value."""
#    name, value = get_api_field_name_and_value(key, data["fields"].get(key))
#    if key not in data["fields"]:
#        _LOGGER.warning('%s key "%s" is missing in fields data', name, key)
#    return value.get("value", value)


# Fonctionne, mais toujours des erreurs dans les logs.
#def get_field_value(key: str, data: dict) -> Any:
#    field_data = data["fields"].get(key)

#    if field_data is None:
#      _LOGGER.debug('La clé "%s" est manquante dans les données des champs pour l\'appareil "%s". Retourne None.',
#                      key, data.get("name", "appareil_inconnu"))
#      return None
    
#    name, value = get_api_field_name_and_value(key, field_data)

#    # Tout d'abord, essayez d'extraire la clé 'value' si le résultat est un dictionnaire.
#    # Cela gère les cas comme {'name': ..., 'value': '...', ...}
#    if isinstance(value, dict) and "value" in value:
#        raw_sensor_value = value["value"]
#    else:
#        # Si ce n'est pas un dictionnaire, ou si la clé 'value' n'y est pas, supposez que extracted_value est la valeur brute.
#        raw_sensor_value = value

#   # 3. Traiter les différents types de 'value'
#    if isinstance(value, dict):
#        # C'est le cas où 'value' est un dictionnaire comme {'name': ..., 'value': '...', ...}
#        # On extrait la sous-clé 'value'
#        raw_sensor_value = value.get("value")

#        if raw_sensor_value is None:
#            _LOGGER.debug(f"No 'value' key found in field data for '{name}' (key: '{key}'): {value}")
#            return None # Ou une valeur par défaut si pertinent

#        # Tenter la conversion si c'est une chaîne qui ressemble à un nombre
#        if isinstance(raw_sensor_value, str):
#            # Vérifier si la chaîne peut être un nombre entier ou flottant
#            if raw_sensor_value.replace('.', '', 1).lstrip('-').isdigit(): # Gère les négatifs et les décimaux
#                try:
#                    # Tente d'abord de le convertir en entier si possible, sinon en flottant
#                    if '.' not in raw_sensor_value: # Si pas de point décimal, tente int
#                        return int(raw_sensor_value)
#                    return float(raw_sensor_value)
#                except ValueError:
#                    _LOGGER.error(f"Failed to convert numerical string '{raw_sensor_value}' for '{name}' (key: '{key}').")
#                    return None
#            else:
#                # La chaîne n'est pas numérique (ex: "NA", "ON", "OFF")
#                _LOGGER.debug(f"Value for '{name}' (key: '{key}') is non-numeric string: '{raw_sensor_value}'. Returning as string.")
#                return raw_sensor_value # Retourne la chaîne telle quelle si elle n'est pas un nombre
#        elif isinstance(raw_sensor_value, (int, float, bool)):
#            # Si la valeur est déjà un int, float ou bool, la retourner directement
#            return raw_sensor_value
#        else:
#            _LOGGER.debug(f"Unexpected type for raw_sensor_value for '{name}' (key: '{key}'): {type(raw_sensor_value)}. Data: {value}")
#            return None # Ou retourner la valeur telle quelle si c'est gérable

#    elif isinstance(value, (bool, int, float, str)):
#        # C'est le cas où 'value' est déjà un type simple (booléen, int, float, string)
#        # par exemple, pour 'pump_enabled_status', 'value' pourrait être True/False directement.
#        _LOGGER.debug(f"Direct value found for '{name}' (key: '{key}'): {value} ({type(value)})")
#        return value
#    else:
#        # Cas inattendu
#        _LOGGER.warning(f"Unexpected data type for field '{name}' (key: '{key}'): {type(value)}. Data: {value}")
#        return None
def _divide_by_10(value: str | int | float) -> float:
    """Divide a value by 10."""
    return float(value) / 10    

def get_field_value(key: str, data: dict) -> Any:
  """Obtient la valeur d'un champ à partir des données Pentair, en gérant les structures imbriquées et les conversions."""
  field_data = data["fields"].get(key)

  if field_data is None:
    _LOGGER.debug('La clé "%s" est manquante dans les données des champs pour l\'appareil "%s". Retourne None.',
                key, data.get("name", "appareil_inconnu"))
    return None

  # Cet appel est au cœur du problème : que renvoie exactement get_api_field_name_and_value pour 'value' ?
  # D'après l'erreur, 'value' peut être le dictionnaire lui-même.
  name, extracted_value = get_api_field_name_and_value(key, field_data)

  # Tout d'abord, essayez d'extraire la clé 'value' si le résultat est un dictionnaire.
  # Cela gère les cas comme {'name': ..., 'value': '...', ...}
  if isinstance(extracted_value, dict) and "value" in extracted_value:
      raw_sensor_value = extracted_value["value"]
  else:
      # Si ce n'est pas un dictionnaire, ou si la clé 'value' n'y est pas, supposez que extracted_value est la valeur brute.
      raw_sensor_value = extracted_value

  # Maintenant, traitez la valeur brute du capteur.
  # Nous convertissons explicitement les chaînes qui ressemblent à des nombres.
  if isinstance(raw_sensor_value, str):
      # Essayez de convertir en nombre si possible
      try:
          # Vérifiez d'abord pour un flottant, car int() échouerait sur "123.0"
          if '.' in raw_sensor_value:
              return float(raw_sensor_value)
          return int(raw_sensor_value)
      except ValueError:
          # Si la conversion échoue, ce n'est pas une simple chaîne numérique (ex: "NA", "ON", "OFF")
          _LOGGER.debug(
              "La valeur pour '%s' (clé : '%s') est une chaîne non numérique : '%s'. Retourne en tant que chaîne.",
              name, key, raw_sensor_value
          )
          return raw_sensor_value
  elif isinstance(raw_sensor_value, (int, float, bool, type(None))):
      # Déjà un nombre, un booléen, ou de type None. Retourne directement.
      return raw_sensor_value
  else:
      # Type inattendu pour raw_sensor_value (ex: une liste, un autre dictionnaire sans clé 'value', etc.)
      _LOGGER.warning(
          "Type de données inattendu pour le champ '%s' (clé : '%s') : %s. Données : %s. Retourne None.",
          name, key, type(raw_sensor_value), raw_sensor_value
      )
      return None

API_FIELD_NAME_MAP: Final[dict[str, str]] = {
    "s1": "Device time",
    "s2": "Finished good serial number",
    "s3": "Drive type",
    "s4": "Wet end type",
    "s5": "Relay installed",
    "s6": "Wifi mac address",
    "s7": "Drive software version",
    "s8": "IoT version",
    "s9": "Controller version",
    "s10": "UDM application software version",
    "s11": "Security key",
    "s12": "Checksum",
    "s13": "RSSI",  # dBm
    "s14": "Active program number",
    "s15": "Active reference",
    "s16": "Active value",
    "s17": "Current pressure",  # psi
    "s18": "Current power",  # watts
    "s19": "Current motor speed",  # %
    "s20": "Alarm condition",
    "s21": "Relay 1 status",
    "s22": "Relay 2 status",
    "s23": "SSID",
    "s24": "Digital inputs",
    "s25": "Pump enabled status",
    "s26": "Current estimated flow",  # gallons per minute
    "s27": "Status word",
    "s28": "Remaining time",
    "s29": "Automation active",
    "s30": "Active program relay 1",
    "s31": "Active program relay 2",
    "s32": "Relay 1 remaining time",
    "s33": "Relay 2 remaining time",
    "s42": "Drive hardware version",
    "s43": "Comm board hardware version",
    "s44": "UDM assets software version",
    "s45": "UDM hardware version",
    "s46": "Drive flow table version",
    "s48": "Wifi level",
    "s50": "Feature bit",
    "d1": "Pump automation address",
    "d2": "Max speed",
    "d3": "Max flow",
    "d4": "Max pressure",
    "d5": "Priming speed",
    "d6": "Priming range",
    "d7": "Max priming duration",
    "d8": "Loss of prime",
    "d9": "Time source",
    "d10": "Flow program pressure max",
    "d11": "Thermal mode enable",
    "d13": "Thermal mode temperature",
    "d14": "Password protection scheme",
    "d15": "Password",
    "d16": "Daylight savings",
    "d17": "Device time zone",
    "d18": "Min speed",
    "d19": "Min flow",
    "d20": "Flow limit speed",
    "d21": "Pressure limit speed",
    "d22": "Priming enabled",
    "d23": "Dry start",
    "d24": "Priming delay",
    "d25": "Pump start stop",
    "d26": "Date provisioned",
    "d27": "Pump nickname",
    "d28": "Relay 1 name",
    "d29": "Relay 1 flow dependent",
    "d30": "Relay 2 name",
    "d31": "Relay 2 flow dependent",
    "d32": "Ramp rate up",
    "d33": "Ramp rate down",
    "d34": "Device resets",
    "d35": "Ble always on",
    "d36": "Relay 1 type",
    "d37": "Relay 2 type",
    "d38": "Booster pump delay",
    "d42": "Timezone string",
    "p1": "Setup complete flag",
    "p2": "Last active program",
    "1": "Pump type 1",
    "2": "Pump type 2",
    "zp1e1": "Program 1 id",
    "zp1e2": "Program 1 name",
    "zp1e3": "Program 1 reference",
    "zp1e4": "Program 1 value",
    "zp1e5": "Program 1 type",
    "zp1e6": "Program 1 start time of day",
    "zp1e7": "Program 1 duration",
    "zp1e8": "Program 1 days to run",
    "zp1e9": "Program 1 pump active",
    "zp1e10": "Program 1 enable",
    "zp1e11": "Program 1 relay 1",
    "zp1e12": "Program 1 relay 2",
    "zp1e13": "Program 1 exists",
    "zp1e14": "Program 1 relay 1 light mode",
    "zp1e15": "Program 1 relay 2 light mode",
    "zp2e1": "Program 2 id",
    "zp2e2": "Program 2 name",
    "zp2e3": "Program 2 reference",
    "zp2e4": "Program 2 value",
    "zp2e5": "Program 2 type",
    "zp2e6": "Program 2 start time of day",
    "zp2e7": "Program 2 duration",
    "zp2e8": "Program 2 days to run",
    "zp2e9": "Program 2 pump active",
    "zp2e10": "Program 2 enable",
    "zp2e11": "Program 2 relay 1",
    "zp2e12": "Program 2 relay 2",
    "zp2e13": "Program 2 exists",
    "zp2e14": "Program 2 relay 1 light mode",
    "zp2e15": "Program 2 relay 2 light mode",
    "zp3e1": "Program 3 id",
    "zp3e2": "Program 3 name",
    "zp3e3": "Program 3 reference",
    "zp3e4": "Program 3 value",
    "zp3e5": "Program 3 type",
    "zp3e6": "Program 3 start time of day",
    "zp3e7": "Program 3 duration",
    "zp3e8": "Program 3 days to run",
    "zp3e9": "Program 3 pump active",
    "zp3e10": "Program 3 enable",
    "zp3e11": "Program 3 relay 1",
    "zp3e12": "Program 3 relay 2",
    "zp3e13": "Program 3 exists",
    "zp3e14": "Program 3 relay 1 light mode",
    "zp3e15": "Program 3 relay 2 light mode",
    "zp4e1": "Program 4 id",
    "zp4e2": "Program 4 name",
    "zp4e3": "Program 4 reference",
    "zp4e4": "Program 4 value",
    "zp4e5": "Program 4 type",
    "zp4e6": "Program 4 start time of day",
    "zp4e7": "Program 4 duration",
    "zp4e8": "Program 4 days to run",
    "zp4e9": "Program 4 pump active",
    "zp4e10": "Program 4 enable",
    "zp4e11": "Program 4 relay 1",
    "zp4e12": "Program 4 relay 2",
    "zp4e13": "Program 4 exists",
    "zp4e14": "Program 4 relay 1 light mode",
    "zp4e15": "Program 4 relay 2 light mode",
    "zp5e1": "Program 5 id",
    "zp5e2": "Program 5 name",
    "zp5e3": "Program 5 reference",
    "zp5e4": "Program 5 value",
    "zp5e5": "Program 5 type",
    "zp5e6": "Program 5 start time of day",
    "zp5e7": "Program 5 duration",
    "zp5e8": "Program 5 days to run",
    "zp5e9": "Program 5 pump active",
    "zp5e10": "Program 5 enable",
    "zp5e11": "Program 5 relay 1",
    "zp5e12": "Program 5 relay 2",
    "zp5e13": "Program 5 exists",
    "zp5e14": "Program 5 relay 1 light mode",
    "zp5e15": "Program 5 relay 2 light mode",
    "zp6e1": "Program 6 id",
    "zp6e2": "Program 6 name",
    "zp6e3": "Program 6 reference",
    "zp6e4": "Program 6 value",
    "zp6e5": "Program 6 type",
    "zp6e6": "Program 6 start time of day",
    "zp6e7": "Program 6 duration",
    "zp6e8": "Program 6 days to run",
    "zp6e9": "Program 6 pump active",
    "zp6e10": "Program 6 enable",
    "zp6e11": "Program 6 relay 1",
    "zp6e12": "Program 6 relay 2",
    "zp6e13": "Program 6 exists",
    "zp6e14": "Program 6 relay 1 light mode",
    "zp6e15": "Program 6 relay 2 light mode",
    "zp7e1": "Program 7 id",
    "zp7e2": "Program 7 name",
    "zp7e3": "Program 7 reference",
    "zp7e4": "Program 7 value",
    "zp7e5": "Program 7 type",
    "zp7e6": "Program 7 start time of day",
    "zp7e7": "Program 7 duration",
    "zp7e8": "Program 7 days to run",
    "zp7e9": "Program 7 pump active",
    "zp7e10": "Program 7 enable",
    "zp7e11": "Program 7 relay 1",
    "zp7e12": "Program 7 relay 2",
    "zp7e13": "Program 7 exists",
    "zp7e14": "Program 7 relay 1 light mode",
    "zp7e15": "Program 7 relay 2 light mode",
    "zp8e1": "Program 8 id",
    "zp8e2": "Program 8 name",
    "zp8e3": "Program 8 reference",
    "zp8e4": "Program 8 value",
    "zp8e5": "Program 8 type",
    "zp8e6": "Program 8 start time of day",
    "zp8e7": "Program 8 duration",
    "zp8e8": "Program 8 days to run",
    "zp8e9": "Program 8 pump active",
    "zp8e10": "Program 8 enable",
    "zp8e11": "Program 8 relay 1",
    "zp8e12": "Program 8 relay 2",
    "zp8e13": "Program 8 exists",
    "zp8e14": "Program 8 relay 1 light mode",
    "zp8e15": "Program 8 relay 2 light mode",
    "zp9e2": "Program 9 name",
    "zp9e3": "Program 9 reference",
    "zp9e4": "Program 9 value",
    "zp9e5": "Program 9 type",
    "zp9e6": "Program 9 start time of day",
    "zp9e7": "Program 9 duration",
    "zp9e8": "Program 9 days to run",
    "zp9e9": "Program 9 pump active",
    "zp9e10": "Program 9 enable",
    "zp9e11": "Program 9 relay 1",
    "zp9e12": "Program 9 relay 2",
    "zp9e13": "Program 9 exists",
    "zp9e14": "Program 9 relay 1 light mode",
    "zp9e15": "Program 9 relay 2 light mode",
    "zp10e3": "Program 10 reference",
    "zp10e4": "Program 10 value",
    "zp10e5": "Program 10 type",
    "zp11e3": "Program 11 reference",
    "zp11e4": "Program 11 value",
    "zp11e5": "Program 11 type",
    "zp12e3": "Program 12 reference",
    "zp12e4": "Program 12 value",
    "zp12e5": "Program 12 type",
    "zp13e3": "Program 13 reference",
    "zp13e4": "Program 13 value",
    "zp13e5": "Program 13 type",
    "zp14e3": "Program 14 reference",
    "zp14e4": "Program 14 value",
    "zp14e5": "Program 14 type",
}


API_FIELD_VALUE_FUNCTION: Final[dict[str, Callable]] = {
    "s1": lambda value: datetime.strptime(value, "%y%m%d%H%M%S"),  # Device time
    "s13": int,  # RSSI (dBm)
    "s17": _divide_by_10,  # Current pressure (psi)
    "s18": int,  # Current power (watts)
    "s19": _divide_by_10,  # Current motor speed (%)
    "s25": bool,  # Pump enabled status
    "s26": _divide_by_10,  # Current estimated flow (gallons per minute)
}

def get_api_field_name_and_value(
    key: str, value: str | int | float | datetime
) -> tuple[str, Any]:
    """Get the API field name and converted value."""
    name = API_FIELD_NAME_MAP.get(key, key)

    raw_value_to_process = value
        
    if isinstance(value, dict) and "value" in value:
        raw_value_to_process = value["value"]
    
    if _fn := API_FIELD_VALUE_FUNCTION.get(key):
      try:
        val = _fn(raw_value_to_process)
      except Exception as ex:  # ignore: bare-except
        _LOGGER.error(
                "Could not convert key '%s%s' value '%s': %s (data received: %s, raw_value_to_process: %s)",
                key,
                f" ({name})" if name != key else "",
                raw_value_to_process, # Log the actual value that caused the error
                ex,
                value, # Log the full dictionary received
                raw_value_to_process # Log the extracted raw value again for clarity
            )
        _LOGGER.warning('name "%s"', name)
        _LOGGER.warning('val "%s"', val)
        _LOGGER.warning('value "%s"', value)
    return name, val