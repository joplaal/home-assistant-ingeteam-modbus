"""The Ingeteam Modbus Integration."""
import asyncio
import logging
import threading
import time
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

# Pre-import platforms to avoid blocking I/O in the event loop
from . import sensor
from . import select

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

PLATFORMS = ["sensor", "select"]


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
        self._slave_arg = None
        self._last_config_update = 0

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
            kwargs = {"address": address, "count": count}
            
            # If we already know the correct argument, use it
            if self._slave_arg:
                kwargs[self._slave_arg] = unit
                return self._client.read_input_registers(**kwargs)

            # Try pymodbus v3.10+ (device_id keyword)
            try:
                kwargs["device_id"] = unit
                result = self._client.read_input_registers(**kwargs)
                self._slave_arg = "device_id"
                return result
            except TypeError:
                kwargs.pop("device_id")

            # Try pymodbus v3.x (slave keyword)
            try:
                kwargs["slave"] = unit
                result = self._client.read_input_registers(**kwargs)
                self._slave_arg = "slave"
                return result
            except TypeError:
                kwargs.pop("slave")
            
            # Try pymodbus v2.x (unit keyword)
            try:
                kwargs["unit"] = unit
                result = self._client.read_input_registers(**kwargs)
                self._slave_arg = "unit"
                return result
            except TypeError:
                kwargs.pop("unit")

            _LOGGER.error("Could not read registers: pymodbus version incompatibility")
            raise ModbusException("Incompatible pymodbus version")

    def read_holding_registers(self, unit, address, count):
        """Read holding registers."""
        with self._lock:
            kwargs = {"address": address, "count": count}
            
            # If we already know the correct argument, use it
            if self._slave_arg:
                kwargs[self._slave_arg] = unit
                return self._client.read_holding_registers(**kwargs)

            # Try pymodbus v3.10+ (device_id keyword)
            try:
                kwargs["device_id"] = unit
                result = self._client.read_holding_registers(**kwargs)
                self._slave_arg = "device_id"
                return result
            except TypeError:
                kwargs.pop("device_id")

            # Try pymodbus v3.x (slave keyword)
            try:
                kwargs["slave"] = unit
                result = self._client.read_holding_registers(**kwargs)
                self._slave_arg = "slave"
                return result
            except TypeError:
                kwargs.pop("slave")
            
            # Try pymodbus v2.x (unit keyword)
            try:
                kwargs["unit"] = unit
                result = self._client.read_holding_registers(**kwargs)
                self._slave_arg = "unit"
                return result
            except TypeError:
                kwargs.pop("unit")

            _LOGGER.error("Could not read registers: pymodbus version incompatibility")
            raise ModbusException("Incompatible pymodbus version")

    def write_register(self, unit, address, value):
        """Write a single holding register."""
        with self._lock:
            kwargs = {"address": address, "value": value}
            
            # If we already know the correct argument, use it
            if self._slave_arg:
                kwargs[self._slave_arg] = unit
                return self._client.write_register(**kwargs)

            # Try pymodbus v3.10+ (device_id keyword)
            try:
                kwargs["device_id"] = unit
                result = self._client.write_register(**kwargs)
                self._slave_arg = "device_id"
                return result
            except TypeError:
                kwargs.pop("device_id")

            # Try pymodbus v3.x (slave keyword)
            try:
                kwargs["slave"] = unit
                result = self._client.write_register(**kwargs)
                self._slave_arg = "slave"
                return result
            except TypeError:
                kwargs.pop("slave")
            
            # Try pymodbus v2.x (unit keyword)
            try:
                kwargs["unit"] = unit
                result = self._client.write_register(**kwargs)
                self._slave_arg = "unit"
                return result
            except TypeError:
                kwargs.pop("unit")

            _LOGGER.error("Could not write register: pymodbus version incompatibility")
            raise ModbusException("Incompatible pymodbus version")

    async def set_schedule_type(self, schedule_index, value):
        """Set the schedule type (0=Disabled, 1=All Week, 2=Weekdays, 3=Weekend)."""
        def _write_modbus():
            # 1. Read current value of Register 25
            rr = self.read_holding_registers(unit=self._address, address=25, count=1)
            if rr.isError():
                _LOGGER.error("Error reading register 25 for update: %s", rr)
                return False
            
            current_val = rr.registers[0]
            
            # 2. Calculate new value
            # Bits 4-5: Sch1, Bits 6-7: Sch2
            sch1_current = (current_val >> 4) & 0x03
            sch2_current = (current_val >> 6) & 0x03
            
            if schedule_index == 1:
                target_sch1 = value
                target_sch2 = sch2_current
            else:
                target_sch1 = sch1_current
                target_sch2 = value
            
            # Bit 0 is always 1 (Enable AC Charging global?)
            new_val = 1 | (target_sch1 << 4) | (target_sch2 << 6)
            
            if new_val == current_val:
                return True
                
            # 3. Write new value
            wr = self.write_register(unit=self._address, address=25, value=new_val)
            if wr.isError():
                _LOGGER.error("Error writing register 25: %s", wr)
                return False
                
            # Force a config refresh on next cycle
            self._last_config_update = 0
            return True

        await self._hass.async_add_executor_job(_write_modbus)

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

        # Chunk 3: 1000-1060 (PV Data for Hybrid 3Play)
        req3 = self.read_input_registers(unit=self._address, address=1000, count=60)
        if req3.isError():
             _LOGGER.error("Error reading modbus registers (1000-1060): %s", req3)
             # Don't fail completely, just use zeros
             regs_1000 = [0] * 60
        else:
             regs_1000 = req3.registers

        # Chunk 4: Holding Registers 0-50 (Configuration)
        # Read only every 60 seconds to avoid overloading the inverter
        holding_regs = None
        now = time.time()
        if now - self._last_config_update > 60:
            req4 = self.read_holding_registers(unit=self._address, address=0, count=50)
            if req4.isError():
                _LOGGER.error("Error reading holding registers (0-50): %s", req4)
                # holding_regs remains None, so we skip processing
            else:
                holding_regs = req4.registers
                self._last_config_update = now

        registers = req1.registers + req2.registers + regs_1000
        
        if len(registers) < 130:
             _LOGGER.warning("Incomplete Modbus response, expected at least 130 registers but got %s", len(registers))
             return False

        # Helper to get 1000-range values safely
        def get_1000(offset):
            idx = 130 + offset
            if idx < len(registers):
                return registers[idx]
            return 0
            
        # Helper to get Holding Registers safely
        def get_holding(offset):
            if holding_regs and offset < len(holding_regs):
                return holding_regs[offset]
            return 0
            
        # Helper to decode packed time (HHMM in hex)
        def decode_time(val):
            # Val is like 2048 (0x0800) -> 08:00
            # Val is like 0 (0x0000) -> 00:00
            hour = (val >> 8) & 0xFF
            minute = val & 0xFF
            return f"{hour:02d}:{minute:02d}"

        # --- 3Play Hybrid Mapping ---
        
        # System Status
        self.data["rms_diff_current"] = registers[1] / 1.0
        self.data["total_hours"] = self._u32_from_words_le(registers, 6)
        self.data["alarm_code"] = self._u32_from_words_le(registers, 10)
        
        # Battery
        self.data["battery_voltage"] = registers[16] / 10.0
        self.data["battery_voltage_internal"] = registers[17] / 10.0
        
        # Battery Power Logic
        # Reg 21 (Power) can be inconsistent or lower than expected.
        # We calculate Power as Voltage (Reg 16) * Current (Reg 19) for better accuracy.
        # Reg 19 > 0: Discharging
        # Reg 19 < 0: Charging
        
        raw_power_21 = self._decode_signed(registers[21]) / 10.0
        self.data["battery_current"] = self._decode_signed(registers[19]) / 100.0
        
        # Calculate power from V * I
        calculated_power = (self.data["battery_voltage"] * self.data["battery_current"])
        
        # Deadband / Zero Override
        # 1. If the inverter reports 0W (Reg 21), trust it (matches official panel).
        # 2. If current is very low (< 0.5A ~ 200W), treat as phantom load.
        if raw_power_21 == 0 or abs(self.data["battery_current"]) < 0.5:
            calculated_power = 0.0
            self.data["battery_current"] = 0.0
        
        if self.data["battery_current"] > 0:
            # Discharging
            self.data["battery_power"] = abs(calculated_power)
            self.data["battery_discharging_power"] = abs(calculated_power)
            self.data["battery_charging_power"] = 0.0
        elif self.data["battery_current"] < 0:
            # Charging
            self.data["battery_power"] = -abs(calculated_power)
            self.data["battery_discharging_power"] = 0.0
            self.data["battery_charging_power"] = abs(calculated_power)
        else:
            # Standby or 0 current
            self.data["battery_power"] = 0.0
            self.data["battery_discharging_power"] = 0.0
            self.data["battery_charging_power"] = 0.0
        
        self.data["battery_status"] = BATTERY_STATUS.get(registers[30], f"Unknown ({registers[30]})")
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
        # Updated mapping for Hybrid 3Play using 1000-range and 0-100 range
        # Analysis of values shows:
        # Reg 1047: PV1 Power (x10) -> Incorrect, using Reg 80 (x1)
        # Reg 1051: PV2 Power (x10) -> Incorrect, using Reg 120 (x0.01)
        # Reg 28: PV1 Voltage (x10) -> Incorrect?
        # Reg 42: PV2 Voltage (x10) -> Incorrect, using Reg 1027 (x10)
        
        # PV1
        # self.data["pv1_power"] = get_1000(47) / 10.0
        self.data["pv1_power"] = registers[41] / 10.0
        self.data["pv1_voltage"] = registers[38] / 10.0
        
        if self.data["pv1_voltage"] > 0:
            self.data["pv1_current"] = self.data["pv1_power"] / self.data["pv1_voltage"]
        else:
            self.data["pv1_current"] = 0.0
        
        # PV2
        # self.data["pv2_power"] = get_1000(51) / 10.0
        self.data["pv2_power"] = registers[45] / 10.0
        self.data["pv2_voltage"] = registers[42] / 10.0
        # self.data["pv2_voltage"] = get_1000(27) / 10.0
        
        if self.data["pv2_voltage"] > 0:
            self.data["pv2_current"] = self.data["pv2_power"] / self.data["pv2_voltage"]
        else:
            self.data["pv2_current"] = 0.0
            
        # Total PV Power (Calculated from PV1 + PV2)
        self.data["pv_total_power"] = self.data["pv1_power"] + self.data["pv2_power"]
        
        # Legacy Totals
        self.data["p_total"] = registers[65] / 1.0 # Reg 65 is Total Loads/Power
        self.data["active_power"] = self.data["p_total"] # Alias
        self.data["q_total"] = self._decode_signed(registers[39]) / 1.0
        self.data["reactive_power"] = self.data["q_total"] # Alias
        self.data["power_factor"] = self._decode_signed(registers[40]) / 1000.0
        self.data["dc_bus_voltage"] = registers[41] / 1.0
        
        # Critical Loads (AC Output)
        self.data["cl_current_l1"] = registers[49] / 100.0
        self.data["ac_l1_current"] = self.data["cl_current_l1"] # Alias
        self.data["cl_active_power_l1"] = registers[51] / 10.0
        self.data["ac_l1_power"] = self.data["cl_active_power_l1"] # Alias
        
        self.data["cl_current_l2"] = registers[53] / 100.0
        self.data["ac_l2_current"] = self.data["cl_current_l2"] # Alias
        self.data["cl_active_power_l2"] = registers[55] / 10.0
        self.data["ac_l2_power"] = self.data["cl_active_power_l2"] # Alias
        
        self.data["cl_current_l3"] = registers[57] / 100.0
        self.data["ac_l3_current"] = self.data["cl_current_l3"] # Alias
        self.data["cl_active_power_l3"] = registers[59] / 10.0
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
        self.data["im_active_power_l2"] = self._decode_signed(registers[87]) / 10.0
        self.data["im_reactive_power_l2"] = self._decode_signed(registers[88]) / 10.0
        self.data["im_active_power_l3"] = self._decode_signed(registers[91]) / 10.0
        self.data["im_reactive_power_l3"] = self._decode_signed(registers[92]) / 10.0
        
        self.data["im_power_factor"] = self._decode_signed(registers[89]) / 1000.0
        
        # External Meter
        # Mapped based on manual correlation:
        # L1 (811 W) -> Reg 91 (815)
        # L2 (4804 W) -> Reg 95 (4799)
        # L3 (689 W) -> Reg 99 (690)
        self.data["em_active_power_l1"] = self._decode_signed(registers[91]) / 1.0
        self.data["em_reactive_power_l1"] = self._decode_signed(registers[92]) / 1.0
        self.data["em_active_power_l2"] = self._decode_signed(registers[95]) / 1.0
        self.data["em_reactive_power_l2"] = self._decode_signed(registers[96]) / 1.0
        self.data["em_active_power_l3"] = self._decode_signed(registers[99]) / 1.0
        self.data["em_reactive_power_l3"] = self._decode_signed(registers[100]) / 1.0
        
        self.data["em_voltage"] = registers[102] / 1.0
        self.data["em_freq"] = registers[103] / 10.0
        self.data["ev_power"] = self._decode_signed(registers[104]) / 1.0
        
        # Reg 105 is Energy (Accumulated), not Power. Removing it from Power sensor to avoid spikes.
        # self.data["em_active_power_returned"] = self._decode_signed(registers[105]) / 1.0
        self.data["em_active_power_returned"] = 0.0
        
        self.data["do_1_status"] = registers[106]
        self.data["do_2_status"] = registers[108]
        self.data["di_drm_status"] = registers[110]
        # self.data["di_2_status"] = registers[111] # Values 11/12 do not match boolean status
        # self.data["di_3_status"] = registers[112] # Value 37 does not match boolean status
        
        # New Mappings from Hunt - INCORRECT (Regs 0-5 are Date/Time)
        # self.data["battery_charge_limitation_reason"] = registers[2] # Day
        # self.data["battery_bms_warnings"] = registers[4] # Minute
        # self.data["battery_bms_errors"] = registers[5] # Second
        # self.data["ap_reduction_ratio"] = registers[14]
        # self.data["ap_reduction_reason"] = registers[15]
        # self.data["waiting_time"] = registers[120] # Value 21634 too high for seconds
        
        self.data["temp_mod_1"] = self._decode_signed(registers[125]) / 1.0
        self.data["temp_mod_2"] = self._decode_signed(registers[126]) / 1.0
        # self.data["temp_pcb"] = self._decode_signed(registers[127]) / 1.0
        self.data["temp_pcb"] = self._decode_signed(registers[112]) / 1.0
        
        # Inverter Status
        # Reg 129 seems to be a bitmask or internal state (values 16, 21, 41, 43 seen).
        # Reg 1007 (index 137) seems to be the standard status code (3 = On-grid).
        # registers list structure: 0-99 (0-99), 100-129 (100-129), 1000-1059 (130-189)
        
        status_reg_1007 = registers[137] if len(registers) > 137 else 0
        
        self.data["inverter_state"] = status_reg_1007
        self.data["status"] = INVERTER_STATUS.get(status_reg_1007, f"Unknown ({status_reg_1007})")

        # --- Configuration (Holding Registers) ---
        if holding_regs:
            # SOC Settings
            self.data["config_soc_max"] = get_holding(14)
            self.data["config_soc_min"] = get_holding(28)
            self.data["config_soc_recovery"] = get_holding(27)
            self.data["config_soc_recx"] = get_holding(29)
            self.data["config_soc_descx"] = get_holding(30)
            
            # AC Charging Settings
            self.data["config_soc_ac_charging_power"] = get_holding(23)
            
            # Schedule Decoding from Register 25
            # Bits 4-5: Schedule 1 Type
            # Bits 6-7: Schedule 2 Type
            reg_25 = get_holding(25)
            sch1_type = (reg_25 >> 4) & 0x03
            sch2_type = (reg_25 >> 6) & 0x03
            
            SCHEDULE_TYPES = {
                0: "Desactivado",
                1: "Toda la semana",
                2: "Entre semana (L-V)",
                3: "Fin de semana (S-D)"
            }
            
            # Schedule 1
            self.data["config_soc_ac_charging_schedule1_type"] = SCHEDULE_TYPES.get(sch1_type, f"Desconocido ({sch1_type})")
            self.data["config_soc_ac_charging_soc_grid1"] = get_holding(32)
            self.data["config_soc_ac_charging_time_start1"] = decode_time(get_holding(33))
            self.data["config_soc_ac_charging_time_end1"] = decode_time(get_holding(34))
            
            # Schedule 2
            self.data["config_soc_ac_charging_schedule2_type"] = SCHEDULE_TYPES.get(sch2_type, f"Desconocido ({sch2_type})")
            self.data["config_soc_ac_charging_soc_grid2"] = get_holding(35)
            self.data["config_soc_ac_charging_time_start2"] = decode_time(get_holding(36))
            self.data["config_soc_ac_charging_time_end2"] = decode_time(get_holding(37))

        # --- Calculated Values ---
        
        # Critical Loads Aggregates
        self.data["cl_active_power"] = (
            self.data.get("cl_active_power_l1", 0) + 
            self.data.get("cl_active_power_l2", 0) + 
            self.data.get("cl_active_power_l3", 0)
        )
        self.data["cl_reactive_power"] = (
            self.data.get("cl_reactive_power_l1", 0) + 
            self.data.get("cl_reactive_power_l2", 0) + 
            self.data.get("cl_reactive_power_l3", 0)
        )
        self.data["cl_voltage"] = self.data.get("cl_voltage_l1", 0) # Proxy using L1
        self.data["cl_current"] = (
            self.data.get("cl_current_l1", 0) + 
            self.data.get("cl_current_l2", 0) + 
            self.data.get("cl_current_l3", 0)
        )

        # Internal Meter Aggregates
        self.data["im_active_power"] = (
            self.data.get("im_active_power_l1", 0) + 
            self.data.get("im_active_power_l2", 0) + 
            self.data.get("im_active_power_l3", 0)
        )
        self.data["im_reactive_power"] = (
            self.data.get("im_reactive_power_l1", 0) + 
            self.data.get("im_reactive_power_l2", 0) + 
            self.data.get("im_reactive_power_l3", 0)
        )
        self.data["im_current"] = (
            self.data.get("im_current_l1", 0) + 
            self.data.get("im_current_l2", 0) + 
            self.data.get("im_current_l3", 0)
        )

        # External Meter Aggregates
        self.data["em_active_power"] = (
            self.data.get("em_active_power_l1", 0) + 
            self.data.get("em_active_power_l2", 0) + 
            self.data.get("em_active_power_l3", 0)
        )
        self.data["em_reactive_power"] = (
            self.data.get("em_reactive_power_l1", 0) + 
            self.data.get("em_reactive_power_l2", 0) + 
            self.data.get("em_reactive_power_l3", 0)
        )
        
        # PV Aggregates
        self.data["pv_internal_total_power"] = self.data.get("pv_total_power", 0)
        self.data["external_pv_power"] = 0 # Placeholder as no register is defined yet
        # self.data["pv_total_power"] is already set from Reg 1001

        # Grid Balance
        # Calculated from signed External Meter registers (Positive = Import, Negative = Export)
        
        grid_p_l1 = self.data.get("em_active_power_l1", 0)
        grid_p_l2 = self.data.get("em_active_power_l2", 0)
        grid_p_l3 = self.data.get("em_active_power_l3", 0)
        
        self.data["grid_balance"] = grid_p_l1 + grid_p_l2 + grid_p_l3

        # Inverter Generation (Calculated)
        # Reg 38 (active_power) is unreliable/unknown.
        # We calculate Inverter Output from DC Input (PV + Battery)
        # Assuming ~96% efficiency or just reporting DC power as AC power for simplicity
        p_pv = self.data.get("pv_total_power", 0)
        p_bat_dis = self.data.get("battery_discharging_power", 0)
        p_bat_chg = self.data.get("battery_charging_power", 0)
        
        p_dc_in = p_pv + p_bat_dis - p_bat_chg
        
        # Estimate AC Output
        self.data["inverter_active_power"] = p_dc_in # * 0.96
        
        # System Efficiency (Solar Coverage Ratio)
        # Calculates system self-sufficiency. Can exceed 100% if generating more than consuming (charging/exporting).
        # Formula: (PV Production + Battery Discharge) / Total Loads * 100
        pv_power = self.data.get("pv_total_power", 0)
        bat_discharge = self.data.get("battery_discharging_power", 0)
        loads_power = self.data.get("total_loads_power", 0)
        
        if loads_power > 0:
            ratio = ((pv_power + bat_discharge) / loads_power) * 100.0
            self.data["system_efficiency"] = ratio
        else:
            self.data["system_efficiency"] = 0.0

        return True
