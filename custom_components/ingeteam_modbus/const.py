from .model_map import R, RegisterMap

DOMAIN = "ingeteam_modbus"
DEFAULT_NAME = "ingeteam"
DEFAULT_SCAN_INTERVAL = 5
DEFAULT_PORT = 502
DEFAULT_MODBUS_ADDRESS = 1
DEFAULT_READ_METER = False
DEFAULT_READ_BATTERY = False
CONF_INGETEAM_HUB = "ingeteam_hub"
ATTR_STATUS_DESCRIPTION = "status_description"
ATTR_MANUFACTURER = "Ingeteam"
CONF_MODBUS_ADDRESS = "modbus_address"
CONF_READ_METER = "read_meter"
CONF_READ_BATTERY = "read_battery"
CONF_MODEL = "model"
CONF_TABLE = "table"
DEFAULT_MODEL = "auto"
DEFAULT_TABLE = "auto"

# =========================================
# REGISTER MAPS FOR DIFFERENT MODELS
# =========================================

# 1Play simplified register map (for backward compatibility)
INGE_1P_INPUT = [
    # Basic 1Play registers - keep original layout for compatibility
    R("active_power", 37, "int16", 1.0, "W", signed=True, description="Active Power"),
    R("reactive_power", 38, "int16", 1.0, "var", signed=True, description="Reactive Power"),
    R("power_factor", 39, "int16", 0.001, None, signed=True, description="Power Factor"),
    R("dc_bus_voltage", 54, "uint16", 1.0, "V", description="DC Bus Voltage"),
    R("temp_mod_1", 55, "int16", 0.1, "°C", signed=True, description="Temperature Module 1"),
    R("temp_mod_2", 56, "int16", 0.1, "°C", signed=True, description="Temperature Module 2"),
    R("temp_pcb", 57, "int16", 0.1, "°C", signed=True, description="Internal Temperature"),
    
    # Basic PV data
    R("pv1_voltage", 31, "uint16", 1.0, "V", description="PV1 Voltage"),
    R("pv1_current", 32, "uint16", 0.01, "A", description="PV1 Current"),
    R("pv1_power", 33, "uint16", 1.0, "W", description="PV1 Power"),
    R("pv2_voltage", 34, "uint16", 1.0, "V", description="PV2 Voltage"),
    R("pv2_current", 35, "uint16", 0.01, "A", description="PV2 Current"),
    R("pv2_power", 36, "uint16", 1.0, "W", description="PV2 Power"),
]

