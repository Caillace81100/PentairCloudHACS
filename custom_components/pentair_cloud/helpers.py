"""Helpers."""

from __future__ import annotations

from datetime import datetime
import logging
from time import time
from typing import Any

from pypentair.utils import get_api_field_name_and_value

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
    

def get_field_value(key: str, data: dict) -> Any:
  """Obtient la valeur d'un champ à partir des données Pentair, en gérant les structures imbriquées et les conversions."""
  field_data = data["fields"].get(key)

  if field_data is None:
    _LOGGER.debug('La clé "%s" est manquante dans les données des champs pour l\'appareil "%s". Retourne None.',
                key, data.get("name", "appareil_inconnu"))
    return None
  
  _LOGGER.warning('field_data "%s"', field_data)

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
