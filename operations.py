from xdsl.ir import *
from xdsl.types import *
from xdsl.dialects import Dialect

class InitOperation(Operation):
    name = "my_dialect.init"

    _operands = [Operand(IntegerType(1))]
    _attributes = [IntegerAttr(name="state", value=0)] #defaul to 0
    _results = [Result(IntegerType(1))]

    def __init__(self, qubit: Value, state: int):
        super().__init__(
            operands=[qubit],
            attributes={"state": IntegerAttr(value=state)},
            results=[IntegerType(1)]
        )

class NotOperation(Operation):

    name = "my_dialect.not"

    _operands = [Operand(IntegerType(1))]
    _results = [OpResult(IntegerType(1))]

    def __init__(self, qubit: Value):
        super().__init__(
            operands=[qubit],
            results=[IntegerType(1)]
        )

class CNotOperation(Operation):

    name = "my_dialect.cnot"

    _operands = [Operand(IntegerType(1)), Operand(IntegerType(1))]
    _results = [OpResult(IntegerType(1))]

    def __init__(self, control: Value, target: Value):
        super().__init__(
            operands=[control, target],
            results=[IntegerType(1)]
        )

class CCNotOperation(Operation):

    name = "my_dialect.ccnot"

    _operands = [Operand(IntegerType(1)), Operand(IntegerType(1)), Operand(IntegerType(1))]
    _results = [OpResult(IntegerType(1))]

    def __init__(self, control_1: Value,  control_2: Value, target: Value):
        super().__init__(
            operands=[control_1, control_2, target],
            results=[IntegerType(1)]
        )

class MeasurementOperation(Operation):
    name = "my_dialect.measure"

    _operands = [Operand(IntegerType(1))]
    _results = [Result(IntegerType(1))] #result of the measurement

    def __init__(self, qubit: Value):
        super().__init__(
            operands=[qubit],
            results=[IntegerType(1)]
        )
    