# 3Play Low Address (Hybrid) Map
# For 3Play devices that map 3-phase data to low registers (0-200)
INGE_3P = [
    # System Status
    R("rms_diff_current", 1, "uint16", 1.0, "mA", description="RMS Differential Current"),
    
    # Power (Inverter Output)
    R("active_power", 38, "int16", 1.0, "W", signed=True, description="Active Power"),
    
    # Battery Data
    R("battery_voltage", 16, "uint16", 0.1, "V", description="Battery Voltage"),
    R("battery_voltage_internal", 17, "uint16", 0.1, "V", description="Battery Voltage Internal"),
    R("battery_current", 19, "int16", 0.01, "A", signed=True, description="Battery Current"),
    R("battery_state_of_charge", 22, "uint16", 1.0, "%", description="Battery State of Charge"),
    R("battery_state_of_health", 23, "uint16", 1.0, "%", description="Battery State of Health"),
    R("battery_charging_current_max", 24, "uint16", 0.01, "A", description="Max Charging Current"),
    R("battery_charging_voltage", 28, "uint16", 0.1, "V", description="Battery Charging Voltage"),
    R("battery_discharging_voltage", 29, "uint16", 0.1, "V", description="Battery Discharging Voltage"),
    R("battery_temp", 31, "int16", 0.1, "°C", signed=True, description="Battery Temperature"),
    
    # PV Power
    R("pv1_voltage", 32, "uint16", 1.0, "V", description="PV1 Voltage"),
    R("pv1_current", 33, "uint16", 0.01, "A", description="PV1 Current"),
    R("pv1_power", 34, "uint16", 1.0, "W", description="PV1 Power"),
    
    R("pv2_voltage", 35, "uint16", 1.0, "V", description="PV2 Voltage"),
    R("pv2_current", 36, "uint16", 0.01, "A", description="PV2 Current"),
    R("pv2_power", 37, "uint16", 1.0, "W", description="PV2 Power"),
    
    # 3-Phase Voltages (Internal Meter)
    R("ac_l1_voltage", 60, "uint16", 0.1, "V", description="L1 Voltage"),
    R("ac_l2_voltage", 61, "uint16", 0.1, "V", description="L2 Voltage"),
    R("ac_l3_voltage", 62, "uint16", 0.1, "V", description="L3 Voltage"),
    
    # Frequency
    R("ac_freq", 63, "uint16", 0.01, "Hz", description="AC Frequency"),
    
    # Total Loads
    R("total_loads_power", 65, "uint16", 1.0, "W", description="Total Loads Power"),
    R("ev_power", 66, "int16", 1.0, "W", signed=True, description="EV Power"),
    
    # 3-Phase Currents (Internal Meter)
    R("ac_l1_current", 76, "uint16", 0.01, "A", description="L1 Current"),
    R("ac_l2_current", 78, "uint16", 0.01, "A", description="L2 Current"),
    R("ac_l3_current", 80, "uint16", 0.01, "A", description="L3 Current"),
    
    # Internal Grid Meter Powers
    R("im_active_power_l1", 83, "int16", 0.1, "W", signed=True, description="Internal Meter Power L1"),
    R("im_active_power_l2", 85, "int16", 0.1, "W", signed=True, description="Internal Meter Power L2"),
    R("im_active_power_l3", 87, "int16", 0.1, "W", signed=True, description="Internal Meter Power L3"),
    
    # External Grid Meter Powers
    R("em_active_power_l1", 91, "int16", 1.0, "W", signed=True, description="External Meter Power L1"),
    R("em_active_power_l2", 95, "int16", 1.0, "W", signed=True, description="External Meter Power L2"),
    R("em_active_power_l3", 99, "int16", 1.0, "W", signed=True, description="External Meter Power L3"),
    
    # Status & Alarms
    R("inverter_state", 129, "uint16", 1.0, None, description="Inverter State"),
    R("total_hours", 105, "uint16", 1.0, "h", description="Total Operating Hours"),
    R("alarm_code", 100, "uint32", 1.0, None, description="Alarm Code"),
    
    # Digital I/O
    R("do_1_status", 113, "uint16", 1.0, None, description="Digital Output 1 Status"),
    R("do_2_status", 114, "uint16", 1.0, None, description="Digital Output 2 Status"),
    R("di_drm_status", 115, "uint16", 1.0, None, description="Digital Input DRM0 Status"),
    R("di_2_status", 116, "uint16", 1.0, None, description="Digital Input 2 Status"),
    R("di_3_status", 117, "uint16", 1.0, None, description="Digital Input 3 Status"),
    
    # Critical Loads (Backup)
    R("cl_current_l1", 49, "uint16", 0.01, "A", description="Critical Loads Current L1"),
    R("cl_active_power_l1", 51, "int16", 0.1, "W", signed=True, description="Critical Loads Power L1"),
    
    R("cl_current_l2", 53, "uint16", 0.01, "A", description="Critical Loads Current L2"),
    R("cl_active_power_l2", 55, "int16", 0.1, "W", signed=True, description="Critical Loads Power L2"),
    
    R("cl_current_l3", 57, "uint16", 0.01, "A", description="Critical Loads Current L3"),
    R("cl_active_power_l3", 59, "int16", 0.1, "W", signed=True, description="Critical Loads Power L3"),
]

# Create register maps
REGISTER_MAPS = {
    "1play": RegisterMap("1play", INGE_1P_INPUT),
    "3play": RegisterMap("3play", INGE_3P),
}

# Legacy sensor type definitions (for backward compatibility)
INVERTER_STATUS_TYPES = {
    "Stop_Event": ["Stop event code", "stop_code", None, None],
    "Alarms": ["Alarm code", "alarm_code", None, None],
    "Status": ["Status", "status", None, None],
    "Waiting_Time": ["Waiting Time to Connect to Grid", "waiting_time", "s", None],
}

