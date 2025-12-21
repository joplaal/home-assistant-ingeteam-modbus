import logging
from datetime import datetime, UTC, timedelta
from typing import Optional, Dict, Any, List
from decimal import Decimal
from .const import (
    DOMAIN,
    ATTR_MANUFACTURER,
    REGISTER_MAPS,
    # Status constants
    INVERTER_STATUS,
    BATTERY_STATUS,
    BATTERY_BMS_ALARMS,
    BATTERY_LIMITATION_REASONS,
    AP_REDUCTION_REASONS,
    BOOLEAN_STATUS,
    # Legacy types for backward compatibility
    INVERTER_STATUS_TYPES,
    INVERTER_SENSOR_TYPES,
    METER_SENSOR_TYPES,
    PV_FIELD_SENSOR_TYPES,
    BATTERY_SENSOR_TYPES,
)
from .model_map import Register
from homeassistant.const import (
    CONF_NAME,
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfPower,
    UnitOfEnergy,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfFrequency,
)

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
    SensorDeviceClass
)
from homeassistant.components.integration.sensor import (
    IntegrationSensor, 
    ATTR_SOURCE_ID, 
    UNIT_PREFIXES, 
    UNIT_TIME, 
    _IntegrationMethod,
    _IntegrationTrigger
)

from homeassistant.components.integration.const import METHOD_TRAPEZOIDAL

from homeassistant.core import callback, CALLBACK_TYPE

_LOGGER = logging.getLogger(__name__)


def create_sensor_description(register: Register) -> SensorEntityDescription:
    """Create a SensorEntityDescription from a Register."""
    device_class = None
    native_unit = register.unit
    state_class = SensorStateClass.MEASUREMENT
    
    # Map units to device classes
    if register.unit == "V":
        device_class = SensorDeviceClass.VOLTAGE
        native_unit = UnitOfElectricPotential.VOLT
    elif register.unit == "A":
        device_class = SensorDeviceClass.CURRENT
        native_unit = UnitOfElectricCurrent.AMPERE
    elif register.unit == "W":
        device_class = SensorDeviceClass.POWER
        native_unit = UnitOfPower.WATT
    elif register.unit == "Wh":
        device_class = SensorDeviceClass.ENERGY
        native_unit = UnitOfEnergy.WATT_HOUR
        state_class = SensorStateClass.TOTAL_INCREASING
    elif register.unit == "kWh":
        device_class = SensorDeviceClass.ENERGY
        native_unit = UnitOfEnergy.KILO_WATT_HOUR
        state_class = SensorStateClass.TOTAL_INCREASING
    elif register.unit == "var":
        device_class = SensorDeviceClass.REACTIVE_POWER
        native_unit = "var"
    elif register.unit == "%":
        native_unit = PERCENTAGE
        if "soc" in register.name.lower() or "battery" in register.name.lower():
            device_class = SensorDeviceClass.BATTERY
    elif register.unit == "°C":
        device_class = SensorDeviceClass.TEMPERATURE
        native_unit = UnitOfTemperature.CELSIUS
    elif register.unit == "Hz":
        device_class = SensorDeviceClass.FREQUENCY
        native_unit = UnitOfFrequency.HERTZ
    elif register.unit is None and ("state" in register.name.lower() or 
                                   "status" in register.name.lower() or
                                   "alarm" in register.name.lower()):
        device_class = SensorDeviceClass.ENUM
        state_class = None
    else:
        # No specific device class, use generic measurement
        state_class = SensorStateClass.MEASUREMENT
    
    return SensorEntityDescription(
        key=register.name,
        name=register.description or register.name.replace("_", " ").title(),
        native_unit_of_measurement=native_unit,
        device_class=device_class,
        state_class=state_class,
    )


