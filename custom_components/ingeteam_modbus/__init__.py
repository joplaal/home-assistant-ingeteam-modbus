"""The Ingeteam Modbus Integration."""
import asyncio
import logging
import threading
from datetime import timedelta
from typing import Optional

import voluptuous as vol
from pymodbus.client import ModbusTcpClient
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
    CONF_MODBUS_ADDRESS,
    CONF_READ_METER,
    CONF_READ_BATTERY,
    DEFAULT_READ_METER,
    DEFAULT_READ_BATTERY,
    BOOLEAN_STATUS,
    INVERTER_STATUS,
    BATTERY_STATUS,
    BATTERY_BMS_ALARMS,
    BATTERY_LIMITATION_REASONS,
    AP_REDUCTION_REASONS,
)

_LOGGER = logging.getLogger(__name__)

INGETEAM_MODBUS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT): cv.string,
        vol.Optional(CONF_MODBUS_ADDRESS, default=DEFAULT_MODBUS_ADDRESS): cv.positive_int,
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

    _LOGGER.debug("Setup %s.%s", DOMAIN, name)

    hub = IngeteamModbusHub(
        hass,
        name,
        host,
        port,
        address,
        scan_interval,
        read_meter,
        read_battery,
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

    def __init__(self, hass, name, host, port, address, scan_interval, read_meter=True, read_battery=False):
        """Initialize the Modbus hub."""
        self._hass = hass
        self._client = ModbusTcpClient(host=host, port=port, timeout=max(3, (scan_interval - 1)))
        self._lock = threading.Lock()
        self._name = name
        self._address = address
        self._host = host
        self._port = port
        self.read_meter = read_meter
        self.read_battery = read_battery
        self._scan_interval = timedelta(seconds=scan_interval)
        self._unsub_interval_method = None
        self._sensors = []
        self.data = {}

    @callback
    def async_add_ingeteam_sensor(self, update_callback):
        """Listen for data updates."""
        if not self._sensors:
            self.connect()
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
            self.close()

    async def async_refresh_modbus_data(self, _now: Optional[int] = None) -> None:
        """Time to update."""
        if not self._sensors:
            return
        update_result = await self._hass.async_add_executor_job(self._update_modbus_data)
        if update_result:
            for update_callback in self._sensors:
                update_callback()

    def _update_modbus_data(self) -> bool:
        """Synchronously fetch data from the modbus device. To be run in an executor."""
        if not self._check_and_reconnect():
            return False
        try:
            return self.read_modbus_data()
        except ModbusException as e:
            _LOGGER.warning("Modbus exception occurred while reading data: %s", e)
            return False
        except Exception:
            _LOGGER.exception("Unexpected error while reading modbus data")
            return False

    @property
    def name(self):
        """Return the name of this hub."""
        return self._name

    def close(self):
        """Disconnect client."""
        with self._lock:
            self._client.close()

    def _check_and_reconnect(self) -> bool:
        """Check connection and reconnect if needed."""
        with self._lock:
            if not self._client.is_socket_open():
                _LOGGER.info("Modbus client is not connected, trying to reconnect")
                return self._client.connect()
            return True

    def connect(self) -> bool:
        """Connect client."""
        with self._lock:
            result = self._client.connect()
            if result:
                _LOGGER.info("Successfully connected to %s:%s", self._host, self._port)
            else:
                _LOGGER.warning("Could not connect to %s:%s", self._host, self._port)
            return result

    def read_input_registers(self, unit, address, count):
        """Read input registers."""
        with self._lock:
            try:
                return self._client.read_input_registers(address=address, count=count, slave=unit)
            except TypeError:
                return self._client.read_input_registers(address=address, count=count, unit=unit)

    @staticmethod
    def _decode_signed(value: int) -> int:
        """Decode a 16-bit signed integer (two's complement)."""
        if value & 0x8000:
            return value - 0x10000
        return value

    @staticmethod
    def _u32_from_words_le(registers, start_index: int) -> int:
        """
        Combina dos registros de 16 bits en un uint32.
        Orden de palabras 'little' (wordorder LITTLE): low word primero.
        """
        low = registers[start_index]
        high = registers[start_index + 1]
        return (high << 16) | low

    def read_modbus_data(self) -> bool:
        """Read and decode all registers in a single, optimized function."""
        # Read 0-130 to cover all 3Play Hybrid registers
        # Split into two chunks to be safe (0-100, 100-30)
        
        # Chunk 1: 0-100
        req1 = self.read_input_registers(unit=self._address, address=0, count=100)
        if req1.isError():
            _LOGGER.error("Error reading modbus registers (0-100): %s", req1)
            return False
        
        # Chunk 2: 100-130
        req2 = self.read_input_registers(unit=self._address, address=100, count=30)
        if req2.isError():
            _LOGGER.error("Error reading modbus registers (100-130): %s", req2)
            return False

        registers = req1.registers + req2.registers
        
        if len(registers) < 130:
             _LOGGER.warning("Incomplete Modbus response, expected 130 registers but got %s", len(registers))
             return False

        # --- 3Play Hybrid Mapping ---
        
        # System Status
        self.data["rms_diff_current"] = registers[1] / 1.0
        self.data["total_hours"] = self._u32_from_words_le(registers, 6)
        self.data["alarm_code"] = self._u32_from_words_le(registers, 10)
        
        # Battery
        self.data["battery_voltage"] = registers[16] / 10.0
        self.data["battery_voltage_internal"] = registers[17] / 10.0
        self.data["battery_power"] = self._decode_signed(registers[18]) / 1.0
        # Legacy battery power aliases
        self.data["battery_charging_power"] = self.data["battery_power"]
        self.data["battery_discharging_power"] = self.data["battery_power"]
        
        self.data["battery_current"] = self._decode_signed(registers[19]) / 100.0
        self.data["battery_status"] = BATTERY_STATUS.get(registers[21], f"Unknown ({registers[21]})")
        self.data["battery_state_of_charge"] = registers[22] / 1.0
        self.data["battery_state_of_health"] = registers[23] / 1.0
        self.data["battery_charging_current_max"] = registers[24] / 100.0
        self.data["battery_discharging_current_max"] = registers[25] / 100.0
        self.data["battery_charging_voltage"] = registers[28] / 10.0
        self.data["battery_discharging_voltage"] = registers[29] / 10.0
        self.data["battery_temp"] = self._decode_signed(registers[31]) / 10.0
        self.data["battery_bms_alarm"] = registers[47]
        self.data["battery_discharge_limitation_reason"] = registers[48] # Placeholder mapping
        
        # PV
        self.data["pv1_voltage"] = registers[32] / 1.0
        self.data["pv1_current"] = registers[33] / 100.0
        self.data["pv1_power"] = registers[34] / 1.0
        self.data["pv2_voltage"] = registers[35] / 1.0
        self.data["pv2_current"] = registers[36] / 100.0
        self.data["pv2_power"] = registers[37] / 1.0
        
        # Legacy Totals
        self.data["p_total"] = self._decode_signed(registers[38]) / 1.0
        self.data["active_power"] = self.data["p_total"] # Alias
        self.data["q_total"] = self._decode_signed(registers[39]) / 1.0
        self.data["reactive_power"] = self.data["q_total"] # Alias
        self.data["power_factor"] = self._decode_signed(registers[40]) / 1000.0
        self.data["dc_bus_voltage"] = registers[41] / 1.0
        
        # Critical Loads (AC Output)
        self.data["cl_current_l1"] = registers[49] / 100.0
        self.data["ac_l1_current"] = self.data["cl_current_l1"] # Alias
        self.data["cl_active_power_l1"] = self._decode_signed(registers[51]) / 10.0
        self.data["ac_l1_power"] = self.data["cl_active_power_l1"] # Alias
        
        self.data["cl_current_l2"] = registers[53] / 100.0
        self.data["ac_l2_current"] = self.data["cl_current_l2"] # Alias
        self.data["cl_active_power_l2"] = self._decode_signed(registers[55]) / 10.0
        self.data["ac_l2_power"] = self.data["cl_active_power_l2"] # Alias
        
        self.data["cl_current_l3"] = registers[57] / 100.0
        self.data["ac_l3_current"] = self.data["cl_current_l3"] # Alias
        self.data["cl_active_power_l3"] = self._decode_signed(registers[59]) / 10.0
        self.data["ac_l3_power"] = self.data["cl_active_power_l3"] # Alias
        
        self.data["cl_voltage_l1"] = registers[60] / 10.0
        self.data["ac_l1_voltage"] = self.data["cl_voltage_l1"] # Alias
        self.data["cl_voltage_l2"] = registers[61] / 10.0
        self.data["ac_l2_voltage"] = self.data["cl_voltage_l2"] # Alias
        self.data["cl_voltage_l3"] = registers[62] / 10.0
        self.data["ac_l3_voltage"] = self.data["cl_voltage_l3"] # Alias
        
        self.data["cl_freq"] = registers[63] / 100.0
        self.data["ac_l1_freq"] = self.data["cl_freq"] # Alias
        self.data["ac_l2_freq"] = self.data["cl_freq"] # Alias
        self.data["ac_l3_freq"] = self.data["cl_freq"] # Alias
        
        self.data["total_loads_power"] = registers[65] / 1.0
        
        self.data["cl_reactive_power_l1"] = self._decode_signed(registers[67]) / 1.0
        self.data["cl_reactive_power_l2"] = self._decode_signed(registers[69]) / 1.0
        self.data["cl_reactive_power_l3"] = self._decode_signed(registers[71]) / 1.0
        
        # Internal Meter
        self.data["im_voltage"] = registers[75] / 10.0 # L1 proxy
        self.data["im_voltage_l1"] = registers[75] / 10.0
        self.data["im_current_l1"] = registers[76] / 100.0
        self.data["im_voltage_l2"] = registers[77] / 10.0
        self.data["im_current_l2"] = registers[78] / 100.0
        self.data["im_voltage_l3"] = registers[79] / 10.0
        self.data["im_current_l3"] = registers[80] / 100.0
        
        self.data["im_freq"] = registers[81] / 100.0
        
        self.data["im_active_power_l1"] = self._decode_signed(registers[83]) / 10.0
        self.data["im_reactive_power_l1"] = self._decode_signed(registers[84]) / 10.0
        self.data["im_active_power_l2"] = self._decode_signed(registers[85]) / 10.0
        self.data["im_reactive_power_l2"] = self._decode_signed(registers[86]) / 10.0
        self.data["im_active_power_l3"] = self._decode_signed(registers[87]) / 10.0
        self.data["im_reactive_power_l3"] = self._decode_signed(registers[88]) / 10.0
        
        self.data["im_power_factor"] = self._decode_signed(registers[89]) / 1000.0
        
        # External Meter
        self.data["em_active_power_l1"] = self._decode_signed(registers[91]) / 1.0
        self.data["em_reactive_power_l1"] = self._decode_signed(registers[92]) / 1.0
        self.data["em_active_power_l2"] = self._decode_signed(registers[95]) / 1.0
        self.data["em_reactive_power_l2"] = self._decode_signed(registers[96]) / 1.0
        self.data["em_active_power_l3"] = self._decode_signed(registers[99]) / 1.0
        self.data["em_reactive_power_l3"] = self._decode_signed(registers[100]) / 1.0
        
        self.data["em_voltage"] = registers[102] / 1.0
        self.data["em_freq"] = registers[103] / 10.0
        self.data["ev_power"] = self._decode_signed(registers[104]) / 1.0
        self.data["em_active_power_returned"] = self._decode_signed(registers[105]) / 1.0
        
        self.data["do_1_status"] = registers[106]
        self.data["do_2_status"] = registers[108]
        self.data["di_drm_status"] = registers[110]
        self.data["di_2_status"] = registers[111]
        self.data["di_3_status"] = registers[112]
        
        self.data["temp_mod_1"] = self._decode_signed(registers[125]) / 1.0
        self.data["temp_mod_2"] = self._decode_signed(registers[126]) / 1.0
        self.data["temp_pcb"] = self._decode_signed(registers[127]) / 1.0
        self.data["inverter_state"] = registers[129]
        self.data["status"] = INVERTER_STATUS.get(registers[129], f"Unknown ({registers[129]})")

        return True
