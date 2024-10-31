from __future__ import annotations

from typing import TypeVar

from xdsl.dialects.builtin import IntegerType, StringAttr, VectorType,IntegerAttr
from xdsl.ir import Dialect, OpResult, SSAValue, Region, Attribute
from xdsl.irdl import IRDLOperation, Operand, attr_def, irdl_op_definition, operand_def, result_def, region_def


# Operation to initialize a qubit (or a vector of them) to zero
@irdl_op_definition
class InitOp(IRDLOperation):

    name = "quantum.init"
    value: IntegerType = attr_def(TypeVar("AttributeInvT", bound=Attribute))
    res: OpResult = result_def()

    def __init__(self, values):
        # Determine if values is a single IntegerType or a VectorType of IntegerType
        result_types=[]
        attributes=[]
        if isinstance(values, IntegerType):
            # Single IntegerType case
            result_types = [IntegerType(1)]
            attributes = {"type": values,"value": IntegerAttr(0,IntegerType(1))}   
        elif isinstance(values, VectorType):
            # Vector of IntegerType case
            result_types= [VectorType(values.get_element_type(), [values.get_shape()[0],])]     
            attributes = {"type": values,"value": IntegerAttr(0,IntegerType(values.get_shape()[0]))}
        else: 
            raise TypeError("Expected IntegerType or VectorType(IntegerType) for values")

        super().__init__(result_types=result_types, attributes=attributes)
           
    @staticmethod
    def from_value(value) -> InitOp:
        return InitOp(value)

# Operation to apply the NOT gate to a qubit (or a vector of them)
@irdl_op_definition
class NotOp(IRDLOperation):

    name = "quantum.not"
    target: Operand = operand_def(TypeVar("AttributeInvT", bound=Attribute))
    res: OpResult = result_def()

    def __init__(self, target: SSAValue):
        if isinstance(target.type, IntegerType):
            super().__init__(result_types=[IntegerType(1)], operands=[target])
        else: # VectorType
            size=target.type.get_shape()[0]
            super().__init__(result_types=[VectorType(IntegerType(1),[size,])], operands=[target])
    
    @staticmethod
    def from_value(value: SSAValue) -> NotOp:
        return NotOp(value)
    
# Operation to apply the CNOT gate to a qubit (or a vector of them)
# the first qubit is the control one, the second is the target.
@irdl_op_definition
class CNotOp(IRDLOperation):

    name = "quantum.cnot"
    control: Operand = operand_def(TypeVar("AttributeInvT", bound=Attribute))
    target: Operand = operand_def(TypeVar("AttributeInvT", bound=Attribute))
    res: OpResult = result_def()

    def __init__(self, control: SSAValue, target: SSAValue):
        if isinstance(control.type, IntegerType) and isinstance(target.type, IntegerType):
            super().__init__(result_types=[IntegerType(1)], operands=[control, target])
        else: # VectorType
            size = control.type.get_shape()[0]
            super().__init__(result_types=[VectorType(IntegerType(1),[size,])], operands=[control, target])

    @staticmethod
    def from_value(control: SSAValue, target: SSAValue) -> CNotOp:
        return CNotOp(control, target)

# Operation to apply the CCNOT gate to a qubit (or a vector of them)
# the first two qubits are the control ones, the third is the target.
@irdl_op_definition
class CCNotOp(IRDLOperation):

    name = "quantum.ccnot"
    control1: Operand = operand_def(TypeVar("AttributeInvT", bound=Attribute))
    control2: Operand = operand_def(TypeVar("AttributeInvT", bound=Attribute))
    target: Operand = operand_def(TypeVar("AttributeInvT", bound=Attribute))
    res: OpResult = result_def()

    def __init__(self, control1: SSAValue, control2: SSAValue, target: SSAValue):
        if isinstance(control1.type, IntegerType) and isinstance(control2.type, IntegerType) and isinstance(target.type, IntegerType):
            super().__init__(result_types=[IntegerType(1)], operands=[control1, control2, target])
        else: # VectorType
            size = control1.type.get_shape()[0]
            super().__init__(result_types=[VectorType(IntegerType(1),[size,])], operands=[control1, control2, target])
 
    @staticmethod
    def from_value(control1: SSAValue, control2: SSAValue, target: SSAValue) -> CCNotOp:
        return CCNotOp(control1, control2, target)