async def async_setup_entry(hass, entry, async_add_entities):
    hub_name = entry.data[CONF_NAME]
    hub = hass.data[DOMAIN][hub_name]["hub"]

    device_info = {
        "identifiers": {(DOMAIN, hub_name)},
        "name": hub_name,
        "manufacturer": ATTR_MANUFACTURER,
    }

    entities = []
    
    # Get the register map from the hub
    register_map = getattr(hub, 'register_map', None)
    
    if register_map:
        # New approach: create sensors from register map
        for register in register_map.registers.values():
            sensor = IngeteamModernSensor(
                hub_name=hub_name,
                hub=hub,
                device_info=device_info,
                register=register,
            )
            entities.append(sensor)
            
        # Add calculated total sensors for 3Play systems
        if "3play" in register_map.name.lower():
            calculated_totals = [
                ("PV Internal Total Power", "pv_internal_total_power", "W", "mdi:solar-power"),
                ("PV Total Power", "pv_total_power", "W", "mdi:solar-power"),
                ("System Efficiency", "system_efficiency", "%", "mdi:percent"),
                ("Grid Power Balance", "grid_balance", "W", "mdi:transmission-tower"),
            ]
            
            for sensor_name, sensor_key, unit, icon in calculated_totals:
                sensor = CalculatedTotalSensor(
                    hub_name=hub_name,
                    hub=hub,
                    device_info=device_info,
                    sensor_name=sensor_name,
                    sensor_key=sensor_key,
                    unit=unit,
                    icon=icon,
                )
                entities.append(sensor)
    else:
        # Legacy approach: maintain backward compatibility
        _LOGGER.warning("Using legacy sensor setup - consider updating configuration")
        
        # Create legacy sensors
        for sensor_info in INVERTER_STATUS_TYPES.values():
            sensor = IngeteamSensor(
                hub_name,
                hub,
                device_info,
                sensor_info[0],
                sensor_info[1],
                sensor_info[2],
                sensor_info[3],
            )
            entities.append(sensor)
        
        for sensor_info in INVERTER_SENSOR_TYPES.values():
            # Handle calculated total sensors specially
            sensor_key = sensor_info[1]
            if sensor_key in ["system_efficiency", "grid_balance"]:
                sensor = CalculatedTotalSensor(
                    hub_name=hub_name,
                    hub=hub,
                    device_info=device_info,
                    sensor_name=sensor_info[0],
                    sensor_key=sensor_key,
                    unit=sensor_info[2],
                    icon=sensor_info[3] or "mdi:gauge",
                )
            elif len(sensor_info) > 4:
                sensor = CalculatedEnergySensor(
                    hub,
                    name=f'{hub_name} {sensor_info[0]}', 
                    source_entity=f'sensor.{hub_name}_{sensor_info[4]}',
                    unique_id=f'{hub_name}_{sensor_info[1]}',
                )
            else:  
                sensor = IngeteamSensor(
                    hub_name,
                    hub,
                    device_info,
                    sensor_info[0],
                    sensor_info[1],
                    sensor_info[2],
                    sensor_info[3],
                )
            entities.append(sensor)

        for sensor_info in PV_FIELD_SENSOR_TYPES.values():
            # Handle calculated total sensors specially
            sensor_key = sensor_info[1]
            if sensor_key in ["pv_internal_total_power", "pv_total_power", "system_efficiency", "grid_balance"]:
                sensor = CalculatedTotalSensor(
                    hub_name=hub_name,
                    hub=hub,
                    device_info=device_info,
                    sensor_name=sensor_info[0],
                    sensor_key=sensor_key,
                    unit=sensor_info[2],
                    icon=sensor_info[3] or "mdi:solar-power",
                )
            elif len(sensor_info) > 4:
                sensor = CalculatedEnergySensor(
                    hub,
                    name=f'{hub_name} {sensor_info[0]}', 
                    source_entity=f'sensor.{hub_name}_{sensor_info[4]}',
                    unique_id=f'{hub_name}_{sensor_info[1]}',
                )
            else:   
                sensor = IngeteamSensor(
                    hub_name,
                    hub,
                    device_info,
                    sensor_info[0],
                    sensor_info[1],
                    sensor_info[2],
                    sensor_info[3],
                )
            entities.append(sensor)

        if getattr(hub, 'read_meter', False):
            for sensor_info in METER_SENSOR_TYPES.values():
                if len(sensor_info) > 4:
                    sensor = CalculatedEnergySensor(
                        hub,
                        name=f'{hub_name} {sensor_info[0]}', 
                        source_entity=f'sensor.{hub_name}_{sensor_info[4]}',
                        unique_id=f'{hub_name}_{sensor_info[1]}',
                    )
                else:    
                    sensor = IngeteamSensor(
                        hub_name,
                        hub,
                        device_info,
                        sensor_info[0],
                        sensor_info[1],
                        sensor_info[2],
                        sensor_info[3],
                    )
                entities.append(sensor)

        if getattr(hub, 'read_battery', False):
            for sensor_info in BATTERY_SENSOR_TYPES.values():
                if len(sensor_info) > 4:
                    sensor = CalculatedEnergySensor(
                        hub,
                        name=f'{hub_name} {sensor_info[0]}', 
                        source_entity=f'sensor.{hub_name}_{sensor_info[4]}',
                        unique_id=f'{hub_name}_{sensor_info[1]}',
                    )
                else:    
                    sensor = IngeteamSensor(
                        hub_name,
                        hub,
                        device_info,
                        sensor_info[0],
                        sensor_info[1],
                        sensor_info[2],
                        sensor_info[3],
                    )
                entities.append(sensor)

    async_add_entities(entities)
    return True

