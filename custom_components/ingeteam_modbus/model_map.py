"""
Model maps and register definitions for Ingeteam inverters.
"""
from typing import Optional, Dict, List, Union, Any
from dataclasses import dataclass
from enum import Enum


class DataType(Enum):
    """Modbus data types."""
    UINT16 = "uint16"
    INT16 = "int16"
    UINT32 = "uint32"
    INT32 = "int32"


class TableType(Enum):
    """Modbus table types."""
    HOLDING = "holding"
    INPUT = "input"


@dataclass
class Register:
    """Register definition."""
    name: str
    address: int
    data_type: DataType
    scale: float = 1.0
    unit: Optional[str] = None
    signed: bool = False
    table: TableType = TableType.INPUT
    description: Optional[str] = None
    
    @property
    def register_count(self) -> int:
        """Number of registers needed for this data type."""
        if self.data_type in [DataType.UINT32, DataType.INT32]:
            return 2
        return 1
    
    @property
    def is_signed(self) -> bool:
        """Whether this register contains signed data."""
        return self.signed or self.data_type in [DataType.INT16, DataType.INT32]


@dataclass
class RegisterBlock:
    """A contiguous block of registers for efficient reading."""
    start_address: int
    count: int
    registers: List[Register]
    table: TableType
    
    @property
    def end_address(self) -> int:
        """End address of the block."""
        return self.start_address + self.count - 1


class RegisterMap:
    """Register map for a specific model."""
    
    def __init__(self, name: str, registers: List[Register]):
        self.name = name
        self.registers = {reg.name: reg for reg in registers}
        self._blocks: Optional[List[RegisterBlock]] = None
    
    def get_register(self, name: str) -> Optional[Register]:
        """Get register by name."""
        return self.registers.get(name)
    
    def get_blocks(self, max_block_size: int = 60, max_gap: int = 5) -> List[RegisterBlock]:
        """
        Create optimized register blocks for efficient reading.
        Groups nearby registers together to minimize Modbus calls.
        """
        if self._blocks is not None:
            return self._blocks
        
        # Group registers by table type
        holding_regs = []
        input_regs = []
        
        for reg in self.registers.values():
            if reg.table == TableType.HOLDING:
                holding_regs.append(reg)
            else:
                input_regs.append(reg)
        
        blocks = []
        
        # Create blocks for each table type
        for table_regs, table_type in [(holding_regs, TableType.HOLDING), 
                                       (input_regs, TableType.INPUT)]:
            if not table_regs:
                continue
                
            # Sort by address
            table_regs.sort(key=lambda r: r.address)
            
            current_block_regs = []
            current_start = None
            current_end = None
            
            for reg in table_regs:
                reg_start = reg.address
                reg_end = reg.address + reg.register_count - 1
                
                if current_start is None:
                    # First register in block
                    current_block_regs = [reg]
                    current_start = reg_start
                    current_end = reg_end
                elif (reg_start - current_end <= max_gap and 
                      reg_end - current_start + 1 <= max_block_size):
                    # Add to current block
                    current_block_regs.append(reg)
                    current_end = max(current_end, reg_end)
                else:
                    # Start new block
                    if current_block_regs:
                        blocks.append(RegisterBlock(
                            start_address=current_start,
                            count=current_end - current_start + 1,
                            registers=current_block_regs.copy(),
                            table=table_type
                        ))
                    
                    current_block_regs = [reg]
                    current_start = reg_start
                    current_end = reg_end
            
            # Add last block
            if current_block_regs:
                blocks.append(RegisterBlock(
                    start_address=current_start,
                    count=current_end - current_start + 1,
                    registers=current_block_regs.copy(),
                    table=table_type
                ))
        
        self._blocks = blocks
        return blocks


def create_register(name: str, address: int, data_type: str, scale: float = 1.0, 
                   unit: Optional[str] = None, signed: bool = False, 
                   table: str = "input", description: Optional[str] = None) -> Register:
    """Helper function to create a register."""
    return Register(
        name=name,
        address=address,
        data_type=DataType(data_type),
        scale=scale,
        unit=unit,
        signed=signed,
        table=TableType(table),
        description=description
    )


# Shorthand function for easier register definition
def R(name: str, address: int, data_type: str, scale: float = 1.0, 
      unit: Optional[str] = None, signed: bool = False, 
      table: str = "input", description: Optional[str] = None) -> Register:
    """Shorthand for create_register."""
    return create_register(name, address, data_type, scale, unit, signed, table, description)