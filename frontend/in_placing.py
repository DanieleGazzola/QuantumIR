from xdsl.ir import Operation
from xdsl.pattern_rewriter import PatternRewriter, RewritePattern
from xdsl.builder import Builder
from xdsl.rewriter import Rewriter
from dialect.dialect import CNotOp,FuncOp,InitOp
from xdsl.dialects.builtin import ModuleOp


# Class to drive the removal of unused operations in the main program.
class InPlacing(RewritePattern):
    
    builder: Builder
    rewriter : Rewriter
    maxqubit : int
    passedOperation: set

    def __init__(self):
        self.passedOperation = set()

    # Find the unused control bit to write the xor results on.
    def unused_operand(self,cnot_list : list):
        used = False

        for cnot in cnot_list: # for every cnot matched
            control = cnot.control
            
            for use in control.uses: # check the uses of the control qubit
                current_userop = use.operation # operation using the control qubit
                # if the use is the cnot itself, skip it and keep used=False.
                if(current_userop == cnot):
                    continue
                
                # if the control has uses after the considered cnot chain, its value cannot be changed.
                if current_userop not in self.passedOperation:
                    used = True
                    break

            if not used:
                return cnot
            else:
                used = False # for next iter
    
    # Match the cnot chain and rewrite it.
    def match_and_rewrite(self, op: Operation, rewriter: PatternRewriter):

        if isinstance(op,ModuleOp) or isinstance(op,FuncOp):
            return
        
        if isinstance(op,InitOp):
            return


        self.rewriter = rewriter
        
        previous_op = op._prev_op
        # Add the operation to the set of passed operations, regardless of it matching the inplacing pattern.
        self.passedOperation.add(op)

        # Start of the program.
        if previous_op is None:
            return
        
        # If the previous op is a quantum.init and the current is a quantum.cnot
        # we have a candidate for the optimization.
        if previous_op.name == "quantum.init" and op.name == "quantum.cnot":
            # The cnot must target the qubit initialized by the init.
            if previous_op.res._name != op.target._name:
                return

            cnot_list = [] # List for the cnot chain.
            cnot_list.append(op)
            next_op = op._next_op
            while ((next_op.name == "quantum.cnot" or next_op.name == "quantum.not") and op.res._name.split('_')[0] == next_op.res._name.split('_')[0]):
                if next_op.name =="quantum.not":
                    self.passedOperation.add(next_op)
                    next_op = next_op._next_op
                    continue
                self.passedOperation.add(op)
                cnot_list.append(next_op)
                next_op = next_op._next_op
            
            # Not a valid chain.
            if len(cnot_list) == 1:
                return
            # The first unused qubit is the one we are gonna write on.

            cnot_unused_control = self.unused_operand(cnot_list)
    
            # All current control qubits are used, can't optimize.
            if cnot_unused_control is None:
                return   
            
            unused_qubit = cnot_unused_control.control

            # In the other cnots, substitute the result of cnot with the unused qubit with the unused qubit.
            qubit_to_pass = unused_qubit
            builder = Builder.before(cnot_list[0])
            for cnot in cnot_list:
                if cnot is not cnot_unused_control:
                    newcnot = builder.insert(CNotOp.from_value(cnot.control, qubit_to_pass))
                    newcnot.res._name = qubit_to_pass._name.split('_')[0] + "_" + str(int(qubit_to_pass._name.split('_')[1]) + 1)
                    self.passedOperation.add(newcnot) # add the new op to the set of passed operations
                    qubit_to_pass = newcnot.res

            # last element of cnot_list is the last operation of the chain. Take its uses to substitute the new
            # SSAValue of the last cnot.
            uses = cnot_list[-1].res.uses.copy()
            future_set = set() # set of the future uses of the last cnot result
            for use in uses:

                if use.operation in self.passedOperation: # already passed operation
                    continue
                else: # future operation
                    future_set.add(use.operation)

            # empty set, no future operations no need to change SSAValues, just erase the old cnot chain.
            if not future_set:
                for cnot in reversed(cnot_list):
                    self.rewriter.erase_op(cnot)  
                return
            
            # set not empty, need to replace the old result from the cnot chain with the new result of the inplaced
            # cnots
            for future_op in future_set:
                operands = future_op.operands
                target_idx = len(operands)-1
                if(operands[target_idx] == cnot_list[-1].res): # if the old result is target
                    operands[target_idx] = qubit_to_pass
                    future_op.res._name = qubit_to_pass._name.split('_')[0] + "_" + str(int(qubit_to_pass._name.split("_")[1])+1)
                else: # it's a control
                    operands[operands.index(cnot_list[-1].res)] = qubit_to_pass
                
            
            for cnot in reversed(cnot_list):
                self.rewriter.erase_op(cnot)  
        else:
            return