INVERTER_SENSOR_TYPES = {
    # Potencias básicas (disponibles en ambos 1Play y 3Play)
    "Active_Power": ["Active Power", "active_power", "W", None],
    "Active_Energy": ["Active Energy", "active_energy", "Wh", None, "active_power"],
    "Reactive_Power": ["Reactive Power", "reactive_power", "W", None],
    "Power_factor": ["Power factor Cosφ", "power_factor", None, None],
    
    # 3Play AC trifásica (solo disponible en 3Play Holding)
    "AC_L1_Voltage": ["L1 AC Voltage", "ac_l1_voltage", "V", None],
    "AC_L1_Current": ["L1 AC Current", "ac_l1_current", "A", "mdi:current-ac"],
    "AC_L1_Power": ["L1 AC Power", "ac_l1_power", "W", None],
    "AC_L1_Freq": ["L1 Frequency", "ac_l1_freq", "Hz", None],
    "AC_L2_Voltage": ["L2 AC Voltage", "ac_l2_voltage", "V", None],
    "AC_L2_Current": ["L2 AC Current", "ac_l2_current", "A", "mdi:current-ac"],
    "AC_L2_Power": ["L2 AC Power", "ac_l2_power", "W", None],
    "AC_L2_Freq": ["L2 Frequency", "ac_l2_freq", "Hz", None],
    "AC_L3_Voltage": ["L3 AC Voltage", "ac_l3_voltage", "V", None],
    "AC_L3_Current": ["L3 AC Current", "ac_l3_current", "A", "mdi:current-ac"],
    "AC_L3_Power": ["L3 AC Power", "ac_l3_power", "W", None],
    "AC_L3_Freq": ["L3 Frequency", "ac_l3_freq", "Hz", None],
    
    # Totales 3Play - registros directos
    "P_Total": ["Total Active Power", "p_total", "W", None],
    "Q_Total": ["Total Reactive Power", "q_total", "Var", None],
    "P_Total_Energy": ["Total Active Energy", "p_total_energy", "Wh", None, "p_total"],
    
    # Totales calculados útiles para overview del sistema
    "System_Efficiency": ["System Efficiency", "system_efficiency", "%", None],
    "Grid_Balance": ["Grid Power Balance", "grid_balance", "W", None],
    "Grid_Balance_Energy": ["Grid Balance Energy", "grid_balance_energy", "Wh", None, "grid_balance"],
    
    # Reducción de potencia (legacy - puede no estar disponible en 3Play)
    "Active_Power_Reduction_Ratio": ["Active Power Reduction Ratio", "ap_reduction_ratio", "%", None],
    "Active_Power_Reduction_Reason": ["Active Power Reduction Reason", "ap_reduction_reason", None, None],
    "Reactive_Power_Set-Point_Type": ["Reactive Power Set-Point Type", "reactive_setpoint_type", None, None],
    
    # Cargas críticas (nombres actualizados para 3Play)
    "CL_Voltage": ["Critical Loads Voltage", "crit_voltage", "V", None],
    "CL_Current": ["Critical Loads Current", "crit_current", "A", "mdi:current-ac"],
    "CL_Freq": ["Critical Loads Frequency", "crit_freq", "Hz", None],
    "CL_Active_Power": ["Critical Loads Active Power", "crit_power", "W", None],
    "CL_Active_Energy": ["Critical Loads Active Energy", "crit_active_energy", "Wh", None, "crit_power"],
    "CL_Reactive_Power": ["Critical Loads Reactive Power", "crit_q", "Var", None],
    
    # Critical Loads 3-Phase (New)
    "CL_Current_L1": ["Critical Loads Current L1", "crit_current_l1", "A", "mdi:current-ac"],
    "CL_Power_L1": ["Critical Loads Power L1", "crit_power_l1", "W", None],
    "CL_Current_L2": ["Critical Loads Current L2", "crit_current_l2", "A", "mdi:current-ac"],
    "CL_Power_L2": ["Critical Loads Power L2", "crit_power_l2", "W", None],
    "CL_Current_L3": ["Critical Loads Current L3", "crit_current_l3", "A", "mdi:current-ac"],
    "CL_Power_L3": ["Critical Loads Power L3", "crit_power_l3", "W", None],
    
    # Medidor interno (nombres actualizados para 3Play)
    "IM_Voltage": ["Internal Meter Voltage", "meter_voltage", "V", None],
    "IM_Current": ["Internal Meter Current", "meter_current", "A", "mdi:current-ac"],
    "IM_Freq": ["Internal Meter Frequency", "meter_freq", "Hz", None],
    "IM_Active_Power": ["Internal Active Power", "meter_power", "W", None],
    "IM_Active_Energy": ["Internal Active Energy", "meter_active_energy", "Wh", None, "meter_power"],
    "IM_Reactive_Power": ["Internal Reactive Power", "meter_q", "Var", None],
    "IM_Power_Factor": ["Internal Power Factor Cosφ", "meter_pf", None, None],
    
    # Internal Meter 3-Phase (New)
    "IM_Active_Power_L1": ["Internal Meter Active Power L1", "meter_power_l1", "W", None],
    "IM_Active_Power_L2": ["Internal Meter Active Power L2", "meter_power_l2", "W", None],
    "IM_Active_Power_L3": ["Internal Meter Active Power L3", "meter_power_l3", "W", None],
    
    # External Meter 3-Phase (New)
    "EM_Active_Power_L1": ["External Meter Active Power L1", "ext_meter_power_l1", "W", None],
    "EM_Active_Power_L2": ["External Meter Active Power L2", "ext_meter_power_l2", "W", None],
    "EM_Active_Power_L3": ["External Meter Active Power L3", "ext_meter_power_l3", "W", None],
    
    # Sistema
    "DC_Bus_Voltaje": ["DC Bus Voltage", "dc_bus_voltage", "V", None],
    "Temperature_Mod_1": ["Temperature Module 1", "temp_mod_1", "°C", None],
    "Temperature_Mod_2": ["Temperature Module 2", "temp_mod_2", "°C", None],
    "Internal_Temperature": ["Internal Temperature", "temp_pcb", "°C", None],
    "RMS_Differential_Current": ["RMS Differential Current", "rms_diff_current", "mA", "mdi:current-ac"],
    
    # E/S digitales
    "DO_1_Status": ["Digital Output 1. Status", "do_1_status", None, None],
    "DO_2_Status": ["Digital Output 2. Status", "do_2_status", None, None],
    "DI_DRM0_Status": ["Digital Input DRM0 Status", "di_drm_status", None, None],
    "DI_2_Status": ["Digital Input 2. Status", "di_2_status", None, None],
    "DI_3_Status": ["Digital Input 3. Status", "di_3_status", None, None],
    
    # Estado del inversor
    "Inverter_State": ["Inverter State", "inverter_state", None, None],
    "Total_Hours": ["Total Operating Hours", "total_hours", "h", "mdi:clock-outline"],
    "Alarm_Code": ["Alarm Code", "alarm_code", None, "mdi:alert-circle"],
}

