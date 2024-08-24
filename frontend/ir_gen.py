from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import NoReturn

from xdsl.builder import Builder
from xdsl.dialects.builtin import ModuleOp, TensorType, UnrankedTensorType, f64, IntegerType
from xdsl.ir import Block, Region, SSAValue

from dialect.dialect import (
    InitOp,
    NotOp,
    CNotOp,
    CCNotOp,
    MeasureOp,
    FuncOp,
)

from JSON_to_DataClasses import (
    ASTNode,
    Assignment,
    BinaryOp,
    UnaryOp,
    CompilationUnit,
    Connection,
    ContinuousAssign,
    Conversion,
    ElementSelect,
    EmptyArgument,
    GenerateBlock,
    GenerateBlockArray,
    Genvar,
    Instance,
    InstanceBody,
    IntegerLiteral,
    NamedValue,
    Net,
    NetType,
    Parameter,
    Port,
    PrimitiveInstance,
    Root,
    Variable
)


class IRGenError(Exception):
    pass


@dataclass
class ScopedSymbolTable:
    "A mapping from variable names to SSAValues, append-only"
    table: dict[str, SSAValue] = field(default_factory=dict)

    def __contains__(self, __o: object) -> bool:
        return __o in self.table

    def __getitem__(self, __key: str) -> SSAValue:
        return self.table[__key]

    def __setitem__(self, __key: str, __value: SSAValue) -> None:
        if __key in self:
            raise AssertionError(f"Cannot add value for key {__key} in scope {self}")
        self.table[__key] = __value


