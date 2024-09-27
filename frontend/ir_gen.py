from __future__ import annotations

from dataclasses import dataclass, field
from typing import NoReturn

from xdsl.builder import Builder
from xdsl.dialects.builtin import ModuleOp, IntegerType, VectorType
from xdsl.ir import Block, Region, SSAValue
from xdsl.dialects import builtin
from xdsl.irdl import IRDLOperation

import re

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
    ProceduralBlock,
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
    Root,
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

    n_qubit: int = 0
    
    def __init__(self):

        self.module = ModuleOp([])
        self.builder = Builder.at_end(self.module.body.blocks[0])
    
    def declare(self, var: str, value: SSAValue) -> bool:
        
        assert self.symbol_table is not None
        if var in self.symbol_table:
            return False
        self.symbol_table[var] = value
        return True
    
    def delete(self,var:str) -> bool:
        assert self.symbol_table is not None
        if var in self.symbol_table:
            self.symbol_table.table.pop(var)
            return True
        return False

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

        # in arguments
        proto_args = [member for member in body.members if isinstance(member, Port) and member.direction == "In"]
        
        arg_types=[]
        for member in proto_args:
            # check if it is a vector
            if "[" in member.type and "]" in member.type:
                match = re.match(r"(\w+)\[(\d+):(\d+)\]", member.type) # regex to match the vector type and size
                if match:
                    # Extract the keyword, high index, and low index
                    keyword = match.group(1)  # The keyword part (e.g., "logic", "wire", "reg")
                    high_index = int(match.group(2))
                    low_index = int(match.group(3))
                    size = high_index - low_index + 1

                    element_type = IntegerType(1) #type of the elements in the vector
                    arg_types.append(builtin.VectorType(element_type, [size,]))
            else:
                # it's a single bit
                arg_types.append(builtin.i1)

        block = Block(arg_types=arg_types)
        self.builder = Builder.at_end(block)

        for name, value in zip(proto_args, block.args):
            value._name = "q"+str(self.n_qubit)+"_0"
            self.n_qubit += 1
            self.declare(name.internalSymbol, value)

        # create function body computations
        for member in body.members:
                self.ir_gen_expr(member)

        proto_return = [member for member in body.members if isinstance(member, Port) and member.direction == "Out"]
    
        for var in proto_return:
            measure = self.builder.insert(MeasureOp.from_value(self.symbol_table[var.internalSymbol]))
            measure.res._name = str(self.symbol_table[var.internalSymbol]._name[:-1]) + str(int(self.symbol_table[var.internalSymbol]._name[-1]) + 1)

        self.symbol_table = None
        self.builder = parent_builder

        func = self.builder.insert(FuncOp(body.name, Region(block)))

        return func

    # act as a switch for the different types of expressions
    def ir_gen_expr(self, expr: ASTNode) -> SSAValue:
        
        # the two ways one can write combinatorial assignments in SystemVerilog
        if isinstance(expr, ContinuousAssign):
            return self.ir_gen_assign(expr.assignment)
        if isinstance(expr, ProceduralBlock):
            return self.ir_gen_procedural_block(expr)

    def ir_gen_procedural_block(self, expr: ProceduralBlock) -> SSAValue:
            # extract the block and the statement containing the operations
            block = expr.body
            statement = block.body
            if isinstance(statement, list):
                for s in statement:
                    self.ir_gen_assign(s.expr)
            else:
                self.ir_gen_assign(statement.expr)

    # act as a switch for the different types of assignements
    def ir_gen_assign(self, assignment: Assignment) -> SSAValue:

        if isinstance(assignment.right, Conversion): # initialization of a variable
            return self.ir_gen_init(assignment)
        if isinstance(assignment.right, BinaryOp): # binary operation
            return self.ir_gen_bin_op(assignment)
        if isinstance(assignment.right, UnaryOp): # unary operation
            return self.ir_gen_unary_op(assignment)
    
    # initialization of a 0 qubit
    # assign var = value;
    def ir_gen_init(self,) -> SSAValue:

        init_op = self.builder.insert(InitOp.from_value(IntegerType(1)))

        init_op.res._name="q"+str(self.n_qubit)+"_0"
        self.n_qubit += 1

        self.declare(init_op.res._name, init_op.res)

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
            self.delete(expr.operand.symbol)

        elif isinstance(expr.operand, BinaryOp):
            operand = self.ir_gen_bin(expr.operand)
            operand = operand.res


        not_op = self.builder.insert(NotOp.from_value(operand))

        not_op.res._name = operand._name[:-1] + str(int(operand._name[-1]) + 1)

        self.declare(expr.operand.symbol, not_op.res)
        
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
        
        raise IRGenError(f"Unknown binary operation {expr.op}")

    def ir_gen_xor(self, expr: BinaryOp) -> IRDLOperation:

        if isinstance(expr.left, NamedValue):
            left = self.symbol_table[expr.left.symbol]
            # if the qubit has been negated, and is searching for the original qubit
            # we negate it again
            if int(left._name[-1])%2 != 0:
                self.delete(expr.left.symbol)
                left_new = self.builder.insert(NotOp.from_value(left))
                left_new.res._name = left._name[:-1]+str(int(left._name[-1])+1)
                self.declare(expr.left.symbol, left_new.res)
                left = left_new.res
        elif isinstance(expr.left, BinaryOp):
            left = self.ir_gen_bin(expr.left)
            left = left.res
        elif isinstance(expr.left, UnaryOp):
            left = self.ir_gen_unary(expr.left)
            left = left.res
                
        if isinstance(expr.right, NamedValue):
            right = self.symbol_table[expr.right.symbol]
            # if the qubit has been negated, and is searching for the original qubit
            # we negate it again
            if int(right._name[-1])%2 != 0:
                self.delete(expr.right.symbol)
                right_new = self.builder.insert(NotOp.from_value(right))
                right_new.res._name = right._name[:-1]+str(int(right._name[-1])+1)
                self.declare(expr.right.symbol, right_new.res)
                right = right_new.res
        elif isinstance(expr.right, BinaryOp):
            right = self.ir_gen_bin(expr.right)
            right = right.res
        elif isinstance(expr.right, UnaryOp):
            right = self.ir_gen_unary(expr.right)
            right = right.res
        
        # controllo per xor consecutivi da fare in place.
        # possibile solo se right e left non sono contemporaneamente named value. In quel caso allochiamo normalmente.
        check1 = False
        check2 = False
        if isinstance(expr.right,NamedValue) or expr.right.op == "BinaryXor" or expr.right.op == "BitWiseNot":
            check1 = True
        if isinstance(expr.left,NamedValue) or expr.left.op == "BinaryXor" or expr.left.op == "BitWiseNot":
            check2 = True
        if isinstance(expr.left,NamedValue) and isinstance(expr.right,NamedValue):
            check1 = False
            check2 = False

        # se non è possibile alloca un nuovo qubit
        if not(check1 and check2):
            # initialize a new qubit or a new qubit register
            if "[" in expr.type and "]" in expr.type:
                    match = re.match(r"(\w+)\[(\d+):(\d+)\]", expr.type) # regex to match the vector type and size
                    if match:
                        # Extract the keyword, high index, and low index
                        high_index = int(match.group(2))
                        low_index = int(match.group(3))
                        size = high_index - low_index + 1
                    element_type= IntegerType(1)
                    init_op = self.builder.insert(InitOp.from_value(VectorType(element_type,[size,])))
            else:
                init_op = self.builder.insert(InitOp.from_value(IntegerType(1)))

            
            init_op.res._name="q"+str(self.n_qubit)+"_0"
            self.n_qubit += 1
            
            self.declare(init_op.res._name, init_op.res)
        
            cnot_op_1 = self.builder.insert(CNotOp.from_value(left, self.symbol_table[init_op.res._name]))

            # leggibilità ciaone
            cnot_op_1.res._name = init_op.res._name[:-1]+str(int(init_op.res._name[-1]) + 1)
            name = cnot_op_1.res._name

            self.declare(cnot_op_1.res._name, cnot_op_1.res)
        else:
            name = left._name

        cnot_op_2 = self.builder.insert(CNotOp.from_value(right, self.symbol_table[name])) 

        cnot_op_2.res._name = name[:-1]+str(int(name[-1]) + 1)

        self.declare(cnot_op_2.res._name, cnot_op_2.res)

        return cnot_op_2

    def ir_gen_and(self, expr: BinaryOp) -> IRDLOperation:
        # initialize a new qubit or a new qubit register
        if "[" in expr.type and "]" in expr.type:
                match = re.match(r"(\w+)\[(\d+):(\d+)\]", expr.type) # regex to match the vector type and size
                if match:
                    # Extract the keyword, high index, and low index
                    keyword = match.group(1)  # The keyword part (e.g., "logic", "wire", "reg")
                    high_index = int(match.group(2))
                    low_index = int(match.group(3))
                    size = high_index - low_index + 1
                element_type= IntegerType(1)
                init_op = self.builder.insert(InitOp.from_value(VectorType(element_type,[size,])))
        else:
            init_op = self.builder.insert(InitOp.from_value(IntegerType(1)))

        init_op.res._name="q"+str(self.n_qubit)+"_0"
        self.n_qubit += 1

        self.declare(init_op.res._name, init_op.res)

        if isinstance(expr.left, NamedValue):
            left = self.symbol_table[expr.left.symbol]
            # if the qubit has been negated, and is searching for the original qubit
            # we negate it again
            if int(left._name[-1])%2 != 0:
                self.delete(expr.left.symbol)
                left_new = self.builder.insert(NotOp.from_value(left))
                left_new.res._name = left._name[:-1]+str(int(left._name[-1])+1)
                self.declare(expr.left.symbol, left_new.res)
                left = left_new.res
        elif isinstance(expr.left, BinaryOp):
            left = self.ir_gen_bin(expr.left)
            left = left.res
        elif isinstance(expr.left, UnaryOp):
            left = self.ir_gen_unary(expr.left)
            left = left.res

        if isinstance(expr.right, NamedValue):
            right = self.symbol_table[expr.right.symbol]
            # if the qubit has been negated, and is searching for the original qubit
            # we negate it again
            if int(right._name[-1])%2 != 0:
                self.delete(expr.right.symbol)
                right_new = self.builder.insert(NotOp.from_value(right))
                right_new.res._name = right._name[:-1]+str(int(right._name[-1])+1)
                self.declare(expr.right.symbol, right_new.res)
                right = right_new.res
        elif isinstance(expr.right, BinaryOp):
            right = self.ir_gen_bin(expr.right)
            right = right.res
        elif isinstance(expr.right, UnaryOp):
            right = self.ir_gen_unary(expr.right)
            right = right.res

        
        ccnot_op = self.builder.insert(CCNotOp.from_value(left, right, self.symbol_table[init_op.res._name]))

        ccnot_op.res._name = init_op.res._name[:-1]+str(int(init_op.res._name[-1]) + 1)
        self.declare(ccnot_op.res._name, ccnot_op.res)
        
        return ccnot_op

    def ir_gen_or(self, expr: BinaryOp) -> IRDLOperation:

        # initialize a new qubit or a new qubit register
        if "[" in expr.type and "]" in expr.type:
                match = re.match(r"(\w+)\[(\d+):(\d+)\]", expr.type) # regex to match the vector type and size
                if match:
                    # Extract the keyword, high index, and low index
                    keyword = match.group(1)  # The keyword part (e.g., "logic", "wire", "reg")
                    high_index = int(match.group(2))
                    low_index = int(match.group(3))
                    size = high_index - low_index + 1
                element_type= IntegerType(1)
                init_op = self.builder.insert(InitOp.from_value(VectorType(element_type,[size,])))
        else:
            init_op = self.builder.insert(InitOp.from_value(IntegerType(1)))
            
        # auxiliary SSAValue
        init_op.res._name="q"+str(self.n_qubit)+"_0"
        self.n_qubit += 1

        self.declare(init_op.res._name, init_op.res)

        if isinstance(expr.left, NamedValue):
            left = self.symbol_table[expr.left.symbol]
            # if the qubit has been negated, and is searching for the original qubit
            # we negate it again
            if int(left._name[-1])%2 != 0:
                self.delete(expr.left.symbol)
                left_new = self.builder.insert(NotOp.from_value(left))
                left_new.res._name = left._name[:-1]+str(int(left._name[-1])+1)
                self.declare(expr.left.symbol, left_new.res)
                left = left_new.res
        elif isinstance(expr.left, BinaryOp):
            left = self.ir_gen_bin(expr.left)
            left = left.res
        elif isinstance(expr.left, UnaryOp):
            left = self.ir_gen_unary(expr.left)
            left = left.res


        if isinstance(expr.right, NamedValue):
            right = self.symbol_table[expr.right.symbol]
            # if the qubit has been negated, and is searching for the original qubit
            # we negate it again
            if int(right._name[-1])%2 != 0:
                self.delete(expr.right.symbol)
                right_new = self.builder.insert(NotOp.from_value(right))
                right_new.res._name = right._name[:-1]+str(int(right._name[-1])+1)
                self.declare(expr.right.symbol, right_new.res)
                right = right_new.res
        elif isinstance(expr.right, BinaryOp):
            right = self.ir_gen_bin(expr.right)
            right = right.res
        elif isinstance(expr.right, UnaryOp):
            right = self.ir_gen_unary(expr.right)
            right = right.res
        
        not_op_1 = self.builder.insert(NotOp.from_value(left))
        not_op_1.res._name = left._name[:-1]+str(int(left._name[-1]) + 1)

        self.declare(not_op_1.res._name, not_op_1.res)

        not_op_2 = self.builder.insert(NotOp.from_value(right))
        not_op_2.res._name = right._name[:-1]+str(int(right._name[-1]) + 1)

        self.declare(not_op_2.res._name, not_op_2.res)

        ccnot_op = self.builder.insert(CCNotOp.from_value(self.symbol_table[not_op_1.res._name], self.symbol_table[not_op_2.res._name], self.symbol_table[init_op.res._name]))
        ccnot_op.res._name = init_op.res._name[:-1]+str(int(init_op.res._name[-1]) + 1)

        self.declare(ccnot_op.res._name, ccnot_op.res)

        not_op_3 = self.builder.insert(NotOp.from_value(self.symbol_table[not_op_1.res._name]))
        not_op_3.res._name = not_op_1.res._name[:-1]+str(int(not_op_1.res._name[-1]) + 1)

        self.declare(not_op_3.res._name, not_op_3.res)

        not_op_4 = self.builder.insert(NotOp.from_value(self.symbol_table[not_op_2.res._name]))
        not_op_4.res._name = not_op_2.res._name[:-1]+str(int(not_op_2.res._name[-1]) + 1)

        self.declare(not_op_4.res._name, not_op_4.res)

        not_op_5 = self.builder.insert(NotOp.from_value(self.symbol_table[ccnot_op.res._name]))
        not_op_5.res._name = ccnot_op.res._name[:-1]+str(int(ccnot_op.res._name[-1]) + 1)

        self.declare(not_op_5.res._name, not_op_5.res)

        return not_op_5

    def error(self, message: str, cause: Exception | None = None) -> NoReturn:
        raise IRGenError(message) from cause