# Operation to measure a qubit (or a vector of them).
# This operation is used at the end of the circuit on the output (qu)bits.
@irdl_op_definition
class MeasureOp(IRDLOperation):

    name = "quantum.measure"
    target: Operand = operand_def(IntegerType(1))
    res: OpResult = result_def()

    def __init__(self, target: SSAValue):
        if isinstance(target.type, IntegerType):
            super().__init__(result_types=[IntegerType(1)], operands=[target])
        else: # VectorType
            size=target.type.get_shape()[0]
            super().__init__(result_types=[VectorType(IntegerType(1),[size,])], operands=[target])

    @staticmethod
    def from_value(target: SSAValue) -> MeasureOp:
        return MeasureOp(target)

# Operation to define a function
@irdl_op_definition
class FuncOp(IRDLOperation):

    name = "quantum.func"
    body: Region = region_def()
    func_name: StringAttr = attr_def(StringAttr)

    def __init__(self, name: str, region: Region | type[Region.DEFAULT] = Region.DEFAULT):

        attributes: dict[str, Attribute] = { "func_name": StringAttr(name) }
        return super().__init__(attributes=attributes, regions=[region])

### Operations for metrics measurement

# T-Gate operation. Unitary gate applied on target qubit.
@irdl_op_definition
class TGateOp(IRDLOperation):

    name = "quantum.t"
    target: Operand = operand_def(TypeVar("AttributeInvT", bound=Attribute))
    res: OpResult = result_def()

    def __init__(self, target: SSAValue):
        if isinstance(target.type, IntegerType):
            super().__init__(result_types=[IntegerType(1)], operands=[target])
        else: # VectorType
            size=target.type.get_shape()[0]
            super().__init__(result_types=[VectorType(IntegerType(1),[size,])], operands=[target])
    @staticmethod
    def from_value(target: SSAValue) -> TGateOp:
        return TGateOp(target)

# TDagger-Gate operation. Unitary gate applied on target qubit.
@irdl_op_definition
class TDaggerGateOp(IRDLOperation):

    name = "quantum.tdagger"
    target: Operand = operand_def(TypeVar("AttributeInvT", bound=Attribute))
    res: OpResult = result_def()

    def __init__(self, target: SSAValue):
        if isinstance(target.type, IntegerType):
            super().__init__(result_types=[IntegerType(1)], operands=[target])
        else: # VectorType
            size=target.type.get_shape()[0]
            super().__init__(result_types=[VectorType(IntegerType(1),[size,])], operands=[target])

    @staticmethod
    def from_value(target: SSAValue) -> TGateOp:
        return TDaggerGateOp(target)
    

# Hadamard gate operation. Unitary gate applied on target qubit.
@irdl_op_definition
class HadamardOp(IRDLOperation):
    
        name = "quantum.h"
        target: Operand = operand_def(TypeVar("AttributeInvT", bound=Attribute))
        res: OpResult = result_def()
    
        def __init__(self, target: SSAValue):
            if isinstance(target.type, IntegerType):
                super().__init__(result_types=[IntegerType(1)], operands=[target])
            else: # VectorType
                size=target.type.get_shape()[0]
                super().__init__(result_types=[VectorType(IntegerType(1),[size,])], operands=[target])
    
        @staticmethod
        def from_value(target: SSAValue) -> HadamardOp:
            return HadamardOp(target)


Quantum = Dialect(
    "quantum",
    [
        InitOp,
        NotOp,
        CNotOp,
        CCNotOp,
        MeasureOp,
        FuncOp,
        TGateOp,
        TDaggerGateOp,
        HadamardOp
    ],
    [],
)