@dataclass(init=False)
class IRGen:

    module: ModuleOp

    builder: Builder

    symbol_table: ScopedSymbolTable | None = None

    n: int = 0

    def __init__(self):

        self.module = ModuleOp([])
        self.builder = Builder.at_end(self.module.body.blocks[0])
    
    def declare(self, var: str, value: SSAValue) -> bool:
        
        assert self.symbol_table is not None
        if var in self.symbol_table:
            return False
        self.symbol_table[var] = value
        return True

    # act on the whole tree
    def ir_gen_module(self, ast: Root) -> ModuleOp:

        for f in ast.members:
            if (isinstance(f, Instance)):
                self.ir_gen_function(f.body)

        return self.module

    # act on each function call
    def ir_gen_function(self, body: InstanceBody) -> FuncOp:

        parent_builder = self.builder

        self.symbol_table = ScopedSymbolTable()

        proto_args = [member for member in body.members if isinstance(member, Port) and member.direction == "In"]

        block = Block(arg_types=[IntegerType for _ in range(len(proto_args))])
        self.builder = Builder.at_end(block)

        for name, value in zip(proto_args, block.args):
            self.declare(name.internalSymbol, value)

        for member in body.members:
            if isinstance(member, ContinuousAssign):
                self.ir_gen_expr(member)

        proto_return = [member for member in body.members if isinstance(member, Port) and member.direction == "Out"]

        for var in proto_return:
            self.builder.insert(MeasureOp.from_value(self.symbol_table[var.internalSymbol]))

        self.symbol_table = None
        self.builder = parent_builder

        func = self.builder.insert(FuncOp(body.name, Region(block)))

        return func

    # act as a switch for the different types of expressions
    def ir_gen_expr(self, expr: ASTNode) -> SSAValue:

        if isinstance(expr, ContinuousAssign):
            return self.ir_gen_assign(expr)

    # act as a switch for the different types of assignements
    def ir_gen_assign(self, expr: ContinuousAssign) -> SSAValue:
        
        assignment = expr.assignment

        if isinstance(assignment.right, Conversion): # initialization of a variable
            return self.ir_gen_init(assignment)
        if isinstance(assignment.right, BinaryOp): # binary operation
            return self.ir_gen_bin_op(assignment)
        if isinstance(assignment.right, UnaryOp): # unary operation
            return self.ir_gen_unary_op(assignment)
    
    # initialization of a variable
    # assign var = value;
    def ir_gen_init(self, expr: Assignment) -> SSAValue:

        symbol = expr.left.symbol
        value = expr.right.operand.operand.value
         
        init_op = self.builder.insert(InitOp.from_value(IntegerType(int(value))))

        self.declare(symbol, init_op.res)

        return init_op.res
    
    def ir_gen_unary_op(self, expr: Assignment) -> SSAValue:
            
        symbol = expr.left.symbol

        final_op = self.ir_gen_unary(expr.right)

        self.declare(symbol, final_op.res)

        return final_op.res

    def ir_gen_unary(self, expr: UnaryOp) -> IRDLOperation:

        if expr.op == "BitwiseNot":
            op = self.ir_gen_not(expr)
            return op

    def ir_gen_not(self, expr: UnaryOp) -> IRDLOperation:

        if isinstance(expr.operand, NamedValue):
            operand = self.symbol_table[expr.operand.symbol]
        elif isinstance(expr.operand, BinaryOp):
            operand = self.ir_gen_bin(expr.operand)
            operand = operand.res

        not_op = self.builder.insert(NotOp.from_value(operand))

        return not_op

    # binary operation
    # assign res = value1 ^|& value2;
    def ir_gen_bin_op(self, expr: Assignment) -> SSAValue:

        symbol = expr.left.symbol

        final_op = self.ir_gen_bin(expr.right)

        self.declare(symbol, final_op.res)

        return final_op.res

    def ir_gen_bin(self, expr: BinaryOp) -> IRDLOperation:

        if expr.op == "BinaryXor":

            op = self.ir_gen_xor(expr)
            return op

        if expr.op == "BinaryAnd":

            op = self.ir_gen_and(expr)
            return op
        
        if expr.op == "BinaryOr":

            op = self.ir_gen_or(expr)
            return op

    def ir_gen_xor(self, expr: BinaryOp) -> IRDLOperation:

        # initialize a new qubit
        init_op = self.builder.insert(InitOp.from_value(IntegerType(0)))
            
        # auxiliary SSAValue
        temp_symbol = "temp" + str(self.n)
        self.n += 1

        self.declare(temp_symbol, init_op.res)

        if isinstance(expr.left, NamedValue):
            left = self.symbol_table[expr.left.symbol]
        elif isinstance(expr.left, BinaryOp):
            left = self.ir_gen_bin(expr.left)
            left = left.res

        if isinstance(expr.right, NamedValue):
            right = self.symbol_table[expr.right.symbol]
        elif isinstance(expr.right, BinaryOp):
            right = self.ir_gen_bin(expr.right)
            right = right.res

        cnot_op_1 = self.builder.insert(CNotOp.from_value(left, self.symbol_table[temp_symbol]))

        # auxiliary SSAValue
        temp_symbol = "temp" + str(self.n)
        self.n += 1

        self.declare(temp_symbol, cnot_op_1.res)

        cnot_op_2 = self.builder.insert(CNotOp.from_value(right, self.symbol_table[temp_symbol]))

        return cnot_op_2

    def ir_gen_and(self, expr: BinaryOp) -> IRDLOperation:

        # initialize a new qubit
        init_op = self.builder.insert(InitOp.from_value(IntegerType(0)))
            
        # auxiliary SSAValue
        temp_symbol = "temp" + str(self.n)
        self.n += 1

        self.declare(temp_symbol, init_op.res)

        if isinstance(expr.left, NamedValue):
            left = self.symbol_table[expr.left.symbol]
        elif isinstance(expr.left, BinaryOp):
            left = self.ir_gen_bin(expr.left)
            left = left.res

        if isinstance(expr.right, NamedValue):
            right = self.symbol_table[expr.right.symbol]
        elif isinstance(expr.right, BinaryOp):
            right = self.ir_gen_bin(expr.right)
            right = right.res

        ccnot_op = self.builder.insert(CCNotOp.from_value(left, right, self.symbol_table[temp_symbol]))

        return ccnot_op

    def ir_gen_or(self, expr: BinaryOp) -> IRDLOperation:

        # initialize a new qubit
        init_op = self.builder.insert(InitOp.from_value(IntegerType(0)))
            
        # auxiliary SSAValue
        temp_symbol_0 = "temp" + str(self.n)
        self.n += 1

        self.declare(temp_symbol_0, init_op.res)

        if isinstance(expr.left, NamedValue):
            left = self.symbol_table[expr.left.symbol]
        elif isinstance(expr.left, BinaryOp):
            left = self.ir_gen_bin(expr.left)
            left = left.res

        if isinstance(expr.right, NamedValue):
            right = self.symbol_table[expr.right.symbol]
        elif isinstance(expr.right, BinaryOp):
            right = self.ir_gen_bin(expr.right)
            right = right.res

        not_op_1 = self.builder.insert(NotOp.from_value(left))
        # auxiliary SSAValue
        temp_symbol_2 = "temp" + str(self.n)
        self.n += 1

        self.declare(temp_symbol_2, not_op_1.res)

        not_op_2 = self.builder.insert(NotOp.from_value(right))
        # auxiliary SSAValue
        temp_symbol_3 = "temp" + str(self.n)
        self.n += 1

        self.declare(temp_symbol_3, not_op_2.res)

        ccnot_op = self.builder.insert(CCNotOp.from_value(self.symbol_table[temp_symbol_2], self.symbol_table[temp_symbol_3], self.symbol_table[temp_symbol_0]))
        # auxiliary SSAValue
        temp_symbol_1 = "temp" + str(self.n)
        self.n += 1

        self.declare(temp_symbol_1, ccnot_op.res)

        not_op_3 = self.builder.insert(NotOp.from_value(self.symbol_table[temp_symbol_2]))
        # auxiliary SSAValue
        temp_symbol = "temp" + str(self.n)
        self.n += 1

        self.declare(temp_symbol, not_op_3.res)

        not_op_4 = self.builder.insert(NotOp.from_value(self.symbol_table[temp_symbol_3]))
        # auxiliary SSAValue
        temp_symbol = "temp" + str(self.n)
        self.n += 1

        self.declare(temp_symbol, not_op_4.res)

        not_op_5 = self.builder.insert(NotOp.from_value(self.symbol_table[temp_symbol_1]))
        # auxiliary SSAValue
        temp_symbol = "temp" + str(self.n)
        self.n += 1

        self.declare(temp_symbol, not_op_5.res)

        return not_op_5

    def error(self, message: str, cause: Exception | None = None) -> NoReturn:
        raise IRGenError(message) from cause
