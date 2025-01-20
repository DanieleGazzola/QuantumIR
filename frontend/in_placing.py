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

    # Find the unused control bit to write the xor results on.
    def unused_operand(self,cnot_list : list):
        used = False
        for cnot in cnot_list: # for every cnot matched
            control = cnot.control
            for use in control.uses: # check the uses of the control qubit

                current_userop = use.operation # operation using the control qubit
                res_qbnumber = int(current_userop.res._name.split('_')[0][1:])
                res_statusnumber = int(current_userop.res._name.split('_')[1])
                control_qbnumber = int(control._name.split('_')[0][1:])
                control_statusnumber =int(control._name.split('_')[1])  
                # if the result of the operation using the control qubit is greater than the number of qubit instantiated
                # until now or is equal to the control qubit number (it's using that qubit as a target), consider the control
                # qubit used, since these operations are performed after the considered cnot list.
                if res_qbnumber > self.maxqubit or (res_qbnumber==control_qbnumber and control_statusnumber < res_statusnumber):
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
            self.maxqubit=int(op.res._name.split('_')[0][1:])
            return

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

