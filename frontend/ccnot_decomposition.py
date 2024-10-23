from xdsl.ir import Operation
from xdsl.pattern_rewriter import PatternRewriter, RewritePattern
from xdsl.builder import Builder
from xdsl.rewriter import Rewriter

from dialect.dialect import HadamardOp, TGateOp,TCrossGateOp, CNotOp, MeasureOp,InitOp

# pattern rewriting pass to transform CCNOT operations in a sequence of CNOT, Hadamard and T-gate operations
# in order to use existing metrics for the evaluation of the circuit performances.
class CCnot_decomposition(RewritePattern):

    builder: Builder

    def fix_names(self, op: Operation):
        # op is the first hadamard gate
        current = op
        
        # go until the end of the transformation and adjust the names of the qubits
        while(current is not None and not isinstance(current,InitOp)):
            res_name = current.res._name
            target_name = current.target._name
            res_name = target_name.split('_')[0] +"_" + str(int(target_name.split('_')[1])+1)
            current.res._name = res_name

            current = current._next_op
    
    # Match every ccnot and transform it to the sequence specified in the documentation.
    # Match also the measure op to correct their target qubit after the transformation.
    def match_and_rewrite(self, op: Operation, rewriter: PatternRewriter):

        if op.name == "quantum.ccnot":
            self.builder = Builder.before(op)
            control1 = op.control1
            control2 = op.control2
            target = op.target
            res = op.res

            h1 = self.builder.insert(HadamardOp.from_value(target))
            h1_res = h1.res
            cnot1_res = self.builder.insert(CNotOp.from_value(control2, h1_res)).res

            tcross1_res = self.builder.insert(TCrossGateOp.from_value(cnot1_res)).res
            cnot2_res = self.builder.insert(CNotOp.from_value(control1, tcross1_res)).res

            t1_res = self.builder.insert(TGateOp.from_value(cnot2_res)).res
            cnot3_res = self.builder.insert(CNotOp.from_value(control2, t1_res)).res

            tcross2_res = self.builder.insert(TCrossGateOp.from_value(cnot3_res)).res

            cnot4_res = self.builder.insert(CNotOp.from_value(control1, tcross2_res)).res
            cnot5_res = self.builder.insert(CNotOp.from_value(control1, control2)).res

            tcross3_res = self.builder.insert(TCrossGateOp.from_value(cnot5_res)).res
            cnot6_res = self.builder.insert(CNotOp.from_value(control1, tcross3_res)).res

            # new control1
            t2_res = self.builder.insert(TGateOp.from_value(control1)).res
            # new control2
            t3_res = self.builder.insert(TGateOp.from_value(cnot6_res)).res

            # new target
            t4_res = self.builder.insert(TGateOp.from_value(cnot4_res)).res
            h2_res = self.builder.insert(HadamardOp.from_value(t4_res)).res
        
            
            # replace the target
            res.replace_by(h2_res)
            # replace the control qubits
            # go from the next operation (in the original mlir)
            # done "by hand" to avoid back sostitution
            current = op.next_op
            while(current is not None):
                i = 0
                # if the current operation uses the previous control 
                for operand in current.operands:
                    if operand._name == control1._name:
                        current.operands[i] = t2_res
                    elif operand._name == control2._name:
                        current.operands[i] = t3_res
                    i +=1
                current = current._next_op
            
            # fix the names of the qubits
            self.fix_names(h1)
            # erase the original ccnot
            rewriter.erase_op(op)
            return
        
        # if it encounters a measure operation, it corrects the target qubit name
        if op.name == "quantum.measure":
            previous = op._prev_op
            target = op.target
            res = op.res

            target_number = target._name.split("_")[0]
            target_state = int(target._name.split("_")[1])

            # go back to the last use of the qubit you want to measure
            print(op)
            while previous is not None:
                prev_res_number = previous.res._name.split("_")[0]
                prev_res_state = int(previous.res._name.split("_")[1])
                # if it's the one you want to measure and it's in a more advanced state that the one you have
                print(previous.res._name, target._name) 
                if prev_res_number == target_number and prev_res_state > target_state:

                    self.builder = Builder.before(op)
                    new_measure_res = self.builder.insert(MeasureOp.from_value(previous.res)).res
                    new_measure_res._name = previous.res._name.split("_")[0] + "_" + str(int(previous.res._name.split("_")[1])+1)
                    rewriter.erase_op(op) # delete the original measure operation
                    break
                
                previous = previous._prev_op   
    

            

