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
        initOp_ssa = self.builder.insert(InitOp.from_value(IntegerType(1))).res

        # set the name of the qubit
        initOp_ssa._name = "q" + str(self.n_qubit) + "_0"
        self.n_qubit += 1

        # add the new SSAValue(qubit) in the symbol_table
        self.declare(initOp_ssa._name, initOp_ssa)

        return initOp_ssa
    
    # generation of a unary operation coming from verilog
    def ir_gen_unary_op(self, expr: Assignment) -> SSAValue:
        
        # symbol coming from verilog
        symbol = expr.left.symbol

        final_op_ssa = self.ir_gen_unary(expr.right)

        # add the SSAValue to the symbol_table
        self.declare(symbol, final_op_ssa)
        
        return final_op_ssa

    # generation of a unary operation
    def ir_gen_unary(self, expr: UnaryOp) -> SSAValue:
        
        if expr.op == "BitwiseNot":     # not operation
            unary_ssa = self.ir_gen_not(expr)
            return unary_ssa
        else:
            raise IRGenError(f"Unknown unary operation {expr.op}")
        
    # generation of a not operation
    def ir_gen_not(self, expr: UnaryOp) -> SSAValue:

        if isinstance(expr.operand, NamedValue):                # not of a variable of the verilog (internal variable or input argument)
            operand = self.symbol_table[expr.operand.symbol]
            self.delete(expr.operand.symbol)

        elif isinstance(expr.operand, BinaryOp):                # not of a binary operation
            operand = self.ir_gen_bin(expr.operand)
            self.delete(operand._name)
        
        # insert the NotOp
        notOp_ssa = self.builder.insert(NotOp.from_value(operand)).res

        # set the name of the SSAValue adding 1 to the temporal state of the qubit
        notOp_ssa._name = operand._name.split('_')[0] + "_" + str(int(operand._name.split('_')[1]) + 1)

        # add the SSAValue to the symbol_table
        if isinstance(expr.operand, NamedValue):
            self.declare(expr.operand.symbol, notOp_ssa) # key is the symbol they have in verilog
        elif isinstance(expr.operand, BinaryOp):
            self.declare(operand._name, notOp_ssa)       # key is the name of the SSAValue
        
        return notOp_ssa

    # generation of a binary operation from verilog
    def ir_gen_bin_op(self, expr: Assignment) -> SSAValue:
        
        # symbol coming from verilog
        symbol = expr.left.symbol

        # generate the binary operation
        final_op_ssa = self.ir_gen_bin(expr.right)

        # add the SSAValue to the symbol_table
        self.declare(symbol, final_op_ssa)

        return final_op_ssa

    # switch for the different types of binary operations
    def ir_gen_bin(self, expr: BinaryOp) -> SSAValue:

        if expr.op == "BinaryXor":
            result_ssa = self.ir_gen_xor(expr) # xor operation
        elif expr.op == "BinaryAnd":
            result_ssa = self.ir_gen_and(expr) # and operation
        elif expr.op == "BinaryOr":
            result_ssa = self.ir_gen_or(expr)  # or operation
        else:
            raise IRGenError(f"Unknown binary operation {expr.op}")
        
        return result_ssa

    def ir_gen_named_value(self, expr: NamedValue) -> SSAValue:
        namedValue_ssa = self.symbol_table[expr.symbol]
        # if the qubit has been negated, and it needs the original qubit
        # we negate it again
        if int(namedValue_ssa._name[-1])%2 != 0 and int(namedValue_ssa._name[1]) < self.n_args: # odd status number and an input argument
            self.delete(expr.symbol)
            not_ssa = self.builder.insert(NotOp.from_value(namedValue_ssa)).res
            not_ssa._name = namedValue_ssa._name.split('_')[0] + "_" + str(int(namedValue_ssa._name.split('_')[1]) + 1)
            self.declare(expr.symbol, not_ssa)
            namedValue_ssa = not_ssa
        
        return namedValue_ssa
    
    def ir_gen_operand(self, expr: BinaryOp, side: str) -> SSAValue:

        if side == "left":
            operand = expr.left
        elif side == "right":
            operand = expr.right

        if isinstance(operand, NamedValue):
            result_ssa = self.ir_gen_named_value(operand)
        elif isinstance(operand, BinaryOp):
            result_ssa = self.ir_gen_bin(operand)
        elif isinstance(operand, UnaryOp):
            if isinstance(operand.operand, NamedValue):
                result_ssa = self.symbol_table[operand.operand.symbol]
            if not(isinstance(operand.operand, NamedValue) and int(result_ssa._name[1]) < self.n_args and int(result_ssa._name[-1])%2 != 0):
                result_ssa = self.ir_gen_unary(operand)
        
        self.declare(result_ssa._name, result_ssa)
        
        return result_ssa
    
    # every time we negate a qubit, after the operation we restore its original state
    # by negating it again. Only if the qubit is not an input argument.
    # if it's an input argument we do it in the gen_named_value function
    def restore_qubit(self, expr: BinaryOp, side: str) -> None:

        if side == "left":
            binaryOp_operand = expr.left
        elif side == "right":
            binaryOp_operand = expr.right
        
        sub_operand = binaryOp_operand.operand
        if isinstance(sub_operand, NamedValue):
            sub_operand_ssa = self.symbol_table[sub_operand.symbol]
            if int(sub_operand_ssa._name[1]) >= self.n_args: # not one of the input arguments
                self.delete(sub_operand.symbol)
                op_new = self.builder.insert(NotOp.from_value(sub_operand_ssa)).res
                op_new._name = sub_operand_ssa._name.split('_')[0] + "_" + str(int(sub_operand_ssa._name.split('_')[1]) + 1)
                self.declare(sub_operand.symbol, op_new)

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
            init_op_ssa = self.builder.insert(InitOp.from_value(VectorType(element_type,[size,]))).res
        else:
            init_op_ssa = self.builder.insert(InitOp.from_value(IntegerType(1))).res

        return init_op_ssa

    # generation of a xor operation
    def ir_gen_xor(self, expr: BinaryOp) -> SSAValue:
        
        # set left operand
        left_ssa = self.ir_gen_operand(expr, "left")

        # set right operand
        right_ssa = self.ir_gen_operand(expr, "right")
        
        # check if we can do the xor in place:
        # e.g. xor is implemented in the quantum world as two cnot. 
        # In the case of two consecutive xor (a^b^c), instead of allocating 2 new qubits we use just one.
        # we can do it only if the two operands are not both named values 
        # also we need left and right to be either a NamedValue or a Xor operation or a Not operation

        # try to write on right qubit
        if isinstance(expr.right, BinaryOp) or (isinstance(expr.right, UnaryOp) and isinstance(expr.right.operand, BinaryOp)):
            ssa_name = right_ssa._name

            cnotOp2_ssa = self.builder.insert(CNotOp.from_value(left_ssa, self.symbol_table[ssa_name])).res
            cnotOp2_ssa._name = ssa_name.split('_')[0] + "_" + str(int(ssa_name.split('_')[1]) + 1)

            self.declare(cnotOp2_ssa._name, cnotOp2_ssa)
        # if possible write on left qubit
        elif isinstance(expr.left, BinaryOp) or (isinstance(expr.left, UnaryOp) and isinstance(expr.left.operand, BinaryOp)):
            ssa_name = left_ssa._name

            cnotOp2_ssa = self.builder.insert(CNotOp.from_value(right_ssa, self.symbol_table[ssa_name])).res
            cnotOp2_ssa._name = ssa_name.split('_')[0] + "_" + str(int(ssa_name.split('_')[1]) + 1)

            self.declare(cnotOp2_ssa._name, cnotOp2_ssa)
        # allocate a new qubit
        else:
            initOp_ssa = self.ir_gen_new_qubit(expr)
            initOp_ssa._name = "q" + str(self.n_qubit) + "_0"
            self.n_qubit += 1                    
            
            self.declare(initOp_ssa._name, initOp_ssa)
        
            cnotOp1_ssa = self.builder.insert(CNotOp.from_value(left_ssa, self.symbol_table[initOp_ssa._name])).res
            cnotOp1_ssa._name = initOp_ssa._name.split('_')[0] + "_" + str(int(initOp_ssa._name.split('_')[1]) + 1)
            name = cnotOp1_ssa._name

            self.declare(cnotOp1_ssa._name, cnotOp1_ssa)

            cnotOp2_ssa = self.builder.insert(CNotOp.from_value(right_ssa, self.symbol_table[name])).res
            cnotOp2_ssa._name = name.split('_')[0] + "_" + str(int(name.split('_')[1]) + 1)
            self.declare(cnotOp2_ssa._name, cnotOp2_ssa)

        if isinstance(expr.left, UnaryOp):
            self.restore_qubit(expr, "left")

        if isinstance(expr.right, UnaryOp):
            self.restore_qubit(expr, "right")

        return cnotOp2_ssa

    def ir_gen_and(self, expr: BinaryOp) -> SSAValue:

        # initialize a new qubit or a new qubit register
        initOp_ssa = self.ir_gen_new_qubit(expr)
        initOp_ssa._name = "q" + str(self.n_qubit) + "_0"
        self.n_qubit += 1

        self.declare(initOp_ssa._name, initOp_ssa)

        # set left operand
        left_ssa = self.ir_gen_operand(expr, "left")

        # set right operand
        right_ssa = self.ir_gen_operand(expr, "right")
        
        ccnotOP_ssa = self.builder.insert(CCNotOp.from_value(left_ssa, right_ssa, self.symbol_table[initOp_ssa._name])).res
        ccnotOP_ssa._name = initOp_ssa._name.split('_')[0] + "_" + str(int(initOp_ssa._name.split('_')[1]) + 1)
        self.declare(ccnotOP_ssa._name, ccnotOP_ssa)

        if isinstance(expr.left, UnaryOp):
            self.restore_qubit(expr, "left")

        if isinstance(expr.right, UnaryOp):
            self.restore_qubit(expr, "right")
        
        return ccnotOP_ssa
    
    # generation of an operand for the or operation
    # it returns the name by which the ssa value is identified in the symboltable
    def ir_gen_operand_or(self, expr: BinaryOp, side: str) -> str:

        if side == "left":
            operand = expr.left
        elif side == "right":
            operand = expr.right

        if isinstance(operand, NamedValue):
            operand_ssaValue = self.ir_gen_named_value(operand)
            self.delete(operand.symbol)

            notOp1_ssa = self.builder.insert(NotOp.from_value(operand_ssaValue)).res
            notOp1_ssa._name = operand_ssaValue._name.split('_')[0] + "_" + str(int(operand_ssaValue._name.split('_')[1]) + 1)
            
            declaration_name = operand.symbol
        else:
            if isinstance(operand, BinaryOp):
                operand_ssaValue = self.ir_gen_bin(operand)

                notOp1_ssa = self.builder.insert(NotOp.from_value(operand_ssaValue)).res
                notOp1_ssa._name = operand_ssaValue._name.split('_')[0] + "_" + str(int(operand_ssaValue._name.split('_')[1]) + 1)
                
                declaration_name = notOp1_ssa._name
            elif isinstance(operand, UnaryOp):
                unary_operand = operand.operand
                if isinstance(unary_operand, NamedValue):
                    operand_ssaValue = self.symbol_table[unary_operand.symbol]
                if not(isinstance(unary_operand, NamedValue) and int(operand_ssaValue._name[1]) < self.n_args and int(operand_ssaValue._name[-1])%2 != 0):
                    operand_ssaValue = self.ir_gen_unary(operand)
                if isinstance(unary_operand, NamedValue):
                    self.delete(unary_operand.symbol)
                    
                    notOp1_ssa = self.builder.insert(NotOp.from_value(operand_ssaValue)).res
                    notOp1_ssa._name = operand_ssaValue._name.split('_')[0] + "_" + str(int(operand_ssaValue._name.split('_')[1]) + 1)
                    
                    declaration_name = unary_operand.symbol
                else:
                    notOp1_ssa = self.builder.insert(NotOp.from_value(operand_ssaValue)).res
                    notOp1_ssa._name = operand_ssaValue._name.split('_')[0] + "_" + str(int(operand_ssaValue._name.split('_')[1]) + 1)
                    
                    declaration_name = notOp1_ssa._name
        
        self.declare(declaration_name, notOp1_ssa)
        
        return declaration_name
    
    # generation of the or operation
    def ir_gen_or(self, expr: BinaryOp) -> SSAValue:

        # auxiliary SSAValue
        initOp_ssa = self.ir_gen_new_qubit(expr)
            
        initOp_ssa._name= "q" + str(self.n_qubit) + "_0"
        self.n_qubit += 1

        self.declare(initOp_ssa._name, initOp_ssa)
        
        # rigth and left operand of the or operation
        left_declaration_name = self.ir_gen_operand_or(expr, "left")

        right_declaration_name = self.ir_gen_operand_or(expr, "right")

        left_ssa = self.symbol_table[left_declaration_name]
        right_ssa = self.symbol_table[right_declaration_name]

        ccnotOp_ssa = self.builder.insert(CCNotOp.from_value(left_ssa, right_ssa, self.symbol_table[initOp_ssa._name])).res
        ccnotOp_ssa._name = initOp_ssa._name.split('_')[0] + "_" + str(int(initOp_ssa._name.split('_')[1]) + 1)

        self.declare(ccnotOp_ssa._name, ccnotOp_ssa)
        
        notOp3_ssa = self.builder.insert(NotOp.from_value(left_ssa)).res
        notOp3_ssa._name = left_ssa._name.split('_')[0] + "_" + str(int(left_ssa._name.split('_')[1]) + 1)
        self.delete(left_declaration_name)

        if isinstance(expr.left, NamedValue) or (isinstance(expr.left, UnaryOp) and isinstance(expr.left.operand, NamedValue)):
            self.declare(left_declaration_name, notOp3_ssa)
        else:
            self.declare(notOp3_ssa._name, notOp3_ssa)

        notOp4_ssa = self.builder.insert(NotOp.from_value(right_ssa)).res
        notOp4_ssa._name = right_ssa._name.split('_')[0] + "_" + str(int(right_ssa._name.split('_')[1]) + 1)
        self.delete(right_declaration_name)

        if isinstance(expr.right, NamedValue) or (isinstance(expr.right, UnaryOp) and isinstance(expr.right.operand, NamedValue)):
            self.declare(right_declaration_name, notOp4_ssa)
        else:
            self.declare(notOp4_ssa._name, notOp4_ssa)

        notOp5_ssa = self.builder.insert(NotOp.from_value(ccnotOp_ssa)).res
        notOp5_ssa._name = ccnotOp_ssa._name.split('_')[0] + "_" + str(int(ccnotOp_ssa._name.split('_')[1]) + 1)

        self.declare(notOp5_ssa._name, notOp5_ssa)

        if isinstance(expr.left, UnaryOp):
            self.restore_qubit(expr, "left")

        if isinstance(expr.right, UnaryOp):
            self.restore_qubit(expr, "right")

        return notOp5_ssa

    def error(self, message: str, cause: Exception | None = None) -> NoReturn:
        raise IRGenError(message) from cause
