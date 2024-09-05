from xdsl.context import MLContext
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Operation, SSAValue
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import PatternRewriter, PatternRewriteWalker, RewritePattern
from xdsl.traits import (
    IsTerminator,
    MemoryEffectKind,
    MemoryEffect,
    EffectInstance,
    SymbolOpInterface,
    get_effects,
)

from dialect.dialect import GetMemoryEffect, FuncOp, MeasureOp

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