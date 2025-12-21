"""The Ingeteam Modbus Integration."""
import asyncio
import logging
import threading
from datetime import timedelta
from typing import Optional

import voluptuous as vol
from pymodbus.exceptions import ModbusException

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    DOMAIN,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_MODBUS_ADDRESS,
    DEFAULT_MODEL,
    CONF_MODBUS_ADDRESS,
    CONF_READ_METER,
    CONF_READ_BATTERY,
    CONF_MODEL,
    DEFAULT_READ_METER,
    DEFAULT_READ_BATTERY,
    REGISTER_MAPS,
    BOOLEAN_STATUS,
    INVERTER_STATUS,
    BATTERY_STATUS,
    BATTERY_BMS_ALARMS,
    BATTERY_LIMITATION_REASONS,
    AP_REDUCTION_REASONS,
)
from .modbus_client import ModbusClient, AsyncModbusClient

_LOGGER = logging.getLogger(__name__)

INGETEAM_MODBUS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT): cv.string,
        vol.Optional(CONF_MODBUS_ADDRESS, default=DEFAULT_MODBUS_ADDRESS): cv.positive_int,
        vol.Optional(CONF_MODEL, default=DEFAULT_MODEL): vol.In(["auto", "1play", "3play"]),
        vol.Optional(CONF_READ_METER, default=DEFAULT_READ_METER): cv.boolean,
        vol.Optional(CONF_READ_BATTERY, default=DEFAULT_READ_BATTERY): cv.boolean,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.positive_int,
    }
)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({cv.slug: INGETEAM_MODBUS_SCHEMA})}, extra=vol.ALLOW_EXTRA)

PLATFORMS = ["sensor"]


