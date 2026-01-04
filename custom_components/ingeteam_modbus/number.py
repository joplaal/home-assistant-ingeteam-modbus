import logging
from homeassistant.components.number import NumberEntity
from homeassistant.const import PERCENTAGE, CONF_NAME
from .const import DOMAIN, ATTR_MANUFACTURER

_LOGGER = logging.getLogger(__name__)

NUMBER_TYPES = {
    "config_soc_min": {
        "name": "Config SOC Min",
        "key": "config_soc_min",
        "native_unit_of_measurement": PERCENTAGE,
        "icon": "mdi:battery-low",
        "address": 28,
        "min": 0,
        "max": 100,
    },
    "config_soc_ac_charging_soc_grid1": {
        "name": "Config SOC AC Charging SOC Grid1",
        "key": "config_soc_ac_charging_soc_grid1",
        "native_unit_of_measurement": PERCENTAGE,
        "icon": "mdi:battery-charging",
        "address": 32,
        "min": 0,
        "max": 100,
    },
    "config_soc_ac_charging_soc_grid2": {
        "name": "Config SOC AC Charging SOC Grid2",
        "key": "config_soc_ac_charging_soc_grid2",
        "native_unit_of_measurement": PERCENTAGE,
        "icon": "mdi:battery-charging",
        "address": 35,
        "min": 0,
        "max": 100,
    },
}

async def async_setup_entry(hass, entry, async_add_entities):
    hub_name = entry.data[CONF_NAME]
    hub = hass.data[DOMAIN][hub_name]["hub"]

    entities = []
    for key, info in NUMBER_TYPES.items():
        entities.append(IngeteamNumber(hub, hub_name, info))

    async_add_entities(entities)

class IngeteamNumber(NumberEntity):
    def __init__(self, hub, hub_name, info):
        self._hub = hub
        self._hub_name = hub_name
        self._key = info["key"]
        self._attr_name = info["name"]
        self._attr_unique_id = f"{hub_name}_{info['key']}"
        self._attr_native_unit_of_measurement = info["native_unit_of_measurement"]
        self._attr_icon = info["icon"]
        self._address = info["address"]
        self._attr_native_min_value = info["min"]
        self._attr_native_max_value = info["max"]
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
        return self._hub.data.get(self._key)

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._hub.write_modbus_register(self._address, int(value))
        self._hub.data[self._key] = int(value)
        self.async_write_ha_state()
