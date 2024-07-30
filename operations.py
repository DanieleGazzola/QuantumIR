from xdsl.ir import *
from xdsl.dialects import Dialect
from xdsl.dialects.builtin import *

class InitOperation(Operation):
    name = "my_dialect.init"

    _operands = [OpOperands(IntegerType(1))]
    _attributes = [IntegerAttr(value=0, value_type=IntegerType(1))]  # Default to 0

    def __init__(self, qubit: int, state: int):
        super().__init__(
            operands=[qubit],
            attributes={"state": IntegerAttr(value=state, value_type=IntegerType(1))},
            results=[]
        )

        self.results = [OpResult(IntegerType(1), op=self, index=0)]


class NotOperation(Operation):

    name = "my_dialect.not"

    _operands = [OpOperands(IntegerType(1))]

    def __init__(self, qubit: int):
        super().__init__(
            operands=[qubit],
            results=[]
        )

        self.results = [OpResult(IntegerType(1), op=self, index=0)]

class CNotOperation(Operation):

    name = "my_dialect.cnot"

    _operands = [OpOperands(IntegerType(1)), OpOperands(IntegerType(1))]

    def __init__(self, control: int, target: int):
        super().__init__(
            operands=[control, target],
            results=[]
        )

        self.results = [OpResult(IntegerType(1), op=self, index=0)]

class CCNotOperation(Operation):

    name = "my_dialect.ccnot"

    _operands = [OpOperands(IntegerType(1)), OpOperands(IntegerType(1)), OpOperands(IntegerType(1))]

    def __init__(self, control_1: int,  control_2: int, target: int):
        super().__init__(
            operands=[control_1, control_2, target],
            results=[]
        )

        self.results = [OpResult(IntegerType(1), op=self, index=0)]

class MeasurementOperation(Operation):
    name = "my_dialect.measure"

    _operands = [OpOperands(IntegerType(1))]

    def __init__(self, qubit: int):
        super().__init__(
            operands=[qubit],
            results=[]
        )

        self.results = [OpResult(IntegerType(1), op=self, index=0)] #result of the measurement