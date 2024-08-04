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
        
        assigment = expr.assignment

        if isinstance(assigment.right, Conversion): # initialization of a variable
            return self.ir_gen_init(assigment)
        if isinstance(assigment.right, BinaryOp): # binary operation
            return self.ir_gen_bin_op(assigment)
    
    # initialization of a variable
    # assign var = value;
    def ir_gen_init(self, expr: Assignment) -> SSAValue:

        symbol = expr.left.symbol
        value = expr.right.operand.operand.value
         
        init_op = self.builder.insert(InitOp.from_value(IntegerType(int(value))))

        self.declare(symbol, init_op.res)

        return init_op.res
    
    # binary operation
    # assign res = value1 ^|& value2;
    def ir_gen_bin_op(self, expr: Assignment) -> SSAValue:

        symbol = expr.left.symbol
        
        if expr.right.op == "BinaryXor":

            # initialize a new qubit
            init_op = self.builder.insert(InitOp.from_value(IntegerType(0)))
            
            # auxiliary SSAValue
            temp_symbol = "temp" + str(self.n)
            self.n += 1

            self.declare(temp_symbol, init_op.res)

            if isinstance(expr.right.left, NamedValue):
                left = self.symbol_table[expr.right.left.symbol]
            #elif isinstance(expr.right.left, BinaryOp):
            #    left = 

            if isinstance(expr.right.right, NamedValue):
                right = self.symbol_table[expr.right.right.symbol]
            #elif isinstance(expr.right.right, BinaryOp):
            #    right =

            cnot_op_1 = self.builder.insert(CNotOp.from_value(left, self.symbol_table[temp_symbol]))

            # auxiliary SSAValue
            temp_symbol = "temp" + str(self.n)
            self.n += 1

            self.declare(temp_symbol, cnot_op_1.res)

            cnot_op_2 = self.builder.insert(CNotOp.from_value(right, self.symbol_table[temp_symbol]))

            self.declare(symbol, cnot_op_2.res)

        return cnot_op_2.res


    def error(self, message: str, cause: Exception | None = None) -> NoReturn:
        raise IRGenError(message) from cause
