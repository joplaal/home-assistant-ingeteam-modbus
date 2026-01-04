from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import CONF_NAME
from .const import DOMAIN, ATTR_MANUFACTURER

SCHEDULE_OPTIONS = {
    "Desactivado": "0",
    "Toda la semana": "1",
    "Entre semana (L-V)": "2",
    "Fin de semana (S-D)": "3",
}

async def async_setup_entry(hass, entry, async_add_entities):
    hub_name = entry.data[CONF_NAME]
    hub = hass.data[DOMAIN][hub_name]["hub"]

    device_info = {
        "identifiers": {(DOMAIN, hub_name)},
        "name": hub_name,
        "manufacturer": ATTR_MANUFACTURER,
    }

    entities = [
        IngeteamScheduleSelect(hub, device_info, "Horario 1 Tipo", "config_soc_ac_charging_schedule1_type", 1),
        IngeteamScheduleSelect(hub, device_info, "Horario 2 Tipo", "config_soc_ac_charging_schedule2_type", 2),
    ]
    
    async_add_entities(entities)

class IngeteamScheduleSelect(SelectEntity):
    """Representation of an Ingeteam Schedule Select."""

    def __init__(self, hub, device_info, name, key, schedule_index):
        self._hub = hub
        self._device_info = device_info
        self._name = name
        self._key = key
        self._schedule_index = schedule_index # 1 or 2
        self._attr_options = list(SCHEDULE_OPTIONS.keys())
        self._attr_current_option = None

    @property
    def name(self):
        return f"{self._hub.name} {self._name}"

    @property
    def unique_id(self):
        return f"{self._hub.name}_{self._key}_select"

    @property
    def device_info(self):
        return self._device_info

    @property
    def current_option(self):
        """Return the current selected option."""
        # Get the value from the hub data (which is already decoded text like "Desactivado", "Toda la semana"...)
        # We need to match it to our options list
        current_val = self._hub.data.get(self._key)
        
        # The hub stores decoded strings like "Toda la semana", "Desactivado", etc.
        # But sometimes it might store "Otro (X)".
        # We try to find an exact match
        if current_val in self._attr_options:
            return current_val
        
        # If not found (e.g. "Otro (5)"), default to Desactivado or handle gracefully
        return "Desactivado"

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        value = int(SCHEDULE_OPTIONS[option])
        await self._hub.set_schedule_type(self._schedule_index, value)
        
        # Optimistically update the state
        self._attr_current_option = option
        self.async_write_ha_state()
