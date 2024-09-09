from __future__ import annotations

from typing import ClassVar, TypeVar

from xdsl.dialects.builtin import IntegerType, StringAttr, VectorType
from xdsl.ir import Dialect, OpResult, SSAValue, Region, Attribute
from xdsl.irdl import IRDLOperation, Operand, attr_def, irdl_op_definition, operand_def, result_def, region_def, traits_def
from xdsl.traits import MemoryEffect, MemoryEffectKind, EffectInstance, OpTrait

class GetMemoryEffect(MemoryEffect):

    @classmethod
    def get_effects(cls, op: IRDLOperation) -> set[EffectInstance] | None:
        return op.traits

@irdl_op_definition
class InitOp(IRDLOperation):

    name = "quantum.init"
    value: IntegerType = attr_def(TypeVar("AttributeInvT", bound=Attribute))
    res: OpResult = result_def()
    traits: ClassVar[frozenset[OpTrait]] = traits_def({OpTrait()})

    def __init__(self, values):
        # Determine if values is a single IntegerType or a VectorType of IntegerType
        result_types=[]
        attributes=[]
        if isinstance(values, IntegerType):
            # Single IntegerType case
            result_types = [IntegerType(1)]
            attributes = {"type": values}
        elif isinstance(values, VectorType):
            # Vector of IntegerType case
            element_type=values.get_element_type()
            size=values.get_shape()[0]
            result_types= [VectorType(element_type, [size,])]     
            attributes = {"type": values}
        else:
            raise TypeError("Expected IntegerType or VectorType(IntegerType) for values")

        super().__init__(result_types=result_types, attributes=attributes)
        self.traits = [EffectInstance(MemoryEffectKind.ALLOC, self.res)]
           
    @staticmethod
    def from_value(value) -> InitOp:
        return InitOp(value)
    
    def verify(self):
    # Ensure the result type matches the attribute type
        if isinstance(self.values, IntegerType):
            assert self.result_types[0] == IntegerType
        elif isinstance(self.values, VectorType):
            assert self.result_types[0] == VectorType(IntegerType, len(self.values))
        else:
            raise ValueError("Invalid attribute type")

@irdl_op_definition
class NotOp(IRDLOperation):

    name = "quantum.not"
    target: Operand = operand_def(TypeVar("AttributeInvT", bound=Attribute))
    res: OpResult = result_def()
    traits: ClassVar[frozenset[OpTrait]] = traits_def({OpTrait()})

    def __init__(self, target: SSAValue):
        if isinstance(target.type, IntegerType):
            super().__init__(result_types=[IntegerType(1)], operands=[target])
        else:
            size=target.type.get_shape()[0]
            super().__init__(result_types=[VectorType(IntegerType(1),[size,])], operands=[target])
        self.traits = [EffectInstance(MemoryEffectKind.READ, self.target), EffectInstance(MemoryEffectKind.WRITE, self.res)]
    
    @staticmethod
    def from_value(value: SSAValue) -> NotOp:
        return NotOp(value)
    
    
@irdl_op_definition
class CNotOp(IRDLOperation):

    name = "quantum.cnot"
    control: Operand = operand_def(TypeVar("AttributeInvT", bound=Attribute))
    target: Operand = operand_def(TypeVar("AttributeInvT", bound=Attribute))
    res: OpResult = result_def()
    traits: ClassVar[frozenset[OpTrait]] = traits_def({OpTrait()})

    def __init__(self, control: SSAValue, target: SSAValue):
        if isinstance(control.type, IntegerType) and isinstance(target.type, IntegerType):
            super().__init__(result_types=[IntegerType(1)], operands=[control, target])
        else:
            size = control.type.get_shape()[0]
            super().__init__(result_types=[VectorType(IntegerType(1),[size,])], operands=[control, target])
        self.traits = [EffectInstance(MemoryEffectKind.READ, self.control), EffectInstance(MemoryEffectKind.READ, self.target), EffectInstance(MemoryEffectKind.WRITE, self.res)]

    @staticmethod
    def from_value(control: SSAValue, target: SSAValue) -> CNotOp:
        return CNotOp(control, target)

@irdl_op_definition
class CCNotOp(IRDLOperation):

    name = "quantum.ccnot"
    control1: Operand = operand_def(TypeVar("AttributeInvT", bound=Attribute))
    control2: Operand = operand_def(TypeVar("AttributeInvT", bound=Attribute))
    target: Operand = operand_def(TypeVar("AttributeInvT", bound=Attribute))
    res: OpResult = result_def()
    traits: ClassVar[frozenset[OpTrait]] = traits_def({OpTrait()})

    def __init__(self, control1: SSAValue, control2: SSAValue, target: SSAValue):
        if isinstance(control1.type, IntegerType) and isinstance(control2.type, IntegerType) and isinstance(target.type, IntegerType):
            super().__init__(result_types=[IntegerType(1)], operands=[control1, control2, target])
        else:
            size = control1.type.get_shape()[0]
            super().__init__(result_types=[VectorType(IntegerType(1),[size,])], operands=[control1, control2, target])
        self.traits = [EffectInstance(MemoryEffectKind.READ, self.control1), EffectInstance(MemoryEffectKind.READ, self.control2), EffectInstance(MemoryEffectKind.READ, self.target), EffectInstance(MemoryEffectKind.WRITE, self.res)]

    @staticmethod
    def from_value(control1: SSAValue, control2: SSAValue, target: SSAValue) -> CCNotOp:
        return CCNotOp(control1, control2, target)

@irdl_op_definition
class MeasureOp(IRDLOperation):

    name = "quantum.measure"
    value: Operand = operand_def(IntegerType(1))
    res: OpResult = result_def()
    traits: ClassVar[frozenset[OpTrait]] = traits_def({OpTrait()})

    def __init__(self, value: SSAValue):
        if isinstance(value.type, IntegerType):
            super().__init__(result_types=[IntegerType(1)], operands=[value])
        else:
            size=value.type.get_shape()[0]
            super().__init__(result_types=[VectorType(IntegerType(1),[size,])], operands=[value])
        self.traits = [EffectInstance(MemoryEffectKind.WRITE, self.value)]

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