METER_SENSOR_TYPES = {
    # Medidor externo (nombres actualizados para 3Play)
    "EM_Voltage": ["External Meter AC Voltage", "ext_meter_voltage", "V", "mdi:sine-wave"],
    "EM_Frequency": ["External Meter AC Frequency", "ext_meter_freq", "Hz", None],
    "EM_Active_Power": ["External Meter AC Active Power", "grid_power", "W", None],
    "EM_Active_Energy": ["External Meter AC Active Energy", "grid_active_energy", "Wh", None, "grid_power"],
    "EM_Reactive_Power": ["External Meter AC Reactive Power", "ext_meter_q", "Var", None],
    
    # Legacy - para compatibilidad con nombres antiguos
    "EM_Active_Power_Returned": ["External Meter AC Active Power Returned", "em_active_power_returned", "W", None],
    "EM_Active_Energy_Returned": ["External Meter AC Active Energy Returned", "em_active_energy_returned", "Wh", None, "em_active_power_returned"],
}

PV_FIELD_SENSOR_TYPES = {
    # PV básicos que sí existen en los registros
    "PV1_Voltage": ["PV1 Voltage", "pv1_voltage", "V", None],
    "PV1_Current": ["PV1 Current", "pv1_current", "A", "mdi:current-dc"],
    "PV1_Power": ["PV1 Power", "pv1_power", "W", None],
    "PV1_Energy": ["PV1 Energy", "pv1_energy", "Wh", None, "pv1_power"],
    "PV2_Voltage": ["PV2 Voltage", "pv2_voltage", "V", None],
    "PV2_Current": ["PV2 Current", "pv2_current", "A", "mdi:current-dc"],
    "PV2_Power": ["PV2 Power", "pv2_power", "W", None],
    "PV2_Energy": ["PV2 Energy", "pv2_energy", "Wh", None, "pv2_power"],
    
    # Solo para 3Play - PV adicionales
    "PV3_Voltage": ["PV3 Voltage", "pv3_voltage", "V", None],
    "PV3_Current": ["PV3 Current", "pv3_current", "A", "mdi:current-dc"],
    "PV3_Power": ["PV3 Power", "pv3_power", "W", None],
    "PV3_Energy": ["PV3 Energy", "pv3_energy", "Wh", None, "pv3_power"],
    "PV4_Voltage": ["PV4 Voltage", "pv4_voltage", "V", None],
    "PV4_Current": ["PV4 Current", "pv4_current", "A", "mdi:current-dc"],
    "PV4_Power": ["PV4 Power", "pv4_power", "W", None],
    "PV4_Energy": ["PV4 Energy", "pv4_energy", "Wh", None, "pv4_power"],
    
    # Totales PV (calculados desde los registros individuales)
    "PV_Internal_Total_Power": ["PV Internal Total Power", "pv_internal_total_power", "W", None],
    "PV_Internal_Total_Energy": ["PV Internal Total Energy", "pv_internal_total_energy", "Wh", None, "pv_internal_total_power"],
    "PV_Total_Power": ["PV Total Power", "pv_total_power", "W", None],
    "PV_Total_Energy": ["PV Total Energy", "pv_total_energy", "Wh", None, "pv_total_power"],
    
    # Registros que realmente existen en 3Play Input
    "PV_External_Power": ["PV External Power", "pv_external_power", "W", None],
    "PV_External_Energy": ["PV External Energy", "pv_external_energy", "Wh", None, "pv_external_power"],
    "EV_Power": ["EV Power", "ev_power", "W", None],
    "EV_Energy": ["EV Energy", "ev_energy", "Wh", None, "ev_power"],
    "Total_Loads_Power": ["Total Loads Power", "loads_power_total", "W", None],
    "Total_Loads_Energy": ["Total Loads Energy", "loads_power_total_energy", "Wh", None, "loads_power_total"],
}

