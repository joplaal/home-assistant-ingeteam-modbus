"""
Enhanced Modbus client for Ingeteam inverters.
Supports efficient block reading, retry logic, and proper data type handling.
"""
import asyncio
import logging
import threading
import time
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

from .model_map import Register, RegisterBlock, RegisterMap, DataType, TableType

_LOGGER = logging.getLogger(__name__)


@dataclass
class ReadResult:
    """Result of a register read operation."""
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None


class ModbusClient:
    """Enhanced Modbus client with block reading and retry logic."""
    
    def __init__(self, host: str, port: int = 502, timeout: float = 3.0, 
                 retries: int = 2, retry_delay: float = 0.5):
        """Initialize the Modbus client."""
        self._host = host
        self._port = port
        self._timeout = timeout
        self._retries = retries
        self._retry_delay = retry_delay
        self._client = ModbusTcpClient(host=host, port=port, timeout=timeout)
        self._lock = threading.Lock()
        self._connected = False
        
    def connect(self) -> bool:
        """Connect to the Modbus device."""
        with self._lock:
            try:
                self._connected = self._client.connect()
                if self._connected:
                    _LOGGER.info("Successfully connected to %s:%s", self._host, self._port)
                else:
                    _LOGGER.warning("Failed to connect to %s:%s", self._host, self._port)
                return self._connected
            except Exception as e:
                _LOGGER.error("Error connecting to %s:%s: %s", self._host, self._port, e)
                self._connected = False
                return False
    
    def disconnect(self):
        """Disconnect from the Modbus device."""
        with self._lock:
            if self._client:
                self._client.close()
                self._connected = False
                _LOGGER.info("Disconnected from %s:%s", self._host, self._port)
    
    def is_connected(self) -> bool:
        """Check if client is connected."""
        with self._lock:
            return self._connected and self._client.is_socket_open()
    
    def _ensure_connected(self) -> bool:
        """Ensure client is connected, reconnect if necessary."""
        if not self.is_connected():
            _LOGGER.info("Modbus client not connected, attempting to reconnect...")
            return self.connect()
        return True
    
    def _read_registers_with_retry(self, unit: int, address: int, count: int, 
                                  is_input: bool = True) -> Optional[List[int]]:
        """Read registers with retry logic."""
        for attempt in range(self._retries + 1):
            try:
                if not self._ensure_connected():
                    if attempt < self._retries:
                        time.sleep(self._retry_delay * (attempt + 1))
                        continue
                    return None
                
                with self._lock:
                    if is_input:
                        response = self._client.read_input_registers(
                            address=address, count=count, device_id=unit
                        )
                    else:
                        response = self._client.read_holding_registers(
                            address=address, count=count, device_id=unit
                        )
                
                if response.isError():
                    _LOGGER.warning(
                        "Modbus error reading %s registers at %d (count: %d), attempt %d: %s",
                        "input" if is_input else "holding", address, count, attempt + 1, response
                    )
                    if attempt < self._retries:
                        time.sleep(self._retry_delay * (attempt + 1))
                        continue
                    return None
                
                return response.registers
                
            except ModbusException as e:
                _LOGGER.warning(
                    "Modbus exception reading %s registers at %d, attempt %d: %s",
                    "input" if is_input else "holding", address, attempt + 1, e
                )
                if attempt < self._retries:
                    time.sleep(self._retry_delay * (attempt + 1))
                    continue
                return None
            except Exception as e:
                _LOGGER.error(
                    "Unexpected error reading %s registers at %d, attempt %d: %s",
                    "input" if is_input else "holding", address, attempt + 1, e
                )
                if attempt < self._retries:
                    time.sleep(self._retry_delay * (attempt + 1))
                    continue
                return None
        
        return None
    
    def read_block(self, block: RegisterBlock, unit: int) -> ReadResult:
        """Read a register block and parse the data."""
        is_input = block.table == TableType.INPUT
        
        registers = self._read_registers_with_retry(
            unit=unit,
            address=block.start_address,
            count=block.count,
            is_input=is_input
        )
        
        if registers is None:
            return ReadResult(
                success=False,
                data={},
                error=f"Failed to read {block.table.value} block at {block.start_address}"
            )
        
        # Parse the register data
        data = {}
        
        for register in block.registers:
            try:
                # Calculate offset within the block
                offset = register.address - block.start_address
                
                if offset < 0 or offset >= len(registers):
                    _LOGGER.warning(
                        "Register %s at address %d is outside block bounds",
                        register.name, register.address
                    )
                    continue
                
                # Extract and convert the value
                value = self._extract_value(registers, offset, register)
                
                # Apply scaling
                if register.scale != 1.0:
                    value = value * register.scale
                
                # Validate physical limits
                if self._validate_value(register, value):
                    data[register.name] = value
                else:
                    _LOGGER.warning(
                        "Value %s for register %s failed validation, skipping",
                        value, register.name
                    )
                    
            except Exception as e:
                _LOGGER.error(
                    "Error parsing register %s: %s", register.name, e
                )
                continue
        
        return ReadResult(success=True, data=data)
    
    def _extract_value(self, registers: List[int], offset: int, register: Register) -> Union[int, float]:
        """Extract value from registers based on data type."""
        if register.data_type == DataType.UINT16:
            return registers[offset]
        
        elif register.data_type == DataType.INT16:
            value = registers[offset]
            # Convert to signed 16-bit
            if value & 0x8000:
                value = value - 0x10000
            return value
        
        elif register.data_type == DataType.UINT32:
            # Big-endian word order (high word first)
            if offset + 1 >= len(registers):
                raise ValueError(f"Not enough registers for UINT32 at offset {offset}")
            high_word = registers[offset]
            low_word = registers[offset + 1]
            return (high_word << 16) | low_word
        
        elif register.data_type == DataType.INT32:
            # Big-endian word order (high word first)
            if offset + 1 >= len(registers):
                raise ValueError(f"Not enough registers for INT32 at offset {offset}")
            high_word = registers[offset]
            low_word = registers[offset + 1]
            value = (high_word << 16) | low_word
            # Convert to signed 32-bit
            if value & 0x80000000:
                value = value - 0x100000000
            return value
        
        else:
            raise ValueError(f"Unsupported data type: {register.data_type}")
    
    def _validate_value(self, register: Register, value: Union[int, float]) -> bool:
        """Validate value against physical limits."""
        # Basic sanity checks based on register type and unit
        
        if register.unit == "V":  # Voltage
            if not (-1000 <= value <= 10000):  # -1kV to 10kV reasonable range
                return False
        elif register.unit == "A":  # Current
            if not (-10000 <= value <= 10000):  # -10kA to 10kA reasonable range
                return False
        elif register.unit == "W":  # Power
            if not (-1000000 <= value <= 1000000):  # -1MW to 1MW reasonable range
                return False
        elif register.unit == "%":  # Percentage
            if not (-10 <= value <= 110):  # Allow some margin for SOC/SOH
                return False
        elif register.unit == "°C":  # Temperature
            if not (-50 <= value <= 150):  # Reasonable temperature range
                return False
        elif register.unit == "Hz":  # Frequency
            if not (40 <= value <= 70):  # Grid frequency range
                return False
        
        return True
    
    def read_register_map(self, register_map: RegisterMap, unit: int) -> ReadResult:
        """Read all blocks in a register map."""
        blocks = register_map.get_blocks()
        all_data = {}
        errors = []
        
        for block in blocks:
            result = self.read_block(block, unit)
            if result.success:
                all_data.update(result.data)
            else:
                errors.append(result.error)
                _LOGGER.warning("Failed to read block: %s", result.error)
        
        success = len(all_data) > 0  # Success if we got at least some data
        error = "; ".join(errors) if errors else None
        
        return ReadResult(success=success, data=all_data, error=error)


class AsyncModbusClient:
    """Async wrapper for the Modbus client."""
    
    def __init__(self, client: ModbusClient):
        self._client = client
    
    async def connect(self) -> bool:
        """Connect to the Modbus device."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._client.connect)
    
    async def disconnect(self):
        """Disconnect from the Modbus device."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._client.disconnect)
    
    async def read_register_map(self, register_map: RegisterMap, unit: int) -> ReadResult:
        """Read all blocks in a register map."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._client.read_register_map, register_map, unit
        )
    
    async def read_block(self, block: RegisterBlock, unit: int) -> ReadResult:
        """Read a register block."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._client.read_block, block, unit)