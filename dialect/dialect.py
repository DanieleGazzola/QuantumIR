from __future__ import annotations
from xdsl.dialects.builtin import IntegerType, StringAttr
from xdsl.ir import Dialect, OpResult, SSAValue, Region, Attribute
from xdsl.irdl import IRDLOperation, Operand, attr_def, irdl_op_definition, operand_def, result_def, region_def


@irdl_op_definition
class InitOp(IRDLOperation):

    name = "quantum.init"
    value: IntegerType = attr_def(IntegerType)
    res: OpResult = result_def(IntegerType)

    def __init__(self, value: IntegerType):
        super().__init__(result_types=[IntegerType], attributes={"value": value})

    @staticmethod
    def from_value(value: IntegerType) -> InitOp:
        return InitOp(value)

@irdl_op_definition
class NotOp(IRDLOperation):

    name = "quantum.not"
    target: Operand = operand_def(IntegerType)
    res: OpResult = result_def(IntegerType)

    def __init__(self, target: SSAValue):
        super().__init__(result_types=[IntegerType], operands=[target])

    @staticmethod
    def from_value(value: SSAValue) -> NotOp:
        return NotOp(value)
    
    
@irdl_op_definition
class CNotOp(IRDLOperation):

    name = "quantum.cnot"
    control: Operand = operand_def(IntegerType)
    target: Operand = operand_def(IntegerType)
    res: OpResult = result_def(IntegerType)

    def __init__(self, control: SSAValue, target: SSAValue):
        super().__init__(result_types=[IntegerType], operands=[control, target])

    @staticmethod
    def from_value(control: SSAValue, target: SSAValue) -> CNotOp:
        return CNotOp(control, target)

@irdl_op_definition
class CCNotOp(IRDLOperation):

    name = "quantum.ccnot"
    rhs1: Operand = operand_def(IntegerType)
    rhs2: Operand = operand_def(IntegerType)
    res: OpResult = result_def(IntegerType)

    def __init__(self, rhs1: SSAValue, rhs2: SSAValue):
        super().__init__(result_types=[IntegerType], operands=[rhs1, rhs2])

    @staticmethod
    def from_value(value1: SSAValue, value2: SSAValue) -> CCNotOp:
        return CCNotOp(value1, value2)

@irdl_op_definition
class MeasureOp(IRDLOperation):

    name = "quantum.measure"
    value: Operand = operand_def(IntegerType)
    res: OpResult = result_def(IntegerType)

    def __init__(self, value: SSAValue):
        super().__init__(result_types=[IntegerType], operands=[value])

    @staticmethod
    def from_value(value: SSAValue) -> MeasureOp:
        return MeasureOp(value)

@irdl_op_definition
class FuncOp(IRDLOperation):

    name = "quantum.func"
    body: Region = region_def()
    func_name: StringAttr = attr_def(StringAttr)

    def __init__(self, name: str, region: Region | type[Region.DEFAULT] = Region.DEFAULT):

        attributes: dict[str, Attribute] = { "func_name": StringAttr(name) }
        return super().__init__(attributes=attributes, regions=[region])


Quantum = Dialect(
    "quantum",
    [
        InitOp,
        NotOp,
        CNotOp,
        CCNotOp,
        MeasureOp,
        FuncOp,
    ],
    [],
)
