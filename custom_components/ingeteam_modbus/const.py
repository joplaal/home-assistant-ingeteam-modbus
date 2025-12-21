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
    
    # Battery Data
    R("battery_voltage", 16, "uint16", 0.1, "V", description="Battery Voltage"),
    R("battery_voltage_internal", 17, "uint16", 0.1, "V", description="Battery Voltage Internal"),
    R("battery_current", 19, "int16", 0.01, "A", signed=True, description="Battery Current"),
    R("battery_power", 18, "int16", 1.0, "W", signed=True, description="Battery Power"),
    R("battery_state_of_charge", 22, "uint16", 1.0, "%", description="Battery State of Charge"),
    R("battery_state_of_health", 23, "uint16", 1.0, "%", description="Battery State of Health"),
    R("battery_charging_current_max", 24, "uint16", 0.01, "A", description="Max Charging Current"),
    R("battery_discharging_current_max", 25, "uint16", 0.01, "A", description="Max Discharging Current"),
    R("battery_charging_voltage", 28, "uint16", 0.1, "V", description="Battery Charging Voltage"),
    R("battery_discharging_voltage", 29, "uint16", 0.1, "V", description="Battery Discharging Voltage"),
    R("battery_temp", 31, "int16", 0.1, "°C", signed=True, description="Battery Temperature"),
    R("battery_status", 21, "uint16", 1.0, None, description="Battery Status"),
    R("battery_bms_alarms", 47, "uint16", 1.0, None, description="Battery BMS Alarms"),
    
    # PV Power
    R("pv1_voltage", 32, "uint16", 1.0, "V", description="PV1 Voltage"),
    R("pv1_current", 33, "uint16", 0.01, "A", description="PV1 Current"),
    R("pv1_power", 34, "uint16", 1.0, "W", description="PV1 Power"),
    
    R("pv2_voltage", 35, "uint16", 1.0, "V", description="PV2 Voltage"),
    R("pv2_current", 36, "uint16", 0.01, "A", description="PV2 Current"),
    R("pv2_power", 37, "uint16", 1.0, "W", description="PV2 Power"),
    
    # Critical Loads (Output)
    # Voltages
    R("cl_voltage_l1", 60, "uint16", 0.1, "V", description="Critical Load Voltage L1"),
    R("cl_voltage_l2", 61, "uint16", 0.1, "V", description="Critical Load Voltage L2"),
    R("cl_voltage_l3", 62, "uint16", 0.1, "V", description="Critical Load Voltage L3"),
    # Currents
    R("cl_current_l1", 49, "uint16", 0.01, "A", description="Critical Load Current L1"),
    R("cl_current_l2", 53, "uint16", 0.01, "A", description="Critical Load Current L2"),
    R("cl_current_l3", 57, "uint16", 0.01, "A", description="Critical Load Current L3"),
    # Powers
    R("cl_active_power_l1", 51, "int16", 0.1, "W", signed=True, description="Critical Load Power L1"),
    R("cl_active_power_l2", 55, "int16", 0.1, "W", signed=True, description="Critical Load Power L2"),
    R("cl_active_power_l3", 59, "int16", 0.1, "W", signed=True, description="Critical Load Power L3"),
    # Reactive Powers (Estimated)
    R("cl_reactive_power_l1", 67, "int16", 1.0, "var", signed=True, description="Critical Load Reactive Power L1"),
    R("cl_reactive_power_l2", 69, "int16", 1.0, "var", signed=True, description="Critical Load Reactive Power L2"),
    R("cl_reactive_power_l3", 71, "int16", 1.0, "var", signed=True, description="Critical Load Reactive Power L3"),
    # Frequency
    R("ac_freq", 63, "uint16", 0.01, "Hz", description="AC Frequency"),
    
    # Internal Meter (Grid/Inverter Output)
    # Voltages
    R("im_voltage_l1", 75, "uint16", 0.1, "V", description="Internal Meter Voltage L1"),
    R("im_voltage_l2", 77, "uint16", 0.1, "V", description="Internal Meter Voltage L2"),
    R("im_voltage_l3", 79, "uint16", 0.1, "V", description="Internal Meter Voltage L3"),
    # Currents
    R("im_current_l1", 76, "uint16", 0.01, "A", description="Internal Meter Current L1"),
    R("im_current_l2", 78, "uint16", 0.01, "A", description="Internal Meter Current L2"),
    R("im_current_l3", 80, "uint16", 0.01, "A", description="Internal Meter Current L3"),
    # Active Powers
    R("im_active_power_l1", 83, "int16", 0.1, "W", signed=True, description="Internal Meter Power L1"),
    R("im_active_power_l2", 85, "int16", 0.1, "W", signed=True, description="Internal Meter Power L2"),
    R("im_active_power_l3", 87, "int16", 0.1, "W", signed=True, description="Internal Meter Power L3"),
    # Reactive Powers (Estimated)
    R("im_reactive_power_l1", 84, "int16", 0.1, "var", signed=True, description="Internal Meter Reactive Power L1"),
    R("im_reactive_power_l2", 86, "int16", 0.1, "var", signed=True, description="Internal Meter Reactive Power L2"),
    R("im_reactive_power_l3", 88, "int16", 0.1, "var", signed=True, description="Internal Meter Reactive Power L3"),
    # Frequency & PF
    R("im_freq", 81, "uint16", 0.01, "Hz", description="Internal Meter Frequency"),
    R("im_power_factor", 89, "int16", 0.001, None, signed=True, description="Internal Meter Power Factor"),
    
    # External Meter
    # Active Powers
    R("em_active_power_l1", 91, "int16", 1.0, "W", signed=True, description="External Meter Power L1"),
    R("em_active_power_l2", 95, "int16", 1.0, "W", signed=True, description="External Meter Power L2"),
    R("em_active_power_l3", 99, "int16", 1.0, "W", signed=True, description="External Meter Power L3"),
    # Reactive Powers (Estimated)
    R("em_reactive_power_l1", 92, "int16", 1.0, "var", signed=True, description="External Meter Reactive Power L1"),
    R("em_reactive_power_l2", 96, "int16", 1.0, "var", signed=True, description="External Meter Reactive Power L2"),
    R("em_reactive_power_l3", 100, "int16", 1.0, "var", signed=True, description="External Meter Reactive Power L3"),
    
    # Totals
    R("total_loads_power", 65, "uint16", 1.0, "W", description="Total Loads Power"),
    
    # Status & Alarms
    R("inverter_state", 129, "uint16", 1.0, None, description="Inverter State"),
    R("total_hours", 6, "uint32", 1.0, "h", description="Total Operating Hours"),
    R("alarm_code", 10, "uint32", 1.0, None, description="Alarm Code"),
    
    # Digital I/O (Estimated)
    R("do_1_status", 106, "uint16", 1.0, None, description="Digital Output 1 Status"),
    R("do_2_status", 108, "uint16", 1.0, None, description="Digital Output 2 Status"),
    
    # Temperatures (Estimated)
    R("temp_mod_1", 125, "int16", 1.0, "°C", signed=True, description="Temperature Module 1"),
    R("temp_pcb", 127, "int16", 1.0, "°C", signed=True, description="Internal Temperature"),
    
    # Missing Entities Placeholders (To match production)
    R("active_power", 38, "int16", 1.0, "W", signed=True, description="Active Power"), # Re-added
    R("reactive_power", 39, "int16", 1.0, "var", signed=True, description="Reactive Power"), # Placeholder
    R("power_factor", 40, "int16", 0.001, None, signed=True, description="Power Factor"), # Placeholder
    R("dc_bus_voltage", 41, "uint16", 1.0, "V", description="DC Bus Voltage"), # Placeholder
    R("temp_mod_2", 126, "int16", 1.0, "°C", signed=True, description="Temperature Module 2"), # Placeholder
    R("di_drm_status", 110, "uint16", 1.0, None, description="Digital Input DRM0 Status"), # Placeholder
    R("di_2_status", 111, "uint16", 1.0, None, description="Digital Input 2 Status"), # Placeholder
    R("di_3_status", 112, "uint16", 1.0, None, description="Digital Input 3 Status"), # Placeholder
    R("em_voltage", 102, "uint16", 1.0, "V", description="External Meter Voltage"), # Updated from 101 based on scan (233V)
    R("em_freq", 103, "uint16", 0.1, "Hz", description="External Meter Frequency"), # Placeholder (Value 234 -> 23.4Hz? or Voltage L2?)
    R("em_active_power_returned", 105, "int16", 1.0, "W", signed=True, description="External Meter Power Returned"), # Updated from 103 (Value 59?)
    R("ev_power", 104, "int16", 1.0, "W", signed=True, description="EV Power"), # Placeholder
    R("battery_discharge_limitation_reason", 48, "uint16", 1.0, None, description="Battery Discharge Limitation Reason"), # Placeholder
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
    "Active_Power": ["Active Power", "active_power", "W", None],
    "Active_Energy": ["Active Energy", "active_energy", "Wh", None, "active_power"],
    "Reactive_Power": ["Reactive Power", "reactive_power", "W", None],
    "Power_factor": ["Power factor Cosφ", "power_factor", None, None],
    "Active_Power_Reduction_Ratio": ["Active Power Reduction Ratio", "ap_reduction_ratio", "%", None],
    "Active_Power_Reduction_Reason": ["Active Power Reduction Reason", "ap_reduction_reason", None, None],
    "Reactive_Power_Set-Point_Type": ["Reactive Power Set-Point Type", "reactive_setpoint_type", None, None],
    "CL_Voltage": ["Critical Loads Voltage", "cl_voltage", "V", None],
    "CL_Current": ["Critical Loads Current", "cl_current", "A", "mdi:current-ac"],
    "CL_Freq": ["Critical Loads Frequency", "cl_freq", "Hz", None],
    "CL_Active_Power": ["Critical Loads Active Power", "cl_active_power", "W", None],
    "CL_Active_Energy": ["Critical Loads Active Energy", "cl_active_energy", "Wh", None, "critical_loads_active_power"],
    "CL_Reactive_Power": ["Critical Loads Reactive Power", "cl_reactive_power", "Var", None],
    "IM_Voltage": ["Internal Meter Voltage", "im_voltage", "V", None],
    "IM_Current": ["Internal Meter Current", "im_current", "A", "mdi:current-ac"],
    "IM_Freq": ["Internal Meter Frequency", "im_freq", "Hz", None],
    "IM_Active_Power": ["Internal Active Power", "im_active_power", "W", None],
    "IM_Active_Energy": ["Internal Active Energy", "im_active_energy", "Wh", None, "internal_active_power"],
    "IM_Reactive_Power": ["Internal Reactive Power", "im_reactive_power", "Var", None],
    "IM_Power_Factor": ["Internal Power Factor Cosφ", "im_power_factor", None, None],
    "DC_Bus_Voltaje": ["DC Bus Voltage", "dc_bus_voltage", "V", None],
    "Temperature_Mod_1": ["Temperature Module 1", "temp_mod_1", "°C", None],
    "Temperature_Mod_2": ["Temperature Module 2", "temp_mod_2", "°C", None],
    "Internal_Temperature": ["Internal Temperature", "temp_pcb", "°C", None],
    "RMS_Differential_Current": ["RMS Differential Current", "rms_diff_current", "mA", "mdi:current-ac"],
    "DO_1_Status": ["Digital Output 1. Status", "do_1_status", None, None],
    "DO_2_Status": ["Digital Output 2. Status", "do_2_status", None, None],
    "DI_DRM0_Status": ["Digital Input DRM0 Status", "di_drm_status", None, None],
    "DI_2_Status": ["Digital Input 2. Status", "di_2_status", None, None],
    "DI_3_Status": ["Digital Input 3. Status", "di_3_status", None, None],

    # 3Play Specific Sensors (Added for Hybrid support)
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
    "P_Total": ["Total Active Power", "p_total", "W", None],
    "Q_Total": ["Total Reactive Power", "q_total", "Var", None],
    "P_Total_Energy": ["Total Active Energy", "p_total_energy", "Wh", None, "p_total"],
    "System_Efficiency": ["System Efficiency", "system_efficiency", "%", None],
    "Grid_Balance": ["Grid Power Balance", "grid_balance", "W", None],
    "Grid_Balance_Energy": ["Grid Balance Energy", "grid_balance_energy", "Wh", None, "grid_balance"],
    "CL_Current_L1": ["Critical Loads Current L1", "cl_current_l1", "A", "mdi:current-ac"],
    "CL_Power_L1": ["Critical Loads Power L1", "cl_active_power_l1", "W", None],
    "CL_Current_L2": ["Critical Loads Current L2", "cl_current_l2", "A", "mdi:current-ac"],
    "CL_Power_L2": ["Critical Loads Power L2", "cl_active_power_l2", "W", None],
    "CL_Current_L3": ["Critical Loads Current L3", "cl_current_l3", "A", "mdi:current-ac"],
    "CL_Power_L3": ["Critical Loads Power L3", "cl_active_power_l3", "W", None],
    "IM_Active_Power_L1": ["Internal Meter Active Power L1", "im_active_power_l1", "W", None],
    "IM_Active_Power_L2": ["Internal Meter Active Power L2", "im_active_power_l2", "W", None],
    "IM_Active_Power_L3": ["Internal Meter Active Power L3", "im_active_power_l3", "W", None],
    "EM_Active_Power_L1": ["External Meter Active Power L1", "em_active_power_l1", "W", None],
    "EM_Active_Power_L2": ["External Meter Active Power L2", "em_active_power_l2", "W", None],
    "EM_Active_Power_L3": ["External Meter Active Power L3", "em_active_power_l3", "W", None],
}