BATTERY_SENSOR_TYPES = {
    # Nombres que coinciden con los registros 3Play reales
    "Battery_Voltage": ["Battery Voltage", "bat_voltage", "V", None],
    "Battery_Current": ["Battery Current", "bat_current", "A", "mdi:current-dc"],
    "Battery_Power": ["Battery Power", "bat_power", "W", "mdi:battery"],
    "Battery_SOC": ["Battery State of Charge", "bat_soc", "%", "mdi:battery-high"],
    "Battery_SOH": ["Battery State of Health", "bat_soh", "%", None],
    "Battery_Charging_Voltage": ["Battery Charging Voltage", "bat_charge_voltage", "V", None],
    "Battery_Discharging_Voltage": ["Battery Discharging Voltage", "bat_discharge_voltage", "V", None],
    "Battery_Charging_Current_max": ["Battery Max. Charging Current", "bat_charge_current_max", "A", "mdi:current-dc"],
    "Battery_Discharging_Current_max": ["Battery Max. Discharging Current", "bat_discharge_current_max", "A", "mdi:current-dc"],
    "Battery_Status": ["Battery Status", "bat_state", None, None],
    "Battery_Temp": ["Battery Temperature", "bat_temp", "°C", "mdi:thermometer"],
    "Battery_BMS_Alarm": ["Battery BMS Alarm", "bat_bms_alarm", None, None],
    "Battery_Discharge_Limitation": ["Battery Discharge Limitation Reason", "bat_discharge_limitation", None, None],
    "Battery_Charge_Limitation": ["Battery Charge Limitation Reason", "bat_charge_limitation", None, None],
    "Battery_Voltage_Internal": ["Battery Voltage Internal Sensor", "bat_voltage_internal", "V", None],
    "Battery_BMS_Flags": ["Battery BMS Flags", "bat_bms_flags", None, None],
    "Battery_BMS_Warnings": ["Battery BMS Warnings", "bat_bms_warnings", None, None],
    "Battery_BMS_Errors": ["Battery BMS Errors", "bat_bms_errors", None, None],
    "Battery_BMS_Faults": ["Battery BMS Faults", "bat_bms_faults", None, None],
    
    # Potencias calculadas para compatibilidad (se calculan desde bat_power)
    "Battery_Charging_Power": ["Battery Charging Power", "battery_charging_power", "W", "mdi:battery-charging-100"],
    "Battery_Charging_Energy": ["Battery Charging Energy", "battery_charging_energy", "Wh", "mdi:battery-charging-100", "battery_charging_power"],
    "Battery_Discharging_Power": ["Battery Discharging Power", "battery_discharging_power", "W", "mdi:battery-charging-100"],
    "Battery_Discharging_Energy": ["Battery Discharging Energy", "battery_discharging_energy", "Wh", "mdi:battery-charging-100", "battery_discharging_power"],
}

