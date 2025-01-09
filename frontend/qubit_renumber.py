from xdsl.ir import Operation
from xdsl.pattern_rewriter import PatternRewriter, RewritePattern
from xdsl.dialects.builtin import ModuleOp

from dialect.dialect import FuncOp, InitOp

# Class to drive the removal of unused operations in the main program.
class QubitRenumber(RewritePattern):

    n_qubits: int = 0

    # Check if the operation needs to be renumbered.
    def rewrite(self, op: Operation) -> None:

        # these types of operations are never modified
        if isinstance(op, ModuleOp):
            return

        # if the operation is a FuncOp we check for the number of parameters
        if isinstance(op, FuncOp):
            self.n_qubits += len(op.body.first_block.args)
            return

        # if the operation is a InitOp we check for the qubit number
        if isinstance(op, InitOp):
            if op.res._name.split('_')[0] != ("q" + str(self.n_qubits)):
                op.res._name = "q" + str(self.n_qubits) + "_0"
            self.n_qubits = self.n_qubits + 1    
            return

        # else check for the target qubit to be the same as the result one
        op.res._name = op.target._name.split('_')[0] + "_" + str(int(op.target._name.split('_')[1]) + 1)

    def match_and_rewrite(self, op: Operation, rewriter: PatternRewriter):
        self.rewrite(op)