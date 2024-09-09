from xdsl.ir import Operation, Block, Region, Use, BlockArgument, OpResult
from xdsl.pattern_rewriter import PatternRewriter, RewritePattern
from xdsl.dialects.builtin import ModuleOp, UnregisteredOp
from xdsl.passes import ModulePass
from xdsl.rewriter import Rewriter
from xdsl.traits import EffectInstance, IsolatedFromAbove

from dataclasses import dataclass

from typing import TypeVar

from dialect.dialect import GetMemoryEffect, FuncOp, MeasureOp, InitOp

                            ##### SUPPORT FUNCTIONS #####

# check if the operation is dead
def is_trivially_dead(op: Operation) -> bool:

    # these types of operations are never dead
    if isinstance(op, ModuleOp) or isinstance(op, FuncOp) or isinstance(op, MeasureOp):
        return False
    
    # if the result of the operation is never used then it is dead
    return not op.res.uses



#
def has_other_modifications(from_op: Operation) -> bool:
    effects = set[EffectInstance]()
    next_op = from_op.next_op
    while not isinstance(next_op, MeasureOp):
        effects = GetMemoryEffect.get_effects(next_op)
        if len(effects) >= 2:
            second_last_effect = list(effects)[-2]
            if second_last_effect.value == from_op.res:
                return True
        next_op = next_op.next_op
    return False


                            ##### CLASSES TO HELP CSE MANAGMENT #####
        
@dataclass
class OperationInfo:

    op: Operation

    @property
    def name(self):
        return self.op.name
    
    @property
    def result_types(self):
        return self.op.result_types
    
    @property
    def operands(self):
        return self.op.operands._op._operands

    #
    def sub_operand(self, operand: OpResult):
        all_operand = tuple()
        all_operand += (operand.owner.name,)

        for sub_operand in operand.owner.operands:
            if isinstance(sub_operand, BlockArgument):
                all_operand += (sub_operand.index,)
            elif isinstance(sub_operand, OpResult):
                if isinstance(sub_operand.owner, InitOp):
                    all_operand += (sub_operand.owner.name,)
                else:
                    all_operand += self.sub_operand(sub_operand)
            else:
                return None
        
        return all_operand
    
    #
    def hash_operands(self):
        all_operands = tuple()

        for operand in self.operands:
            if isinstance(operand, BlockArgument):
                all_operands += (operand.index,)
            elif isinstance(operand, OpResult):
                if isinstance(operand.owner, InitOp):
                    all_operands += (operand.owner.name,)
                else:
                    all_operands += self.sub_operand(operand)
            else:
                return None

        return hash(all_operands)

    def __hash__(self):
        return hash(
            (
                self.name,
                hash(self.result_types),
                self.hash_operands()
            )
        )

    def __eq__(self, other: object):
        return hash(self) == hash(other)


_D = TypeVar("_D")

class KnownOps:

    _known_ops: dict[OperationInfo, Operation]

    def __init__(self, known_ops: "KnownOps | None" = None):
        if known_ops is None:
            self._known_ops = {}
        else:
            self._known_ops = dict(known_ops._known_ops)

    def __getitem__(self, k: Operation):
        return self._known_ops[OperationInfo(k)]

    def __setitem__(self, k: Operation, v: Operation):
        self._known_ops[OperationInfo(k)] = v

    def __contains__(self, k: Operation):
        return OperationInfo(k) in self._known_ops

    def get(self, k: Operation) -> Operation | None:
        if op := self._known_ops.get(OperationInfo(k)):
            return op
        return None

    def pop(self, k: Operation):
        return self._known_ops.pop(OperationInfo(k))



                            ##### CLASS TO MANAGE CSE TRANSFORMATIONS #####

class CSEDriver:

    _rewriter: Rewriter
    _known_ops: KnownOps = KnownOps()

    def __init__(self):
        self._rewriter = Rewriter()
        self._known_ops = KnownOps()

    def _commit_erasure(self, op: Operation):
        if op.parent is not None:
            self._rewriter.erase_op(op)

    #
    def _replace_and_delete(self, op: Operation, existing: Operation):

        def wasVisited(use: Use):
            return use.operation not in self._known_ops

        for o, n in zip(op.results, existing.results, strict=True):
            if all(wasVisited(u) for u in o.uses):
                o.replace_by(n)

        if all(not r.uses for r in op.results):
            self._commit_erasure(op)

    #
    def _simplify_operation(self, op: Operation):

        if isinstance(op, InitOp) or isinstance(op, ModuleOp) or isinstance(op, FuncOp) or isinstance(op, MeasureOp):
            return

        if existing := self._known_ops.get(op):
            if (op.parent_block() is existing.parent_block() and not has_other_modifications(existing)):
                self._replace_and_delete(op, existing)
                return
        self._known_ops[op] = op
        return

    #
    def _simplify_block(self, block: Block):
        for op in block.ops:
            if op.regions:
                might_be_isolated = isinstance(op, UnregisteredOp) or (op.get_trait(IsolatedFromAbove) is not None)
                if might_be_isolated:
                    old_scope = self._known_ops
                    self._known_ops = KnownOps()
                    for region in op.regions:
                        self._simplify_region(region)
                    self._known_ops = old_scope
                else:
                    for region in op.regions:
                        self._simplify_region(region)
        
            self._simplify_operation(op)

    #
    def _simplify_region(self, region: Region):
        if not region.blocks:
            return

        if len(region.blocks) == 1:
            old_scope = self._known_ops
            self._known_ops = KnownOps(self._known_ops)

            self._simplify_block(region.block)

            self._known_ops = old_scope

    #
    def simplify(self, thing: Operation | Block | Region):
        match thing:
            case Operation():
                for region in thing.regions:
                    self._simplify_region(region)
            case Block():
                self._simplify_block(thing)
            case Region():
                self._simplify_region(thing)



                            ##### MAIN CLASSES TO INVOKE THE TRANSFORMATIONS #####

class RemoveUnusedOperations(RewritePattern):

    def match_and_rewrite(self, op: Operation, rewriter: PatternRewriter):
        if is_trivially_dead(op) and op.parent is not None:
            rewriter.erase_op(op)

class CommonSubexpressionElimination(ModulePass):

    def apply(self, op: ModuleOp) -> None:
        CSEDriver().simplify(op)