from xdsl.ir import Operation
from xdsl.pattern_rewriter import PatternRewriter, RewritePattern
from xdsl.builder import Builder
from xdsl.rewriter import Rewriter
from xdsl.ir import SSAValue
from dialect.dialect import CNotOp

# Class to drive the removal of unused operations in the main program.
class InPlacing(RewritePattern):
    
    builder: Builder
    rewriter : Rewriter

    # find the unused control bit to write the xor results on
    def unused_operand(self,cnot_list : list):
        used = False
        for cnot in cnot_list:
            control = cnot.control
            next_op = cnot.next_op
            # go on until the end of the mlir
            while(next_op is not None):
                # if the control qubit is used
                if control in next_op.operands:
                      used=True
                next_op = next_op.next_op
            
            if(used == False):
                return cnot
            else: used = False # set false for the next iter
    
    # match the cnot chain and rewrite it
    def match_and_rewrite(self, op: Operation, rewriter: PatternRewriter):
        self.rewriter = rewriter
        
        previous_op = op._prev_op
        # start of the program
        if previous_op is None:
            return

        # if the previous op is a quantum.init and the current is a quantum.cnot
        # we have a candidate for the optimization
        if previous_op.name == "quantum.init" and op.name == "quantum.cnot":
            cnot_list = [] # list for the cnot chain
            cnot_list.append(op)
            next_op = op._next_op
            while ((next_op.name == "quantum.cnot" or next_op.name == "quantum.not") and op.res._name.split('_')[0] == next_op.res._name.split('_')[0]):
                if next_op.name =="quantum.not":
                    next_op = next_op._next_op
                    continue
                cnot_list.append(next_op)
                next_op = next_op._next_op
            
            # the first unused qubit is the one we are gonna write on
            cnot_unused_control = self.unused_operand(cnot_list)

            # all current control qubits are used, can't optimize
            if cnot_unused_control is None:
                return   
            
            unused_qubit = cnot_unused_control.control

            # in the other cnots, substitute the result of cnot with the unused qubit with the unused qubit
            qubit_to_pass = unused_qubit
            for cnot in cnot_list:
                # if the cnot is not the one with the control to write on and is not already changed
                if cnot.control != unused_qubit and cnot.target._name != qubit_to_pass._name:
                    cnot.target.replace_by(qubit_to_pass)
                    cnot.res._name = cnot.target._name.split('_')[0] + "_" + str(int(cnot.target._name.split('_')[1]) + 1)
                    qubit_to_pass = cnot.res
                    
            # fix the names
            for cnot in cnot_list:
                cnot.res._name = cnot.target._name.split('_')[0] + "_" + str(int(cnot.target._name.split('_')[1]) + 1)

            # erase the init and the cnot with the unused control
            self.rewriter.erase_op(cnot_unused_control)
            self.rewriter.erase_op(previous_op)
