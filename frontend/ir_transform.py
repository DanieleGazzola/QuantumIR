from xdsl.ir import Operation, SSAValue, Block, Region, Use
from xdsl.pattern_rewriter import PatternRewriter, RewritePattern
from dataclasses import dataclass, field
from typing import TypeVar
from xdsl.context import MLContext
from xdsl.dialects.builtin import ModuleOp, UnregisteredOp
from xdsl.passes import ModulePass
from xdsl.rewriter import Rewriter
from dialect.dialect import GetMemoryEffect, FuncOp, MeasureOp
from xdsl.traits import (
    IsTerminator,
    MemoryEffectKind,
    EffectInstance,
    SymbolOpInterface,
    get_effects,
    IsolatedFromAbove,
    is_side_effect_free,
    only_has_effect,
)

def is_trivially_dead(op: Operation) -> bool:

    if isinstance(op, ModuleOp):
        return False
    if isinstance(op, FuncOp):
        return False
    if isinstance(op, MeasureOp):
        return False

    return (
        (not op.res.uses)
        and (not op.get_trait(IsTerminator))
        and (not op.get_trait(SymbolOpInterface))
        and result_only_effects(op)
    )

def result_only_effects(rootOp: Operation) -> bool:

    effects = get_effects(rootOp)
    
    return effects is not None and all(
        e.kind == MemoryEffectKind.READ
        or (
            e.kind == MemoryEffectKind.ALLOC
            and isinstance(v := e.value, SSAValue)
            and rootOp.is_ancestor(v.owner)
        )
        or (
            e.kind == MemoryEffectKind.WRITE
            and isinstance(v := e.value, SSAValue)
            and rootOp.is_ancestor(v.owner)
        )
        for e in effects
    )

def get_effects(op: Operation) -> set[EffectInstance] | None:

    effect_interfaces = GetMemoryEffect.get_effects(op)
    if not effect_interfaces:
        return None

    effects = set[EffectInstance]()
    for it in op.get_traits_of_type(EffectInstance):
        it_effects = GetMemoryEffect.get_effects(op)
        if it_effects is None:
            return None
        effects.update(it_effects)

    return effects

class RemoveUnusedOperations(RewritePattern):

    def match_and_rewrite(self, op: Operation, rewriter: PatternRewriter):
        if is_trivially_dead(op) and op.parent is not None:
            rewriter.erase_op(op)
        
@dataclass
class OperationInfo:
    """
    Boilerplate helper to use in KnownOps cache.

    This is to compare operations on their name, attributes, properties, results,
    operands, and matching region structure.
    """

    op: Operation

    @property
    def name(self):
        return (
            self.op.op_name.data
            if isinstance(self.op, UnregisteredOp)
            else self.op.name
        )

    def __hash__(self):
        return hash(
            (
                self.name,
                sum(hash(i) for i in self.op.attributes.items()),
                sum(hash(i) for i in self.op.properties.items()),
                hash(self.op.result_types),
                hash(self.op.operands),
            )
        )

    def __eq__(self, other: object):
        return (
            isinstance(other, OperationInfo)
            and hash(self) == hash(other)
            and self.name == other.name
            and self.op.attributes == other.op.attributes
            and self.op.properties == other.op.properties
            and self.op.operands == other.op.operands
            and self.op.result_types == other.op.result_types
            and all(
                s.is_structurally_equivalent(o)
                for s, o in zip(self.op.regions, other.op.regions, strict=True)
            )
        )


_D = TypeVar("_D")

class KnownOps:
    """
    Cache dictionary for known operations used in CSE.
    It quacks like a dict[Operation, Operation], but uses OperationInfo of an Opetration
    as the actual key.
    """

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

    def get(self, k: Operation, default: _D = None) -> Operation | _D:
        return self._known_ops.get(OperationInfo(k), default)

    def pop(self, k: Operation):
        return self._known_ops.pop(OperationInfo(k))


def has_other_side_effecting_op_in_between(
    from_op: Operation, to_op: Operation
) -> bool:
    """
    Returns if there *may* be a 'write' effecting operation between `from_op` and
    `to_op`.
    """
    assert from_op.parent is to_op.parent
    next_op = from_op
    while next_op is not to_op:
        effects = get_effects(next_op)
        if effects is None or any(e.kind is MemoryEffectKind.WRITE for e in effects):
            return True
        next_op = next_op.next_op
        assert next_op is not None, "Incorrect order of ops in side-effect search"
    return False


