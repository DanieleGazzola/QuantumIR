from xml.etree.ElementTree import tostring
from xdsl.ir import Operation, Block, Region, Use, BlockArgument, OpResult
from xdsl.dialects.builtin import ModuleOp, UnregisteredOp
from xdsl.passes import ModulePass
from xdsl.rewriter import Rewriter
from xdsl.traits import EffectInstance, IsolatedFromAbove

from dataclasses import dataclass

from dialect.dialect import GetMemoryEffect, FuncOp, MeasureOp, InitOp

                            ##### SUPPORT FUNCTION #####


# check if the existing SSAValue will be changed in the future
# if not we can safely use it to replace the current operation
def has_uses_between(from_op: Operation, to_op: Operation) -> bool:

    effects = set[EffectInstance]()
    next_op = from_op.next_op

    # check on every operation until the end of the function
    while not next_op is to_op:
        effects = GetMemoryEffect.get_effects(next_op)
        
        # il the op is an InitOp surely will not change the SSAValue 
        if not isinstance(next_op, InitOp):
            for effect in effects:
                if effect.value == from_op.res:
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
    
    # hash the operands of the operation
    def hash_operands(self):
        operands = tuple()
        if(self.op.name =="quantum.cnot"):
            operands += (self.op.control,)
        elif(self.op.name =="quantum.ccnot"):
            operands += (self.op.control1,self.op.control2,)
        elif(self.op.name=="quantum.not"):
            operands += (self.op.target,)
        return hash(operands)
    
    # this function is used to check if two hashes match
    def __hash__(self):
        return hash(
            (
                self.name,
                self.hash_operands(),
            )
        )
    

    # other is the second operation matched, self is the first
    # qui non ho messo nessun tipo di logica, ho notato che quando facciamo una get confronta automaticamente le chiavi usando
    # hash. Di conseguenza lì già matcha solo le operazioni con lo stesso nome e gli stessi operandi di controllo ( e il loro numero).
    # In questo eq ho semplicemente messo il confronto tra le due operazioni su target e result.
    def __eq__(self, other: object):

        value = (self.name == other.name and  # same name
                self.result_types == other.result_types and # same result types
                other.op.target == self.op.res) # other target is my result
        
        return value

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



                            ##### CLASS TO MANAGE HGE TRANSFORMATIONS #####

class HGEDriver:

    _rewriter: Rewriter
    _known_ops: KnownOps = KnownOps()
    n = 0
    def __init__(self):
        self._rewriter = Rewriter()
        self._known_ops = KnownOps()

    def _commit_erasure(self, op: Operation):
        if op.parent is not None:
            self._rewriter.erase_op(op)

    # replace the SSAValue of the current operation with the existing one
    # and delete the current operation
    def _replace_and_delete(self, op: Operation, existing: Operation):

        def wasVisited(use: Use):
            return use.operation not in self._known_ops

        # replace all future uses of the current operation results with the existing one
        # !!! orrible solution with the tuple
        for o, n in zip([op.results,], [existing.target,], strict=True):
            if all(wasVisited(u) for u in o[0].uses):
                o[0].replace_by(n)

        # if there are no uses delete the operationS
        if all(not r.uses for r in op.results):
            self._commit_erasure(op)
            self._commit_erasure(existing)

    # simplify the operation
    def _simplify_operation(self, op: Operation):

        # never simplify these types of operations
        if isinstance(op, InitOp) or isinstance(op, ModuleOp) or isinstance(op, FuncOp) or isinstance(op, MeasureOp):
            return
        # print("Check if the operation is already known:", op.name, op._operands)
        # check if the operation is already known
        if existing := self._known_ops.get(op):
            # print(op," matching with ",existing)
            # if the existing op will not be changed in the future we can replace the current operation
            if not has_uses_between(existing, op):
                self._replace_and_delete(op, existing)
                return
        
        # if the operation is not known we add it to the known operations
        self._known_ops[op] = op
        return

    # simplify the block
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

    # simplify the region
    def _simplify_region(self, region: Region):

        if not region.blocks:
            return

        if len(region.blocks) == 1:
            old_scope = self._known_ops
            self._known_ops = KnownOps(self._known_ops)

            self._simplify_block(region.block)

            self._known_ops = old_scope

    # switch between the different simplification functions
    def simplify(self, thing: Operation | Block | Region):

        match thing:
            case Operation():
                for region in thing.regions:
                    self._simplify_region(region)
            case Block():
                self._simplify_block(thing)
            case Region():
                self._simplify_region(thing)



                            ##### MAIN CLASSES TO INVOKE THE TRANSFORMATION #####

class HermitianGatesElimination(ModulePass):

    def apply(self, op: ModuleOp) -> None:
        HGEDriver().simplify(op)