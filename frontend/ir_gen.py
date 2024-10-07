from __future__ import annotations

from dataclasses import dataclass, field
from typing import NoReturn

from xdsl.builder import Builder
from xdsl.dialects import builtin
from xdsl.dialects.builtin import ModuleOp, IntegerType, VectorType
from xdsl.ir import Block, Region, SSAValue
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
    ContinuousAssign,
    Conversion,
    Instance,
    InstanceBody,
    NamedValue,
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

    # stores the active SSAValues
    # variables coming from the verilog have as key their symbol(1234567890 a), temporary SSAValues have as key their name(q4_7)
    symbol_table: ScopedSymbolTable | None = None

    n_qubit: int = 0  # n_qubits that need to be used when generating the first IR
    n_args: int = 0   # n_args taken as input from the verilog
    
    def __init__(self):

        self.module = ModuleOp([])
        self.builder = Builder.at_end(self.module.body.blocks[0])
    
    # add a new entry in the symbol_table
    def declare(self, var: str, value: SSAValue) -> bool:
        
        assert self.symbol_table is not None
        if var in self.symbol_table:
            return False
        self.symbol_table[var] = value
        return True
    
    # delete an entry from the symbol_table
    def delete(self, var: str) -> bool:
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
        
        # parsing input arguments
        arg_types=[]
        for member in proto_args:
            # check if it is a vector
            if "[" in member.type and "]" in member.type:
                match = re.match(r"(\w+)\[(\d+):(\d+)\]", member.type) # regex to match the vector type and size
                if match:
                    # Extract the high index, and low index
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
        self.n_args = len(block.args)

        # declare each input argument as a new qubit
        for name, value in zip(proto_args, block.args):
            value._name = "q" + str(self.n_qubit) + "_0"
            self.n_qubit += 1
            self.declare(name.internalSymbol, value)

        # create function body computations
        for member in body.members:
                self.ir_gen_expr(member)

        # out arguments
        proto_return = [member for member in body.members if isinstance(member, Port) and member.direction == "Out"]

        # add a MeasureOp for each output argument of the function
        for var in proto_return:
            measure = self.builder.insert(MeasureOp.from_value(self.symbol_table[var.internalSymbol])).res
            measure._name = str(self.symbol_table[var.internalSymbol]._name.split('_')[0]) + "_" + str(int(self.symbol_table[var.internalSymbol]._name.split('_')[1]) + 1)

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
            return self.ir_gen_init()
        if isinstance(assignment.right, BinaryOp):   # binary operation
            return self.ir_gen_bin_op(assignment)
        if isinstance(assignment.right, UnaryOp):    # unary operation
            return self.ir_gen_unary_op(assignment)
    
    # initialization of a new qubit
    def ir_gen_init(self) -> SSAValue:

        # insert the InitOp
        init_op = self.builder.insert(InitOp.from_value(IntegerType(1))).res

        # set the name of the qubit
        init_op._name = "q" + str(self.n_qubit) + "_0"
        self.n_qubit += 1

        # add the new SSAValue(qubit) in the symbol_table
        self.declare(init_op._name, init_op)

        return init_op
    
    # generation of a unary operation coming from verilog
    def ir_gen_unary_op(self, expr: Assignment) -> SSAValue:
        
        # symbol coming from verilog
        symbol = expr.left.symbol

        final_op = self.ir_gen_unary(expr.right)

        # add the SSAValue to the symbol_table
        self.declare(symbol, final_op)
        
        return final_op

    # generation of a unary operation
    def ir_gen_unary(self, expr: UnaryOp) -> SSAValue:
        
        if expr.op == "BitwiseNot":     # not operation
            op = self.ir_gen_not(expr)
            return op
        
    # generation of a not operation
    def ir_gen_not(self, expr: UnaryOp) -> SSAValue:

        if isinstance(expr.operand, NamedValue):                # not of a variable of the verilog (internal variable or input argument)
            operand = self.symbol_table[expr.operand.symbol]
            self.delete(expr.operand.symbol)

        elif isinstance(expr.operand, BinaryOp):                # not of a binary operation
            operand = self.ir_gen_bin(expr.operand)
            self.delete(operand._name)
        
        # insert the NotOp
        not_op = self.builder.insert(NotOp.from_value(operand)).res

        # set the name of the SSAValue adding 1 to the temporal state of the qubit
        not_op._name = operand._name.split('_')[0] + "_" + str(int(operand._name.split('_')[1]) + 1)

        # add the SSAValue to the symbol_table
        if isinstance(expr.operand, NamedValue):
            self.declare(expr.operand.symbol, not_op) # key is the symbol they have in verilog
        elif isinstance(expr.operand, BinaryOp):
            self.declare(operand._name, not_op)       # key is the name of the SSAValue
        
        return not_op

    # generation of a binary operation from verilog
    def ir_gen_bin_op(self, expr: Assignment) -> SSAValue:
        
        # symbol coming from verilog
        symbol = expr.left.symbol

        # generate the binary operation
        final_op = self.ir_gen_bin(expr.right)

        # add the SSAValue to the symbol_table
        self.declare(symbol, final_op)

        return final_op

    # switch for the different types of binary operations
    def ir_gen_bin(self, expr: BinaryOp) -> SSAValue:

        if expr.op == "BinaryXor":
            op = self.ir_gen_xor(expr) # xor operation
        elif expr.op == "BinaryAnd":
            op = self.ir_gen_and(expr) # and operation
        elif expr.op == "BinaryOr":
            op = self.ir_gen_or(expr)  # or operation
        else:
            raise IRGenError(f"Unknown binary operation {expr.op}")
        
        return op

    def ir_gen_named_value(self, expr: NamedValue) -> SSAValue:
        operand = self.symbol_table[expr.symbol]
        # if the qubit has been negated, and is searching for the original qubit
        # we negate it again
        if int(operand._name[-1])%2 != 0 and int(operand._name[1]) < self.n_args:
            self.delete(expr.symbol)
            operand_new = self.builder.insert(NotOp.from_value(operand)).res
            operand_new._name = operand._name.split('_')[0] + "_" + str(int(operand._name.split('_')[1]) + 1)
            self.declare(expr.symbol, operand_new)
            operand = operand_new
        
        return operand
    
    def ir_gen_operand(self, expr: BinaryOp, side: str) -> SSAValue:

        if side == "left":
            operand = expr.left
        elif side == "right":
            operand = expr.right

        if isinstance(operand, NamedValue):
            result = self.ir_gen_named_value(operand)
        elif isinstance(operand, BinaryOp):
            result = self.ir_gen_bin(operand)
        elif isinstance(operand, UnaryOp):
            if isinstance(operand.operand, NamedValue):
                result = self.symbol_table[operand.operand.symbol]
            if not(isinstance(operand.operand, NamedValue) and int(result._name[1]) < self.n_args and int(result._name[-1])%2 != 0):
                result = self.ir_gen_unary(operand)
        
        return result
    
    def restore_qubit(self, expr: BinaryOp, side: str) -> None:

        if side == "left":
            operand = expr.left
        elif side == "right":
            operand = expr.right

        if isinstance(operand.operand, NamedValue):
            op = self.symbol_table[operand.operand.symbol]
            if int(op._name[1]) >= self.n_args:
                self.delete(operand.operand.symbol)
                op_new = self.builder.insert(NotOp.from_value(op)).res
                op_new._name = op._name.split('_')[0] + "_" + str(int(op._name.split('_')[1]) + 1)
                self.declare(operand.operand.symbol, op_new)

    def ir_gen_new_qubit(self, expr: BinaryOp) -> SSAValue:

        # initialize a new qubit or a new qubit register
        if "[" in expr.type and "]" in expr.type:
            match = re.match(r"(\w+)\[(\d+):(\d+)\]", expr.type) # regex to match the vector type and size
            if match:
                # Extract the keyword, high index, and low index
                high_index = int(match.group(2))
                low_index = int(match.group(3))
                size = high_index - low_index + 1
            element_type = IntegerType(1)
            init_op = self.builder.insert(InitOp.from_value(VectorType(element_type,[size,]))).res
        else:
            init_op = self.builder.insert(InitOp.from_value(IntegerType(1))).res

        return init_op

    # generation of a xor operation
    def ir_gen_xor(self, expr: BinaryOp) -> SSAValue:
        
        # set left operand
        left = self.ir_gen_operand(expr, "left")

        # set right operand
        right = self.ir_gen_operand(expr, "right")
        
        # check if we can do the xor in place
        # we can do it only if the two operands are not both named values
        # also we need left and right to be either a NamedValue or a Xor operation or a Not operation
        check1 = (isinstance(expr.right, NamedValue) or expr.right.op == "BinaryXor" or expr.right.op == "BitWiseNot") # need to be True
        check2 = (isinstance(expr.left, NamedValue) or expr.left.op == "BinaryXor" or expr.left.op == "BitWiseNot")    # need to be True
        check3 = (isinstance(expr.right, NamedValue) and isinstance(expr.left, NamedValue))                            # need to be False

        # se non è possibile alloca un nuovo qubit
        if not(check1 and check2 and not check3):

            init_op = self.ir_gen_new_qubit(expr)
            init_op._name = "q" + str(self.n_qubit) + "_0"
            self.n_qubit += 1
            
            self.declare(init_op._name, init_op)
        
            cnot_op_1 = self.builder.insert(CNotOp.from_value(left, self.symbol_table[init_op._name])).res
            cnot_op_1._name = init_op._name.split('_')[0] + "_" + str(int(init_op._name.split('_')[1]) + 1)
            name = cnot_op_1._name

            self.declare(cnot_op_1._name, cnot_op_1)
        else:
            name = left._name

        cnot_op_2 = self.builder.insert(CNotOp.from_value(right, self.symbol_table[name])).res
        cnot_op_2._name = name.split('_')[0] + "_" + str(int(name.split('_')[1]) + 1)
        self.declare(cnot_op_2._name, cnot_op_2)

        if isinstance(expr.left, UnaryOp):
            self.restore_qubit(expr, "left")

        if isinstance(expr.right, UnaryOp):
            self.restore_qubit(expr, "right")

        return cnot_op_2

    def ir_gen_and(self, expr: BinaryOp) -> SSAValue:

        # initialize a new qubit or a new qubit register
        init_op = self.ir_gen_new_qubit(expr)
        init_op._name = "q" + str(self.n_qubit) + "_0"
        self.n_qubit += 1

        self.declare(init_op._name, init_op)

        # set left operand
        left = self.ir_gen_operand(expr, "left")

        # set right operand
        right = self.ir_gen_operand(expr, "right")
        
        ccnot_op = self.builder.insert(CCNotOp.from_value(left, right, self.symbol_table[init_op._name])).res
        ccnot_op._name = init_op._name.split('_')[0] + "_" + str(int(init_op._name.split('_')[1]) + 1)
        self.declare(ccnot_op._name, ccnot_op)

        if isinstance(expr.left, UnaryOp):
            self.restore_qubit(expr, "left")

        if isinstance(expr.right, UnaryOp):
            self.restore_qubit(expr, "right")
        
        return ccnot_op
    
    def ir_gen_operand_or(self, expr: BinaryOp, side: str) -> str:

        if side == "left":
            operand = expr.left
        elif side == "right":
            operand = expr.right

        if isinstance(operand, NamedValue):
            op = self.symbol_table[operand.symbol]
            # if the qubit has been negated, and is searching for the original qubit
            # we negate it again
            if int(op._name[-1])%2 != 0 and int(op._name[1]) < self.n_args:
                self.delete(operand.symbol)
                op_new = self.builder.insert(NotOp.from_value(op)).res
                op_new._name = op._name.split('_')[0] + "_" + str(int(op._name.split('_')[1]) + 1)
                self.declare(operand.symbol, op_new)
                op = op_new
            self.delete(operand.symbol)
            not_op_1 = self.builder.insert(NotOp.from_value(op)).res
            not_op_1._name = op._name.split('_')[0] + "_" + str(int(op._name.split('_')[1]) + 1)
            name = operand.symbol
        else:
            if isinstance(operand, BinaryOp):
                op = self.ir_gen_bin(operand)
                name = op._name
                not_op_1 = self.builder.insert(NotOp.from_value(op)).res
                not_op_1._name = op._name.split('_')[0] + "_" + str(int(op._name.split('_')[1]) + 1)
                name = not_op_1._name
            elif isinstance(operand, UnaryOp):
                unary_operand = operand.operand
                if isinstance(unary_operand, NamedValue):
                    op = self.symbol_table[unary_operand.symbol]
                if not(isinstance(unary_operand, NamedValue) and int(op._name[1]) < self.n_args and int(op._name[-1])%2 != 0):
                    op = self.ir_gen_unary(operand)
                if isinstance(unary_operand, NamedValue):
                    self.delete(unary_operand.symbol)
                    not_op_1 = self.builder.insert(NotOp.from_value(op)).res
                    not_op_1._name = op._name.split('_')[0] + "_" + str(int(op._name.split('_')[1]) + 1)
                    name = unary_operand.symbol
                else:
                    not_op_1 = self.builder.insert(NotOp.from_value(op)).res
                    not_op_1._name = op._name.split('_')[0] + "_" + str(int(op._name.split('_')[1]) + 1)
                    name = not_op_1._name
        
        self.declare(name, not_op_1)
        
        return name

    def ir_gen_or(self, expr: BinaryOp) -> SSAValue:

        init_op = self.ir_gen_new_qubit(expr)
            
        # auxiliary SSAValue
        init_op._name= "q" + str(self.n_qubit) + "_0"
        self.n_qubit += 1

        self.declare(init_op._name, init_op)
        
        left_name = self.ir_gen_operand_or(expr, "left")

        right_name = self.ir_gen_operand_or(expr, "right")

        ccnot_op = self.builder.insert(CCNotOp.from_value(self.symbol_table[left_name], self.symbol_table[right_name], self.symbol_table[init_op._name])).res
        ccnot_op._name = init_op._name.split('_')[0] + "_" + str(int(init_op._name.split('_')[1]) + 1)

        self.declare(ccnot_op._name, ccnot_op)
        
        name = self.symbol_table[left_name]._name
        not_op_3 = self.builder.insert(NotOp.from_value(self.symbol_table[left_name])).res
        not_op_3._name = name.split('_')[0] + "_" + str(int(name.split('_')[1]) + 1)
        self.delete(left_name)

        if isinstance(expr.left, NamedValue) or (isinstance(expr.left, UnaryOp) and isinstance(expr.left.operand, NamedValue)):
            self.declare(left_name, not_op_3)
        else:
            self.declare(not_op_3._name, not_op_3)

        name = self.symbol_table[right_name]._name
        not_op_4 = self.builder.insert(NotOp.from_value(self.symbol_table[right_name])).res
        not_op_4._name = name.split('_')[0] + "_" + str(int(name.split('_')[1]) + 1)
        self.delete(right_name)

        if isinstance(expr.right, NamedValue) or (isinstance(expr.left, UnaryOp) and isinstance(expr.left.operand, NamedValue)):
            self.declare(right_name, not_op_4)
        else:
            self.declare(not_op_4._name, not_op_4)

        not_op_5 = self.builder.insert(NotOp.from_value(self.symbol_table[ccnot_op._name])).res
        not_op_5._name = ccnot_op._name.split('_')[0] + "_" + str(int(ccnot_op._name.split('_')[1]) + 1)

        self.declare(not_op_5._name, not_op_5)

        if isinstance(expr.left, UnaryOp):
            self.restore_qubit(expr, "left")

        if isinstance(expr.right, UnaryOp):
            self.restore_qubit(expr, "right")

        return not_op_5

    def error(self, message: str, cause: Exception | None = None) -> NoReturn:
        raise IRGenError(message) from cause
