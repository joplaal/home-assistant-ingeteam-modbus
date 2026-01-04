import logging
from datetime import time
from homeassistant.components.time import TimeEntity
from homeassistant.const import CONF_NAME
from .const import DOMAIN, ATTR_MANUFACTURER

_LOGGER = logging.getLogger(__name__)

TIME_TYPES = {
    "config_soc_ac_charging_time_start1": {
        "name": "Config SOC AC Charging Time Start1",
        "key": "config_soc_ac_charging_time_start1",
        "icon": "mdi:clock-start",
        "address": 33,
    },
    "config_soc_ac_charging_time_end1": {
        "name": "Config SOC AC Charging Time End1",
        "key": "config_soc_ac_charging_time_end1",
        "icon": "mdi:clock-end",
        "address": 34,
    },
    "config_soc_ac_charging_time_start2": {
        "name": "Config SOC AC Charging Time Start2",
        "key": "config_soc_ac_charging_time_start2",
        "icon": "mdi:clock-start",
        "address": 36,
    },
    "config_soc_ac_charging_time_end2": {
        "name": "Config SOC AC Charging Time End2",
        "key": "config_soc_ac_charging_time_end2",
        "icon": "mdi:clock-end",
        "address": 37,
    },
}

async def async_setup_entry(hass, entry, async_add_entities):
    hub_name = entry.data[CONF_NAME]
    hub = hass.data[DOMAIN][hub_name]["hub"]

    entities = []
    for key, info in TIME_TYPES.items():
        entities.append(IngeteamTime(hub, hub_name, info))

    async_add_entities(entities)

class IngeteamTime(TimeEntity):
    def __init__(self, hub, hub_name, info):
        self._hub = hub
        self._hub_name = hub_name
        self._key = info["key"]
        self._attr_name = info["name"]
        # Append _time to unique_id to force new entity creation with correct name prefix
        self._attr_unique_id = f"{hub_name}_{info['key']}_time"
        self._attr_icon = info["icon"]
        self._address = info["address"]
        self._attr_device_info = {
            "identifiers": {(DOMAIN, hub_name)},
            "name": hub_name,
            "manufacturer": ATTR_MANUFACTURER,
        }

    @property
    def name(self):
        return f"{self._hub_name} {self._attr_name}"

    @property
    def native_value(self):
        val_str = self._hub.data.get(self._key)
        if val_str:
            try:
                parts = val_str.split(":")
                return time(hour=int(parts[0]), minute=int(parts[1]))
            except (ValueError, IndexError):
                return None
        return None

    async def async_set_value(self, value: time) -> None:
        """Update the current value."""
        # Convert time to HHMM hex format (integer)
        # e.g. 08:30 -> 0x0830 -> 2096
        int_val = (value.hour << 8) | value.minute
        
        await self._hub.write_modbus_register(self._address, int_val)
        
        # Update local state
        self._hub.data[self._key] = f"{value.hour:02d}:{value.minute:02d}"
        self.async_write_ha_state()
