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

#from .location import Location

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

    def __init__(self):

        self.module = ModuleOp([])
        self.builder = Builder.at_end(self.module.body.blocks[0])

    def ir_gen_module(self, ast: Root) -> ModuleOp:

        for f in ast.members:
            if (isinstance(f, Instance)):
                self.ir_gen_function(f.body) # passing InstanceBody as it is a function

        return self.module

    def declare(self, var: str, value: SSAValue) -> bool:
        """
        Declare a variable in the current scope, return success if the variable
        wasn't declared yet."""
        assert self.symbol_table is not None
        if var in self.symbol_table:
            return False
        self.symbol_table[var] = value
        return True

    def ir_gen_function(self, body: InstanceBody) -> FuncOp:

        parent_builder = self.builder

        self.symbol_table = ScopedSymbolTable()

        # saves the arguments in input to the function
        proto_args = [member for member in body.members if isinstance(member, Port) and member.direction == "In"]

        # creates a block for the function
        block = Block(arg_types=[IntegerType for _ in range(len(proto_args))])
        self.builder = Builder.at_end(block)

        # Declare all the function arguments in the symbol table.
        for name, value in zip(proto_args, block.args):
            self.declare(name.internalSymbol, value)

        # Emit the body of the function.
        for member in body.members:
            if isinstance(member, ContinuousAssign):
                self.ir_gen_expr(member)




        # TODO here we add the measuremnt operations on outputs
        
        #return_types = []

        # Implicitly return void if no return statement was emitted.
        #return_op = None
        #if block.ops:
        #    last_op = block.last_op
        #    if isinstance(last_op, ReturnOp):
        #        return_op = last_op
        #        if return_op.input is not None:
        #            return_arg = return_op.input
        #            return_types = [return_arg.type]
        #if return_op is None:
        #    self.builder.insert(ReturnOp())

        self.symbol_table = None
        self.builder = parent_builder

        func = self.builder.insert(FuncOp(body.name, Region(block)))

        return func


    



    # assign var = value;
    def ir_gen_init(self, expr: Assignment) -> SSAValue:

        symbol = expr.left.symbol
        value = expr.right.operand.operand.value
         
        init_op = self.builder.insert(InitOp.from_value(IntegerType(int(value))))

        self.declare(symbol, init_op.res)

        return init_op.res
    
    # assign var1 = var2;
    # it works as a CNot if var2 is surely 0
    def ir_gen_copy(self, expr: Assignment) -> SSAValue:

        symbol = expr.left.symbol
        value = self.symbol_table[expr.right.symbol]
         
        copy_op = self.builder.insert(CNotOp.from_value(value))

        self.declare(symbol, copy_op.res)

        return copy_op.res

    # act as a switch for the different types of expressions
    def ir_gen_expr(self, expr: ContinuousAssign) -> SSAValue:
        
        assigment = expr.assignment

        if isinstance(assigment.right, Conversion):
            return self.ir_gen_init(assigment)
        if isinstance(assigment.right, NamedValue):
            return self.ir_gen_copy(assigment)
        else:
            self.error(f"MLIR codegen encountered an unhandled expr kind '{expr.kind}'")


    def error(self, message: str, cause: Exception | None = None) -> NoReturn:
        raise IRGenError(message) from cause