BOOLEAN_STATUS = {
    0: "Off",
    1: "On"
}

INVERTER_STATUS = {
    0: "Inverter Stopped",
    1: "Starting",
    2: "Off-grid",
    3: "On-grid",
    4: "On-grid (Standby Battery)",
    5: "Waiting to connect to Grid",
    6: "Critical Loads Bypassed to Grid",
    7: "Emergency Charge from PV",
    8: "Emergency Charge from Grid",
    9: "Inverter Locked waiting for Reset",
    10: "Error Mode"
}

BATTERY_STATUS = {
    0: "Standby",
    1: "Discharging",
    2: "Constant Current Charging",
    3: "Constant Voltage Charging",
    4: "Floating",
    5: "Equalizing",
    6: "Error Communication with BMS",
    7: "No Configured",
    8: "Capacity Calibration (Step 1)",
    9: "Capacity Calibration (Step 2)",
    10: "Standby Manual"
}

BATTERY_BMS_ALARMS = {
    0: "High Current Charge",
    1: "High Voltage",
    2: "Low Voltage",
    3: "High Temperatura",
    4: "Low Temperatura",
    5: "BMS Internal",
    6: "Cell Imbalance",
    7: "High Current Discharge",
    8: "System BMS Error",
}

BATTERY_LIMITATION_REASONS = {
    0: "No limitation",
    1: "Heat Sink Temperature",
    2: "PT100 Temperature",
    3: "Low Bus Voltage Protection",
    4: "Battery Settings",
    5: "BMS Communication",
    6: "SOC Max Configured",
    7: "SOC Min Configured",
    8: "Maximum Battery Power",
    9: "Modbus command",
    10: "Digital Input 2",
    11: "Digital Input 3",
    12: "PV Charging scheduling",
    13: "EMS Strategy",
}

AP_REDUCTION_REASONS = {
    0: "No limitation",
    1: "Communication",
    2: "PCB Temperature",
    3: "Heat Sink Temperature",
    4: "Pac vs Fac Algorithm",
    5: "Soft Start",
    6: "Charge Power Configured",
    7: "PV Surplus injected to the Loads",
    8: "Pac vs Vac Algorithm",
    9: "Battery Power Limited",
    10: "AC Grid Power Limited",
    11: "Self-Consumption Mode",
    12: "High Bus Voltage Protection",
    13: "LVRT or HVRT Process",
    14: "Nominal AC Current",
    15: "Grid Consumption Protection",
    16: "PV Surplus Injected to the Grid",
}
