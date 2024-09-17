from xdsl.ir import Operation, Block, Region, Use, BlockArgument, OpResult
from xdsl.pattern_rewriter import PatternRewriter, RewritePattern
from xdsl.dialects.builtin import ModuleOp, UnregisteredOp
from xdsl.passes import ModulePass
from xdsl.rewriter import Rewriter
from xdsl.traits import EffectInstance, IsolatedFromAbove

from dataclasses import dataclass

from dialect.dialect import GetMemoryEffect, FuncOp, MeasureOp, InitOp

                            ##### SUPPORT FUNCTIONS #####

# check if the operation is dead
def is_trivially_dead(op: Operation) -> bool:

    # these types of operations are never dead
    if isinstance(op, ModuleOp) or isinstance(op, FuncOp) or isinstance(op, MeasureOp):
        return False
    
    # if the result of the operation is never used then it is dead
    return not op.res.uses


class RemoveUnusedOperations(RewritePattern):

    def match_and_rewrite(self, op: Operation, rewriter: PatternRewriter):
        if is_trivially_dead(op) and op.parent is not None:
            rewriter.erase_op(op)