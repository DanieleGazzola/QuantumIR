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

    # Stores the active SSAValues
    # variables coming from the verilog have as key their symbol(1234567890 a), temporary SSAValues have as key their name(q4_7)
    symbol_table: ScopedSymbolTable | None = None

    n_qubit: int = 0  # n_qubits that need to be used when generating the first IR
    n_args: int = 0   # n_args taken as input in the verilog
    
    def __init__(self):

        self.module = ModuleOp([])
        self.builder = Builder.at_end(self.module.body.blocks[0])
    
    # Add a new entry in the symbol_table
    def declare(self, var: str, value: SSAValue) -> bool:
        
        assert self.symbol_table is not None
        if var in self.symbol_table:
            return False
        self.symbol_table[var] = value
        return True
    
    # Delete an entry from the symbol_table
    def delete(self, var: str) -> bool:
        assert self.symbol_table is not None
        if var in self.symbol_table:
            self.symbol_table.table.pop(var)
            return True
        return False

    # Acts on the whole tree
    def ir_gen_module(self, ast: Root) -> ModuleOp:

        for f in ast.members:
            if (isinstance(f, Instance)):
                self.ir_gen_function(f.body)

        return self.module

    # Acts on each function call
    def ir_gen_function(self, body: InstanceBody) -> FuncOp:

        parent_builder = self.builder

        self.symbol_table = ScopedSymbolTable()

        # Input arguments
        proto_args = [member for member in body.members if isinstance(member, Port) and member.direction == "In"]
        
        # Parsing input arguments
        arg_types=[]
        for member in proto_args:
            # Check if it is a vector
            if "[" in member.type and "]" in member.type:
                match = re.match(r"(\w+)\[(\d+):(\d+)\]", member.type) # regex to match the vector type and size
                if match:
                    # Extract the high index, and low index
                    high_index = int(match.group(2))
                    low_index = int(match.group(3))
                    size = high_index - low_index + 1

                    element_type = IntegerType(1) #Type of the elements in the vector
                    arg_types.append(builtin.VectorType(element_type, [size,]))
            else:
                # It's a single bit
                arg_types.append(builtin.i1)

        block = Block(arg_types=arg_types)
        self.builder = Builder.at_end(block)
        self.n_args = len(block.args)

        # Declare each input argument as a new qubit
        for name, value in zip(proto_args, block.args):
            value._name = "q" + str(self.n_qubit) + "_0"
            self.n_qubit += 1
            self.declare(name.internalSymbol, value)

        # Create operations for computations inside the function
        for member in body.members:
                self.ir_gen_expr(member)

        # Output arguments
        proto_return = [member for member in body.members if isinstance(member, Port) and member.direction == "Out"]

        # Add a MeasureOp for each output argument of the function
        for var in proto_return:
            try:
                measure = self.builder.insert(MeasureOp.from_value(self.symbol_table[var.internalSymbol])).res
                measure._name = str(self.symbol_table[var.internalSymbol]._name.split('_')[0]) + "_" + str(int(self.symbol_table[var.internalSymbol]._name.split('_')[1]) + 1)
            except:
                raise IRGenError(f"Variable {var.internalSymbol} not found in the symbol table, may be uninitilized output var")
       
        self.symbol_table = None
        self.builder = parent_builder

        func = self.builder.insert(FuncOp(body.name, Region(block)))

        return func

    # Act as a switch for the different types of expressions
    def ir_gen_expr(self, expr: ASTNode) -> SSAValue:
        
        # The two ways one can write combinatorial assignments in SystemVerilog
        if isinstance(expr, ContinuousAssign):
            return self.ir_gen_assign(expr.assignment)
        if isinstance(expr, ProceduralBlock):
            return self.ir_gen_procedural_block(expr)

    # Create operations from expression in the procedural block
    def ir_gen_procedural_block(self, expr: ProceduralBlock) -> SSAValue:
            
            # Extract the block and the statement containing the operations
            block = expr.body
            statement = block.body
            if isinstance(statement, list):
                for s in statement:
                    self.ir_gen_assign(s.expr)
            else:
                self.ir_gen_assign(statement.expr)

    # Acts as a switch for the different types of assignements
    def ir_gen_assign(self, assignment: Assignment) -> SSAValue:

        if isinstance(assignment.right, Conversion): # initialization of a variable
            return self.ir_gen_init()
        if isinstance(assignment.right, BinaryOp):   # binary operation
            return self.ir_gen_bin_op(assignment)
        if isinstance(assignment.right, UnaryOp):    # unary operation
            return self.ir_gen_unary_op(assignment)
    
    # Initialization of a new qubit
    def ir_gen_init(self) -> SSAValue:

        # Insert the InitOp
        initOp_ssa = self.builder.insert(InitOp.from_value(IntegerType(1))).res

        # Set the name of the qubit
        initOp_ssa._name = "q" + str(self.n_qubit) + "_0"
        self.n_qubit += 1

        # Add the new SSAValue(qubit) in the symbol_table
        self.declare(initOp_ssa._name, initOp_ssa)

        return initOp_ssa
    
    # Generation of a unary operation from verilog
    def ir_gen_unary_op(self, expr: Assignment) -> SSAValue:
        
        # Symbol from verilog
        symbol = expr.left.symbol

        final_op_ssa = self.ir_gen_unary(expr.right)

        # add the SSAValue to the symbol_table
        self.declare(symbol, final_op_ssa)
        
        return final_op_ssa

    # Generation of a unary operation
    def ir_gen_unary(self, expr: UnaryOp) -> SSAValue:
        
        if expr.op == "BitwiseNot":     # Not operation
            unary_ssa = self.ir_gen_not(expr)
            return unary_ssa
        else:
            raise IRGenError(f"Unknown unary operation {expr.op}")
        
    # Generation of a Not operation
    def ir_gen_not(self, expr: UnaryOp) -> SSAValue:

        if isinstance(expr.operand, NamedValue):                # not of a variable of the verilog (internal variable or input argument)
            operand = self.symbol_table[expr.operand.symbol]
            self.delete(expr.operand.symbol)

        elif isinstance(expr.operand, BinaryOp):                # Not of a binary operation
            operand = self.ir_gen_bin(expr.operand)
            self.delete(operand._name)
        
        # Insert the NotOp
        notOp_ssa = self.builder.insert(NotOp.from_value(operand)).res

        # Set the name of the SSAValue adding 1 to the temporal state of the qubit
        notOp_ssa._name = operand._name.split('_')[0] + "_" + str(int(operand._name.split('_')[1]) + 1)

        # Add the SSAValue to the symbol_table
        if isinstance(expr.operand, NamedValue):
            self.declare(expr.operand.symbol, notOp_ssa) # key is the symbol they have in verilog
        elif isinstance(expr.operand, BinaryOp):
            self.declare(operand._name, notOp_ssa)       # key is the name of the SSAValue
        
        return notOp_ssa

    # Generation of a binary operation from verilog
    def ir_gen_bin_op(self, expr: Assignment) -> SSAValue:
        
        # Symbol coming from verilog
        symbol = expr.left.symbol

        # Generate the binary operation
        final_op_ssa = self.ir_gen_bin(expr.right)

        # Add the SSAValue to the symbol_table
        self.declare(symbol, final_op_ssa)

        return final_op_ssa

    # Switch for the different types of binary operations
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

    # Construction of an operation operand which is a NamedValue.
    # NamedValue corresponding to input arguments can't be assigned in SystemVerilog.
    # This means that if the status number of the corresponding SSAValue is odd 
    # that SSAValue corresponds to a negated value.
    def ir_gen_named_value(self, expr: NamedValue) -> SSAValue:
        namedValue_ssa = self.symbol_table[expr.symbol]

        # If the qubit has been negated, and it needs the original qubit
        # we negate it again
        if int(namedValue_ssa._name[-1])%2 != 0 and int(namedValue_ssa._name[1]) < self.n_args: # odd status number and an input argument
            self.delete(expr.symbol)
            not_ssa = self.builder.insert(NotOp.from_value(namedValue_ssa)).res
            not_ssa._name = namedValue_ssa._name.split('_')[0] + "_" + str(int(namedValue_ssa._name.split('_')[1]) + 1)
            self.declare(expr.symbol, not_ssa)
            namedValue_ssa = not_ssa
        
        return namedValue_ssa
    
    # Generation of operands for a binary operation. Right and left.
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
            unary_operand = operand.operand
            # Unary operation on a NamedValue
            if isinstance(unary_operand, NamedValue):
                result_ssa = self.symbol_table[unary_operand.symbol]
            # If it is not a NamedValue or it's not an input argument or it's not with an odd status number.
            if not(isinstance(unary_operand, NamedValue) and int(result_ssa._name.split("_")[1]) < self.n_args and int(result_ssa._name.split("_")[1])%2 != 0):
                result_ssa = self.ir_gen_unary(operand)
        
        self.declare(result_ssa._name, result_ssa)
        
        return result_ssa
    
    # Every time we negate a qubit, after the operation we restore its original state
    # by negating it again. Only if the qubit is not an input argument.
    # If it's an input argument we do it in the gen_named_value function
    def restore_qubit(self, expr: BinaryOp, side: str) -> None:

        if side == "left":
            binaryOp_operand = expr.left
        elif side == "right":
            binaryOp_operand = expr.right
        
        sub_operand = binaryOp_operand.operand
        if isinstance(sub_operand, NamedValue):
            sub_operand_ssa = self.symbol_table[sub_operand.symbol]
            if int(sub_operand_ssa._name[1]) >= self.n_args: # Not one of the input arguments
                self.delete(sub_operand.symbol)
                op_new = self.builder.insert(NotOp.from_value(sub_operand_ssa)).res
                op_new._name = sub_operand_ssa._name.split('_')[0] + "_" + str(int(sub_operand_ssa._name.split('_')[1]) + 1)
                self.declare(sub_operand.symbol, op_new)

    # Creates a new qubit and instantiates a InitOp.
    # Then, changes the name of the qubit, declares it in the ScopedSymbolTable.
    # Returns the ssa of the InitOp result for future reference in the caller.
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
            initOp_ssa = self.builder.insert(InitOp.from_value(VectorType(element_type,[size,]))).res
        else:
            initOp_ssa = self.builder.insert(InitOp.from_value(IntegerType(1))).res

        initOp_ssa._name= "q" + str(self.n_qubit) + "_0"
        self.n_qubit += 1

        self.declare(initOp_ssa._name, initOp_ssa)

        return initOp_ssa

    # Generation of a XOR operation.
    # a XOR b (a ^ b) is implemented in the quantum world as two CNot controlled one by a and one by b, both
    # writing on a newly instantiated qubit, initialized to zero.
    def ir_gen_xor(self, expr: BinaryOp) -> SSAValue:
        
        # Set left operand
        left_ssa = self.ir_gen_operand(expr, "left")

        # Set right operand
        right_ssa = self.ir_gen_operand(expr, "right")
        
        # Check if we can do the xor in place:
        # in the case of two consecutive xor (a^b^c), instead of allocating 2 new qubits we use just one.
        # We can do it only if the two operands are not both named values. 
        # Also we need left and right to be either a NamedValue or a Xor operation or a Not operation.

        # try to write on right qubit.
        if isinstance(expr.right, BinaryOp) or (isinstance(expr.right, UnaryOp) and isinstance(expr.right.operand, BinaryOp)):
            ssa_name = right_ssa._name

            # CNotOp writing on the right operand.
            cnotOp2_ssa = self.builder.insert(CNotOp.from_value(left_ssa, self.symbol_table[ssa_name])).res
            cnotOp2_ssa._name = ssa_name.split('_')[0] + "_" + str(int(ssa_name.split('_')[1]) + 1)

            self.declare(cnotOp2_ssa._name, cnotOp2_ssa)

        # if possible write on left qubit
        elif isinstance(expr.left, BinaryOp) or (isinstance(expr.left, UnaryOp) and isinstance(expr.left.operand, BinaryOp)):
            ssa_name = left_ssa._name

            # CNotOp writing on the left operand.
            cnotOp2_ssa = self.builder.insert(CNotOp.from_value(right_ssa, self.symbol_table[ssa_name])).res
            cnotOp2_ssa._name = ssa_name.split('_')[0] + "_" + str(int(ssa_name.split('_')[1]) + 1)

            self.declare(cnotOp2_ssa._name, cnotOp2_ssa)

        # Allocate a new qubit.
        else:
            
            initOp_ssa = self.ir_gen_new_qubit(expr)
        
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

    # Generation of an AND operation.
    # a AND b (a & b) is implemented in the quantum world as one CCNot controlled by both a and b, writing
    # on a newly instantiated third qubit initialized to zero.
    def ir_gen_and(self, expr: BinaryOp) -> SSAValue:

        # Initialize a new qubit or a new qubit register
        initOp_ssa = self.ir_gen_new_qubit(expr)


        # Set left operand
        left_ssa = self.ir_gen_operand(expr, "left")

        # Set right operand
        right_ssa = self.ir_gen_operand(expr, "right")
        
        # Create the CCNot operation
        ccnotOp_ssa = self.builder.insert(CCNotOp.from_value(left_ssa, right_ssa, self.symbol_table[initOp_ssa._name])).res
        ccnotOp_ssa._name = initOp_ssa._name.split('_')[0] + "_" + str(int(initOp_ssa._name.split('_')[1]) + 1)
        self.declare(ccnotOp_ssa._name, ccnotOp_ssa)

        if isinstance(expr.left, UnaryOp):
            self.restore_qubit(expr, "left")

        if isinstance(expr.right, UnaryOp):
            self.restore_qubit(expr, "right")
        
        return ccnotOp_ssa
    
    # Generation of an operand for the OR operation.
    # It returns the name by which the SSAValue is identified in the SymbolTable
    # for future reference in the OR creation process.
    def ir_gen_operand_or(self, expr: BinaryOp, side: str) -> str:

        if side == "left":
            operand = expr.left
        elif side == "right":
            operand = expr.right

        # If the operand is a NamedValue
        if isinstance(operand, NamedValue):
            # Extract the corresponding SSAValue
            operand_ssaValue = self.ir_gen_named_value(operand)
            self.delete(operand.symbol) # delete it's previous name
            
            # Insert the first NOT for the OR conversion
            notOp1_ssa = self.builder.insert(NotOp.from_value(operand_ssaValue)).res
            notOp1_ssa._name = operand_ssaValue._name.split('_')[0] + "_" + str(int(operand_ssaValue._name.split('_')[1]) + 1)
            
            # Return the name to use for declaring it in the symbol table
            declaration_name = operand.symbol
        else:
            if isinstance(operand, BinaryOp):
                # Create the binary operation
                operand_ssaValue = self.ir_gen_bin(operand)

                # Insert the first NOT for the OR conversion
                notOp1_ssa = self.builder.insert(NotOp.from_value(operand_ssaValue)).res
                notOp1_ssa._name = operand_ssaValue._name.split('_')[0] + "_" + str(int(operand_ssaValue._name.split('_')[1]) + 1)
                
                # Return the name to use for declaring it in the symbol table
                declaration_name = notOp1_ssa._name

            elif isinstance(operand, UnaryOp):
                unary_operand = operand.operand
                # Unary operation on a simple Named Value
                if isinstance(unary_operand, NamedValue):
                    operand_ssaValue = self.symbol_table[unary_operand.symbol]
                # If it is not a NamedValue or it's not an input argument or it's not with an odd status number.
                if not(isinstance(unary_operand, NamedValue) and int(operand_ssaValue._name[1]) < self.n_args and int(operand_ssaValue._name[-1])%2 != 0):
                    operand_ssaValue = self.ir_gen_unary(operand)
                if isinstance(unary_operand, NamedValue):
                    self.delete(unary_operand.symbol)
                    
                    # Insert the first NOT for the OR conversion
                    notOp1_ssa = self.builder.insert(NotOp.from_value(operand_ssaValue)).res
                    notOp1_ssa._name = operand_ssaValue._name.split('_')[0] + "_" + str(int(operand_ssaValue._name.split('_')[1]) + 1)
                    
                    # Return the name to use for declaring it in the symbol table
                    declaration_name = unary_operand.symbol
                else:
                    notOp1_ssa = self.builder.insert(NotOp.from_value(operand_ssaValue)).res
                    notOp1_ssa._name = operand_ssaValue._name.split('_')[0] + "_" + str(int(operand_ssaValue._name.split('_')[1]) + 1)
                    
                    # Return the name to use for declaring it in the symbol table
                    declaration_name = notOp1_ssa._name
        
        self.declare(declaration_name, notOp1_ssa)
        
        return declaration_name
    
    # Generation of the or operation.
    # a OR b (a | b) is implemented in the quantum world by:
    # - negating both a and b 
    # - applying a CCNot controlled by the negated value of the two operands writing on a newly instantiated 
    #   third qubit initialized to zero
    # - negating again a and b and also the CCNot target qubit.
    def ir_gen_or(self, expr: BinaryOp) -> SSAValue:

        # Auxiliary SSAValue
        initOp_ssa = self.ir_gen_new_qubit(expr)

        # Rigth and left operand of the or operation
        left_declaration_name = self.ir_gen_operand_or(expr, "left")

        right_declaration_name = self.ir_gen_operand_or(expr, "right")

        # Extract the SSAValues
        left_ssa = self.symbol_table[left_declaration_name]
        right_ssa = self.symbol_table[right_declaration_name]

        # Create the CCNotOp
        ccnotOp_ssa = self.builder.insert(CCNotOp.from_value(left_ssa, right_ssa, self.symbol_table[initOp_ssa._name])).res
        ccnotOp_ssa._name = initOp_ssa._name.split('_')[0] + "_" + str(int(initOp_ssa._name.split('_')[1]) + 1)

        self.declare(ccnotOp_ssa._name, ccnotOp_ssa)
        
        # Create the final NOT on the left operand
        notOp3_ssa = self.builder.insert(NotOp.from_value(left_ssa)).res
        notOp3_ssa._name = left_ssa._name.split('_')[0] + "_" + str(int(left_ssa._name.split('_')[1]) + 1)
        self.delete(left_declaration_name)

        # If it's a Named Value or a UnaryOp acting on a NamedValue declare it with 
        if isinstance(expr.left, NamedValue) or (isinstance(expr.left, UnaryOp) and isinstance(expr.left.operand, NamedValue)):
            self.declare(left_declaration_name, notOp3_ssa)
        else:
            self.declare(notOp3_ssa._name, notOp3_ssa)

        # Create the final NOT on the right operand
        notOp4_ssa = self.builder.insert(NotOp.from_value(right_ssa)).res
        notOp4_ssa._name = right_ssa._name.split('_')[0] + "_" + str(int(right_ssa._name.split('_')[1]) + 1)
        self.delete(right_declaration_name)

        if isinstance(expr.right, NamedValue) or (isinstance(expr.right, UnaryOp) and isinstance(expr.right.operand, NamedValue)):
            self.declare(right_declaration_name, notOp4_ssa)
        else:
            self.declare(notOp4_ssa._name, notOp4_ssa)

        # Create the final NOT on the target qubit of the CCNot
        notOp5_ssa = self.builder.insert(NotOp.from_value(ccnotOp_ssa)).res
        notOp5_ssa._name = ccnotOp_ssa._name.split('_')[0] + "_" + str(int(ccnotOp_ssa._name.split('_')[1]) + 1)

        self.declare(notOp5_ssa._name, notOp5_ssa)

        if isinstance(expr.left, UnaryOp):
            self.restore_qubit(expr, "left")

        if isinstance(expr.right, UnaryOp):
            self.restore_qubit(expr, "right")

        return notOp5_ssa

    # Error message generation
    def error(self, message: str, cause: Exception | None = None) -> NoReturn:
        raise IRGenError(message) from cause