async def async_setup(hass, config):
    """Set up the Ingeteam modbus component."""
    hass.data[DOMAIN] = {}
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up a ingeteam mobus."""
    host = entry.data[CONF_HOST]
    name = entry.data[CONF_NAME]
    port = entry.data[CONF_PORT]
    address = entry.data.get(CONF_MODBUS_ADDRESS, 1)
    scan_interval = entry.data[CONF_SCAN_INTERVAL]
    read_meter = entry.data.get(CONF_READ_METER, False)
    read_battery = entry.data.get(CONF_READ_BATTERY, False)
    model = entry.data.get(CONF_MODEL, DEFAULT_MODEL)

    _LOGGER.debug("Setup %s.%s with model=%s", DOMAIN, name, model)

    hub = IngeteamModbusHub(
        hass,
        name,
        host,
        port,
        address,
        scan_interval,
        read_meter,
        read_battery,
        model,
    )

    """Register the hub."""
    hass.data[DOMAIN][name] = {"hub": hub}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    """Unload Ingeteam mobus entry."""
    hub: "IngeteamModbusHub" = hass.data[DOMAIN][entry.data["name"]]["hub"]
    hub.close()

    unload_ok = all(
        await asyncio.gather(
            *[hass.config_entries.async_forward_entry_unload(entry, component) for component in PLATFORMS]
        )
    )
    if not unload_ok:
        return False

    hass.data[DOMAIN].pop(entry.data["name"])
    return True


class IngeteamModbusHub:
    """Thread safe wrapper class for pymodbus."""

    def __init__(self, hass, name, host, port, address, scan_interval, 
                 read_meter=True, read_battery=False, model="auto"):
        """Initialize the Modbus hub."""
        self._hass = hass
        self._name = name
        self._address = address
        self._host = host
        self._port = port
        self.read_meter = read_meter
        self.read_battery = read_battery
        self._model = model
        self._scan_interval = timedelta(seconds=scan_interval)
        self._unsub_interval_method = None
        self._sensors = []
        self.data = {}
        
        # Initialize the new Modbus client
        timeout = max(3.0, scan_interval - 1.0)
        self._modbus_client = ModbusClient(
            host=host,
            port=port,
            timeout=timeout,
            retries=2,
            retry_delay=0.5
        )
        self._async_client = AsyncModbusClient(self._modbus_client)
        
        # Determine the register map to use
        self.register_map = self._determine_register_map()
        
        _LOGGER.info(
            "Initialized hub %s with model=%s, register_map=%s",
            name, model, self.register_map.name if self.register_map else "None"
        )

    def _determine_register_map(self):
        """Determine which register map to use based on configuration."""
        if self._model == "1play":
            _LOGGER.info("📋 Using configured 1Play register map")
            return REGISTER_MAPS.get("1play")
        elif self._model == "3play":
            _LOGGER.info("📋 Using configured 3Play Low Address (Hybrid) register map")
            return REGISTER_MAPS.get("3play")
        else:  # auto detection mode
            _LOGGER.info("🔍 Starting auto-detection mode...")
            _LOGGER.info("   Will attempt to detect: model=%s", self._model)
            
            # Start with 3Play Low map for initial detection as it's the most complex
            _LOGGER.debug("Auto-detection starting with 3Play Low registers")
            return REGISTER_MAPS.get("3play")

    @callback
    def async_add_ingeteam_sensor(self, update_callback):
        """Listen for data updates."""
        if not self._sensors:
            self._unsub_interval_method = async_track_time_interval(
                self._hass, self.async_refresh_modbus_data, self._scan_interval
            )
        self._sensors.append(update_callback)

    @callback
    def async_remove_ingeteam_sensor(self, update_callback):
        """Remove data update."""
        self._sensors.remove(update_callback)
        if not self._sensors and self._unsub_interval_method:
            self._unsub_interval_method()
            self._unsub_interval_method = None
            asyncio.create_task(self._async_client.disconnect())

    async def async_refresh_modbus_data(self, _now: Optional[int] = None) -> None:
        """Time to update."""
        if not self._sensors:
            return
        
        try:
            success = await self._update_modbus_data()
            if success:
                for update_callback in self._sensors:
                    update_callback()
            else:
                _LOGGER.warning("Failed to update modbus data")
        except Exception as e:
            _LOGGER.error("Error during modbus data update: %s", e)

    async def _update_modbus_data(self) -> bool:
        """Fetch data from the modbus device."""
        if not self.register_map:
            _LOGGER.error("No register map available")
            return False
        
        try:
            # Read data using the register map
            result = await self._async_client.read_register_map(self.register_map, self._address)
            
            if result.success:
                # Update internal data
                self.data.update(result.data)
                
                # Perform auto-detection if needed
                if self._model == "auto":
                    await self._perform_auto_detection(result.data)
                
                _LOGGER.debug("Successfully read %d registers", len(result.data))
                return True
            else:
                _LOGGER.warning("Failed to read modbus data: %s", result.error)
                
                # Try fallback if in auto mode
                if self._model == "auto":
                    return await self._try_fallback_maps()
                
                return False
                
        except Exception as e:
            _LOGGER.error("Error reading modbus data: %s", e)
            return False

    async def _perform_auto_detection(self, data):
        """Perform intelligent auto-detection based on successful reads and register patterns."""
        _LOGGER.info("Performing auto-detection based on %d registers read", len(data))
        
        # Detection criteria for 3Play
        three_play_indicators = {
            'ac_trifasico': ['ac_l1_voltage', 'ac_l2_voltage', 'ac_l3_voltage'],
            'pv_multiple': ['pv3_voltage', 'pv4_voltage'],  # 3Play has 4 PV inputs
            'battery_detailed': ['bat_voltage', 'bat_soc', 'bat_state'],
            'critical_loads': ['crit_voltage', 'crit_power'],
            'internal_meter': ['meter_voltage', 'meter_power'],
            'system_advanced': ['temp_mod_1', 'temp_mod_2', 'dc_bus_voltage']
        }
        
        # Detection criteria for 1Play  
        one_play_indicators = {
            'basic_power': ['active_power', 'reactive_power', 'power_factor'],
            'basic_pv': ['pv1_voltage', 'pv2_voltage'],  # 1Play typically has 2 PV inputs
            'simple_system': ['dc_bus_voltage']
        }
        
        # Score the detection
        three_play_score = 0
        one_play_score = 0
        
        for category, registers in three_play_indicators.items():
            matches = sum(1 for reg in registers if reg in data)
            if matches > 0:
                three_play_score += matches * 2  # Weight 3Play indicators higher
                _LOGGER.debug("3Play indicator '%s': %d/%d matches", category, matches, len(registers))
        
        for category, registers in one_play_indicators.items():
            matches = sum(1 for reg in registers if reg in data)
            if matches > 0:
                one_play_score += matches
                _LOGGER.debug("1Play indicator '%s': %d/%d matches", category, matches, len(registers))
        
        # Special bonus for definitive 3Play features
        if any(reg in data for reg in ['ac_l2_voltage', 'ac_l3_voltage']):
            three_play_score += 10  # Trifasic AC is definitive
            _LOGGER.debug("Definitive 3Play feature detected: trifasic AC")
            
        if any(reg in data for reg in ['pv3_voltage', 'pv4_voltage']):
            three_play_score += 8  # 4 PV inputs is strong indicator
            _LOGGER.debug("Strong 3Play feature detected: 4 PV inputs")
            
        if any(reg in data for reg in ['bat_voltage', 'crit_voltage']):
            three_play_score += 6  # Battery and critical loads
            _LOGGER.debug("Strong 3Play feature detected: battery/critical loads")
        
        _LOGGER.info("Auto-detection scores: 3Play=%d, 1Play=%d", three_play_score, one_play_score)
        
        # Make decision
        if three_play_score > one_play_score and three_play_score >= 5:
            if self._model == "auto":
                _LOGGER.info("🔍 Auto-detected: 3Play Low (Hybrid) inverter (score: %d)", three_play_score)
                self._model = "3play"
                self.register_map = REGISTER_MAPS.get("3play")
                    
        elif one_play_score > 0:
            if self._model == "auto":
                _LOGGER.info("🔍 Auto-detected: 1Play inverter (score: %d)", one_play_score)
                self._model = "1play" 
                self.register_map = REGISTER_MAPS.get("1play")
        else:
            _LOGGER.warning("⚠️ Could not confidently auto-detect model (3Play:%d, 1Play:%d)", 
                          three_play_score, one_play_score)

    async def _try_fallback_maps(self) -> bool:
        """Try fallback register maps with intelligent ordering."""
        _LOGGER.info("🔄 Attempting fallback detection...")
        
        # Define fallback sequence - most likely to least likely
        fallback_sequence = [
            # First try 3Play Low (Hybrid)
            ("3play", REGISTER_MAPS.get("3play")),
            # Then try 1Play (legacy inverters)
            ("1play", REGISTER_MAPS.get("1play")),
        ]
        
        for map_name, fallback_map in fallback_sequence:
            if not fallback_map:
                _LOGGER.debug("Skipping unavailable map: %s", map_name)
                continue
                
            _LOGGER.info("🧪 Testing fallback register map: %s", map_name)
            
            try:
                result = await self._async_client.read_register_map(fallback_map, self._address)
                
                if result.success and len(result.data) > 0:
                    # Validate that we got meaningful data
                    meaningful_data = self._validate_meaningful_data(result.data)
                    
                    if meaningful_data:
                        _LOGGER.info("✅ Fallback successful with %s (%d registers, %d meaningful)", 
                                   map_name, len(result.data), meaningful_data)
                        
                        # Update configuration based on successful fallback
                        self.register_map = fallback_map
                        self.data.update(result.data)
                        
                        # Update model based on what worked
                        if map_name == "3play":
                            self._model = "3play"
                        elif "1play" in map_name:
                            self._model = "1play"
                        
                        _LOGGER.info("🎯 Auto-configuration updated: model=%s", self._model)
                        return True
                    else:
                        _LOGGER.debug("❌ %s returned data but not meaningful", map_name)
                else:
                    _LOGGER.debug("❌ %s failed: %s", map_name, result.error if result.error else "no data")
                    
            except Exception as e:
                _LOGGER.debug("❌ %s exception: %s", map_name, e)
                continue
        
        _LOGGER.error("🚫 All fallback attempts failed - device may not be compatible")
        return False

    def _validate_meaningful_data(self, data) -> int:
        """Validate that the data contains meaningful values (not all zeros/nulls)."""
        meaningful_count = 0
        
        # Check for meaningful values in key registers
        meaningful_keys = [
            'active_power', 'pv1_voltage', 'pv1_power', 'pv2_voltage', 'pv2_power',
            'ac_l1_voltage', 'bat_voltage', 'dc_bus_voltage', 'temp_mod_1'
        ]
        
        for key in meaningful_keys:
            value = data.get(key)
            if value is not None and value != 0:
                # Additional validation for voltage/power ranges
                if 'voltage' in key and (10 <= value <= 1000):  # Reasonable voltage range
                    meaningful_count += 2  # Weight voltages higher
                elif 'power' in key and (0 <= abs(value) <= 50000):  # Reasonable power range
                    meaningful_count += 2
                elif 'temp' in key and (-20 <= value <= 80):  # Reasonable temperature range  
                    meaningful_count += 1
                elif value > 0:  # Any other positive value
                    meaningful_count += 1
        
        return meaningful_count

    @property
    def name(self):
        """Return the name of this hub."""
        return self._name

    def close(self):
        """Disconnect client."""
        if self._modbus_client:
            self._modbus_client.disconnect()

    # Legacy methods for backward compatibility
    def connect(self) -> bool:
        """Connect client."""
        return self._modbus_client.connect()

    def read_input_registers(self, unit, address, count):
        """Read input registers (legacy method)."""
        return self._modbus_client._read_registers_with_retry(unit, address, count, is_input=True)

    def read_modbus_data(self) -> bool:
        """Legacy method for reading modbus data."""
        # This will be called by legacy sensors, try to return some basic data
        try:
            if self.register_map:
                result = asyncio.run(self._async_client.read_register_map(self.register_map, self._address))
                if result.success:
                    self.data.update(result.data)
                    return True
            return False
        except Exception as e:
            _LOGGER.error("Error in legacy read_modbus_data: %s", e)
            return False

    def get_register_value(self, register_name: str):
        """Get the value of a specific register by name."""
        return self.data.get(register_name)