METER_SENSOR_TYPES = {
    "EM_Voltage": ["External Meter AC Voltage", "em_voltage", "V", "mdi:sine-wave"],
    "EM_Frequency": ["External Meter AC Frequency", "em_freq", "Hz", None],
    "EM_Active_Power": ["External Meter AC Active Power", "em_active_power", "W", None],
    "EM_Active_Energy": ["External Meter AC Active Energy", "em_active_energy", "Wh", None, "external_meter_ac_active_power"],
    "EM_Active_Power_Returned": ["External Meter AC Active Power Returned", "em_active_power_returned", "W", None],
    "EM_Active_Energy_Returned": ["External Meter AC Active Energy Returned", "em_active_energy_returned", "Wh", None, "external_meter_ac_active_power_returned"],
    "EM_Reactive_Power": ["External Meter AC Reactive Power", "em_reactive_power", "Var", None],
}

PV_FIELD_SENSOR_TYPES = {
    "PV1_Voltage": ["PV1 Voltage", "pv1_voltage", "V", None],
    "PV1_Current": ["PV1 Current", "pv1_current", "A", "mdi:current-dc"],
    "PV1_Power": ["PV1 Power", "pv1_power", "W", None],
    "PV1_Energy": ["PV1 Energy", "pv1_energy", "Wh", None, "pv1_power"],
    "PV2_Voltage": ["PV2 Voltage", "pv2_voltage", "V", None],
    "PV2_Current": ["PV2 Current", "pv2_current", "A", "mdi:current-dc"],
    "PV2_Power": ["PV2 Power", "pv2_power", "W", None],
    "PV2_Energy": ["PV2 Energy", "pv2_energy", "Wh", None, "pv2_power"],
    "PV_External_Power": ["PV External Power", "external_pv_power", "W", None],
    "PV_Eternal_Energy": ["PV External Energy", "external_pv_energy", "Wh", None, "pv_external_power"],
    "PV_Internal_Total_Power": ["PV Internal Total Power", "pv_internal_total_power", "W", None],
    "PV_Internal_Total_Energy": ["PV Internal Total Energy", "pv_internal_total_energy", "Wh", None, "pv_internal_total_power"],
    "PV_Total_Power": ["PV Total Power", "pv_total_power", "W", None],
    "PV_Total_Energy": ["PV Total Energy", "pv_total_energy", "Wh", None, "pv_total_power"],
    "Total_Loads_Power": ["Total Loads Power", "total_loads_power", "W", None],
    "Total_Loads_Energy": ["Total Loads Energy", "total_loads_energy", "Wh", None, "total_loads_power"],
    "EV_Power": ["EV Power", "ev_power", "W", None],
    "EV_Energy": ["EV Energy", "ev_energy", "Wh", None, "ev_power"],

    # 3Play Specific PV Sensors
    "PV3_Voltage": ["PV3 Voltage", "pv3_voltage", "V", None],
    "PV3_Current": ["PV3 Current", "pv3_current", "A", "mdi:current-dc"],
    "PV3_Power": ["PV3 Power", "pv3_power", "W", None],
    "PV3_Energy": ["PV3 Energy", "pv3_energy", "Wh", None, "pv3_power"],
    "PV4_Voltage": ["PV4 Voltage", "pv4_voltage", "V", None],
    "PV4_Current": ["PV4 Current", "pv4_current", "A", "mdi:current-dc"],
    "PV4_Power": ["PV4 Power", "pv4_power", "W", None],
    "PV4_Energy": ["PV4 Energy", "pv4_energy", "Wh", None, "pv4_power"],
}

