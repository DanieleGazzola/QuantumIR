from xdsl.ir import Operation
from xdsl.pattern_rewriter import PatternRewriter, RewritePattern
from xdsl.dialects.builtin import ModuleOp

from dialect.dialect import FuncOp, MeasureOp

                            ##### SUPPORT FUNCTIONS #####

# Check if the operation is not used in the following part of the program.
def is_trivially_dead(op: Operation) -> bool:

    # these types of operations are never dead
    if isinstance(op, ModuleOp) or isinstance(op, FuncOp) or isinstance(op, MeasureOp):
        return False
    
    # if the result of the operation is never used then it is dead
    return not op.res.uses

# Class to drive the removal of unused operations in the main program.
class RemoveUnusedOperations(RewritePattern):

    def match_and_rewrite(self, op: Operation, rewriter: PatternRewriter):
        if is_trivially_dead(op) and op.parent is not None:
            rewriter.erase_op(op)