_DESCRIPTIONS: dict[str, SensorEntityDescription] = {
    "A": SensorEntityDescription(
        key="A",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "V": SensorEntityDescription(
        key="V",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "W": SensorEntityDescription(
        key="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "Var": SensorEntityDescription(
        key="Var",
        device_class=SensorDeviceClass.REACTIVE_POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "B": SensorEntityDescription(
        key="B",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
    "C": SensorEntityDescription(
        key="C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    "Hz": SensorEntityDescription(
        key="Hz",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "%": SensorEntityDescription(
        key="%",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
}

DIAG_SENSOR = SensorEntityDescription(
    key="_",
    state_class=SensorStateClass.MEASUREMENT,
)

class CalculatedTotalSensor(SensorEntity):
    """Sensor for calculated totals (PV total, system efficiency, etc)."""

    def __init__(self, hub_name: str, hub, device_info: Dict[str, Any], 
                 sensor_name: str, sensor_key: str, unit: str, icon: str):
        """Initialize the calculated sensor."""
        self._hub_name = hub_name
        self._hub = hub
        self._device_info = device_info
        self._sensor_name = sensor_name
        self._sensor_key = sensor_key
        self._attr_unique_id = f"{hub_name}_{sensor_key}"
        self._attr_name = f"{hub_name} {sensor_name}"
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_state_class = SensorStateClass.MEASUREMENT
        if unit == "W":
            self._attr_device_class = SensorDeviceClass.POWER
        elif unit == "Wh":
            self._attr_device_class = SensorDeviceClass.ENERGY
        elif unit == "%":
            self._attr_device_class = SensorDeviceClass.POWER_FACTOR

    @property
    def device_info(self) -> Dict[str, Any]:
        return self._device_info

    @property
    def available(self) -> bool:
        return self._hub.online

    @property
    def native_value(self):
        """Return the calculated value."""
        try:
            if self._sensor_key == "pv_internal_total_power":
                # Sum PV1-4 power
                pv_total = 0
                for pv_num in [1, 2, 3, 4]:
                    pv_power = self._hub.get_register_value(f"pv{pv_num}_power")
                    if pv_power is not None:
                        pv_total += pv_power
                return pv_total if pv_total > 0 else None
                
            elif self._sensor_key == "pv_total_power":
                # Sum internal PV + external PV
                internal_total = 0
                for pv_num in [1, 2, 3, 4]:
                    pv_power = self._hub.get_register_value(f"pv{pv_num}_power")
                    if pv_power is not None:
                        internal_total += pv_power
                
                external_pv = self._hub.get_register_value("pv_external_power") or 0
                return internal_total + external_pv if (internal_total + external_pv) > 0 else None
                
            elif self._sensor_key == "system_efficiency":
                # Calculate efficiency: (AC output) / (PV input) * 100
                ac_power = self._hub.get_register_value("p_total") or self._hub.get_register_value("active_power")
                pv_total = 0
                for pv_num in [1, 2, 3, 4]:
                    pv_power = self._hub.get_register_value(f"pv{pv_num}_power")
                    if pv_power is not None:
                        pv_total += pv_power
                
                if pv_total > 0 and ac_power is not None:
                    efficiency = (abs(ac_power) / pv_total) * 100
                    return round(min(efficiency, 100), 1)  # Cap at 100%
                return None
                
            elif self._sensor_key == "grid_balance":
                # Grid balance: positive = consuming from grid, negative = injecting to grid
                grid_power = self._hub.get_register_value("grid_power")
                return grid_power
                
            return None
            
        except Exception as ex:
            _LOGGER.warning(f"Error calculating {self._sensor_key}: {ex}")
            return None


class CalculatedEnergySensor(IntegrationSensor):
    def __init__(
        self,
        *
        hub,
        integration_method = METHOD_TRAPEZOIDAL,
        name: str | None,
        source_entity: str,
        unique_id: str | None,
        max_sub_interval: timedelta | None = None,):
        """Initialize the integration sensor."""
        unit_prefix = "k"
        unit_time = "h"
        self._attr_unique_id = unique_id
        self._sensor_source_id = source_entity
        self._round_digits = 2
        self._state: Decimal | None = None
        self._last_valid_state = Decimal | None 
        self._method = _IntegrationMethod.from_name(integration_method)
        self._max_sub_interval: timedelta | None = (
            None  # disable time based integration
            if max_sub_interval is None or max_sub_interval.total_seconds() == 0
            else max_sub_interval
        )
        self._max_sub_interval_exceeded_callback: CALLBACK_TYPE = lambda *args: None
        self._last_integration_time: datetime = datetime.now(tz=UTC)
        self._last_integration_trigger = _IntegrationTrigger.StateEvent


        self._attr_name = name if name is not None else f"{source_entity} integral"
        self._unit_template = f"{'' if unit_prefix is None else unit_prefix}{{}}"
        self._unit_of_measurement: str | None = None
        self._unit_prefix = UNIT_PREFIXES[unit_prefix]
        self._unit_prefix_string = unit_prefix
        self._unit_time = UNIT_TIME[unit_time]
        self._unit_time_str = unit_time
        self._attr_icon = "mdi:chart-histogram"
        self._attr_extra_state_attributes = {ATTR_SOURCE_ID: source_entity}
        self._source_entity = source_entity
        self._hub = hub

    @property
    def hub(self):
        return self._hub
    
    @property
    def device_class(self):
        return SensorDeviceClass.ENERGY


class IngeteamModernSensor(SensorEntity):
    """Modern sensor implementation using Register definitions."""

    def __init__(self, hub_name: str, hub, device_info: Dict[str, Any], register: Register):
        """Initialize the sensor."""
        self._hub_name = hub_name
        self._hub = hub
        self._device_info = device_info
        self._register = register
        self._attr_unique_id = f"{hub_name}_{register.name}"
        self._attr_name = f"{hub_name} {register.description or register.name.replace('_', ' ').title()}"
        
        # Set entity description
        self.entity_description = create_sensor_description(register)
        
        # Override some attributes if needed
        self._attr_device_class = self.entity_description.device_class
        self._attr_state_class = self.entity_description.state_class
        self._attr_native_unit_of_measurement = self.entity_description.native_unit_of_measurement
        
        # Special handling for status/state sensors
        if register.unit is None and ("state" in register.name.lower() or 
                                     "status" in register.name.lower()):
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_state_class = None
            # Define options based on register name
            self._attr_options = self._get_status_options(register.name)

    def _get_status_options(self, register_name: str) -> Optional[List[str]]:
        """Get options for status/enum sensors."""
        if "inverter_state" in register_name or "status" in register_name:
            return list(INVERTER_STATUS.values())
        elif "bat_state" in register_name or "battery_status" in register_name:
            return list(BATTERY_STATUS.values())
        elif "bat_bms_alarm" in register_name:
            return list(BATTERY_BMS_ALARMS.values())
        elif "limitation" in register_name:
            return list(BATTERY_LIMITATION_REASONS.values())
        elif "reduction_reason" in register_name:
            return list(AP_REDUCTION_REASONS.values())
        return None

    async def async_added_to_hass(self):
        """Register callbacks."""
        self._hub.async_add_ingeteam_sensor(self._modbus_data_updated)

    async def async_will_remove_from_hass(self) -> None:
        self._hub.async_remove_ingeteam_sensor(self._modbus_data_updated)

    @callback
    def _modbus_data_updated(self):
        self.async_write_ha_state()

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self._register.name in self._hub.data:
            value = self._hub.data[self._register.name]
            
            # Special handling for status/enum values
            if self._attr_device_class == SensorDeviceClass.ENUM:
                if "inverter_state" in self._register.name:
                    return INVERTER_STATUS.get(value, f"Unknown ({value})")
                elif "bat_state" in self._register.name:
                    return BATTERY_STATUS.get(value, f"Unknown ({value})")
                elif "bat_bms_alarm" in self._register.name:
                    return BATTERY_BMS_ALARMS.get(value, f"Unknown ({value})")
                elif "limitation" in self._register.name:
                    return BATTERY_LIMITATION_REASONS.get(value, f"Unknown ({value})")
                elif "reduction_reason" in self._register.name:
                    return AP_REDUCTION_REASONS.get(value, f"Unknown ({value})")
                elif "do_" in self._register.name or "di_" in self._register.name:
                    return BOOLEAN_STATUS.get(value, f"Unknown ({value})")
            
            return value
        return None

    @property
    def should_poll(self) -> bool:
        """Data is delivered by the hub"""
        return False

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        return self._device_info

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._register.name in self._hub.data


class IngeteamSensor(SensorEntity):
    """Representation of an Ingeteam Modbus sensor."""

    def __init__(self, platform_name, hub, device_info, name, key, unit, icon):
        """Initialize the sensor."""
        self._platform_name = platform_name
        self._hub = hub
        self._key = key
        self._name = name
        self._unit_of_measurement = unit if unit != "B" else "%"
        self._icon = icon
        self._device_info = device_info
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self.entity_description = _DESCRIPTIONS.get(unit, DIAG_SENSOR)

    async def async_added_to_hass(self):
        """Register callbacks."""
        self._hub.async_add_ingeteam_sensor(self._modbus_data_updated)

    async def async_will_remove_from_hass(self) -> None:
        self._hub.async_remove_ingeteam_sensor(self._modbus_data_updated)

    @callback
    def _modbus_data_updated(self):
        self.async_write_ha_state()

    @callback
    def _update_state(self):
        if self._key in self._hub.data:
            self._state = self._hub.data[self._key]

    @property
    def name(self):
        """Return the name."""
        return f"{self._platform_name} {self._name}"

    @property
    def unique_id(self) -> Optional[str]:
        return f"{self._platform_name}_{self._key}"

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Return the sensor icon."""
        return self._icon

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._key in self._hub.data:
            return self._hub.data[self._key]

    @property
    def should_poll(self) -> bool:
        """Data is delivered by the hub"""
        return False

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        return self._device_info