class CSEDriver:
    """
    Boilerplate class to handle and carry the state for CSE.
    """

    _rewriter: Rewriter
    _to_erase: set[Operation] = field(default_factory=set)
    _known_ops: KnownOps = KnownOps()

    def __init__(self):
        self._rewriter = Rewriter()
        self._to_erase = set()
        self._known_ops = KnownOps()

    def _mark_erasure(self, op: Operation):
        self._to_erase.add(op)

    def _commit_erasures(self):
        for o in self._to_erase:
            if o.parent is not None:
                self._rewriter.erase_op(o)

    def _replace_and_delete(self, op: Operation, existing: Operation):
        """
        Factoring, replace `op` by `existing` and mark `op` for erasure.
        """

        # Just replace results
        def wasVisited(use: Use):
            return use.operation not in self._known_ops

        for o, n in zip(op.results, existing.results, strict=True):
            if all(wasVisited(u) for u in o.uses):
                o.replace_by(n)

        # If no uses remain, we can mark this operation for erasure
        if all(not r.uses for r in op.results):
            self._mark_erasure(op)

    def _simplify_operation(self, op: Operation):
        """
        Simplify a single operation: replace it by a corresponding known operation in
        scope, if any.
        Also just delete dead operations.
        """
        # # Don't simplify terminators.
        # if op.has_trait(IsTerminator):
        #     return

        # If the operation is already trivially dead just add it to the erase list.
        # if is_trivially_dead(op):
        #     self._mark_erasure(op)
        #     return

        # Don't simplify operations with regions that have multiple blocks.
        # MLIR doesn't either at time of writing :)
        if any(len(region.blocks) > 1 for region in op.regions):
            return

        # Have a close look if the op might have side effects.
        if not is_side_effect_free(op):
            # If we can't be sure or the op has side effects, bail out
            # if not only_has_effect(op, MemoryEffectKind.READ):
            #     return
            # If the op is only reading, we can still try to CSE it
            # exisiting is the old operation
            print(OperationInfo(self._known_ops.get(op)))
            if existing := self._known_ops.get(op):
                if (
                    op.parent_block() is existing.parent_block()
                    # We then ensure there are no 'write' side-effecting operations
                    # in between the two, that could change the result of the operation
                    and not has_other_side_effecting_op_in_between(existing, op)
                ):
                    self._replace_and_delete(op, existing)
                    return

            # The operation is a CSE candidate, but we did not find a replacement
            # Mark it for any later occurence
            self._known_ops[op] = op
            return

        # If we know the operation is side-effect free, we can just replace it
        if existing := self._known_ops.get(op):
            self._replace_and_delete(op, existing)
            return

        # The operation is a CSE candidate, but we did not find a replacement
        # Mark it for any later occurence
        self._known_ops[op] = op

    def _simplify_block(self, block: Block):
        for op in block.ops:
            if op.regions:
                might_be_isolated = isinstance(op, UnregisteredOp) or (
                    op.get_trait(IsolatedFromAbove) is not None
                )
                # If we can't be sure the op isn't isolated, we assume it is for safety
                if might_be_isolated:
                    # Then save the current scope for later, but continue inside with a
                    # blank slate
                    old_scope = self._known_ops
                    self._known_ops = KnownOps()
                    for region in op.regions:
                        self._simplify_region(region)
                    self._known_ops = old_scope
                else:
                    for region in op.regions:
                        self._simplify_region(region)
        
            self._simplify_operation(op)

    def _simplify_region(self, region: Region):
        if not region.blocks:
            return

        if len(region.blocks) == 1:
            old_scope = self._known_ops
            self._known_ops = KnownOps(self._known_ops)

            self._simplify_block(region.block)

            self._known_ops = old_scope

    def simplify(self, thing: Operation | Block | Region):
        match thing:
            case Operation():
                for region in thing.regions:
                    self._simplify_region(region)
            case Block():
                self._simplify_block(thing)
            case Region():
                self._simplify_region(thing)
        self._commit_erasures()


def cse(thing: Operation | Block | Region):
    CSEDriver().simplify(thing)


class CommonSubexpressionElimination(ModulePass):
    name = "cse"

    def apply(self, op: ModuleOp) -> None:
        cse(op)