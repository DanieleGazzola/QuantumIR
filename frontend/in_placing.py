from xdsl.ir import Operation
from xdsl.pattern_rewriter import PatternRewriter, RewritePattern
from xdsl.builder import Builder
from xdsl.rewriter import Rewriter
from dialect.dialect import CNotOp

# Class to drive the removal of unused operations in the main program.
class InPlacing(RewritePattern):
    
    builder: Builder
    rewriter : Rewriter

    # Find the unused control bit to write the xor results on.
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
                      break
                next_op = next_op.next_op
            
            if(used == False):
                return cnot
            else: used = False # Set false for the next iter.
    
    # Match the cnot chain and rewrite it.
    def match_and_rewrite(self, op: Operation, rewriter: PatternRewriter):
        self.rewriter = rewriter
        
        previous_op = op._prev_op
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
                    next_op = next_op._next_op
                    continue
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
                    qubit_to_pass = newcnot.res

            cnot_list[-1].res.replace_by(qubit_to_pass)

            for cnot in reversed(cnot_list):
                self.rewriter.erase_op(cnot)  