BATTERY_SENSOR_TYPES = {
    "Battery_Voltage": ["Battery Voltage", "battery_voltage", "V", None],
    "Battery_Current": ["Battery Current", "battery_current", "A", "mdi:current-dc"],
    "Battery_Charging_Power": ["Battery Charging Power", "battery_charging_power", "W", "mdi:battery-charging-100"],
    "Battery_Charging_Energy": ["Battery Charging Energy", "battery_charging_energy", "Wh", "mdi:battery-charging-100", "battery_charging_power"],
    "Battery_Discharging_Power": ["Battery Discharging Power", "battery_discharging_power", "W", "mdi:battery-charging-100"],
    "Battery_Discharging_Energy": ["Battery Discharging Energy", "battery_discharging_energy", "Wh", "mdi:battery-charging-100", "battery_discharging_power"],
    "Battery_SOC": ["Battery State of Charge", "battery_state_of_charge", "%", "mdi:battery-high"],
    "Battery_SOH": ["Battery State of Health", "battery_state_of_health", "%", None],
    "Battery_Charging_Voltage": ["Battery Charging Voltage", "battery_charging_voltage", "V", None],
    "Battery_Discharging_Voltage": ["Battery Discharging Voltage", "battery_discharging_voltage", "V", None],
    "Battery_Charging_Current_max": ["Battery Max. Charging Current", "battery_charging_current_max", "A", "mdi:current-dc"],
    "Battery_Discharging_Current_max": ["Battery Max. Discharging Current", "battery_discharging_current_max", "A", "mdi:current-dc"],
    "Battery_Status": ["Battery Status", "battery_status", None, None],
    "Battery_Temp": ["Battery Temp", "battery_temp", "°C", None],
    "Battery_BMS_Alarm": ["Battery BMS Alarm", "battery_bms_alarm", None, None],
    "Battery_Discharch_Limitation": ["Battery Discharge Limitation Reason", "battery_discharge_limitation_reason", None, None],
    "Battery_Charge_Limitation": ["Battery Charge Limitation Reason", "battery_charge_limitation_reason", None, None],
    "Battery_Voltage_Internal": ["Battery Voltage Internal Sensor", "battery_voltage_internal", "V", None],

    # 3Play Specific Battery Sensors
    "Battery_BMS_Flags": ["Battery BMS Flags", "bat_bms_flags", None, None],
    "Battery_BMS_Warnings": ["Battery BMS Warnings", "bat_bms_warnings", None, None],
    "Battery_BMS_Errors": ["Battery BMS Errors", "bat_bms_errors", None, None],
    "Battery_BMS_Faults": ["Battery BMS Faults", "bat_bms_faults", None, None],
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
