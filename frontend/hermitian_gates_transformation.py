from xdsl.ir import Operation, Block, Region
from xdsl.dialects.builtin import ModuleOp, UnregisteredOp
from xdsl.passes import ModulePass
from xdsl.rewriter import Rewriter
from xdsl.traits import IsolatedFromAbove

from dataclasses import dataclass

from dialect.dialect import FuncOp, MeasureOp, InitOp

                            ##### SUPPORT FUNCTION #####

# check if the qubit has uses in between the two operation we want to eliminate
# if not we can safely delete the two operations as they commute
def has_uses_between(from_op: Operation, to_op: Operation) -> bool:
    
    next_op = from_op.next_op

    # check on every operation until the target operation
    while not next_op is to_op:

        # if the operation is an InitOp surely it will not use the existing qubit 
        if not isinstance(next_op, InitOp):

            # if we find the SSAValue is used in any way we don't delete
            for operand in next_op.operands:
                if operand._name == from_op.res._name:
                    return True  
                
        next_op = next_op.next_op

    return False


                            ##### CLASSES TO HELP CSE MANAGMENT #####

# OperationInfo is a class that contains the operations
# The hash is used by the dictionary KnownOps to check if two OperationInfo are equal       
@dataclass
class OperationInfo:

    op: Operation

    hash: int = 0

    @property
    def name(self):
        return self.op.name
    
    @property
    def result_types(self):
        return self.op.result_types
    
    @property
    def operands(self):
        return self.op.operands._op._operands
    
    # compute the hash of the operation
    def __hash__(self):
        self.hash = hash((self.name, tuple(operand._name for operand in self.operands[:-1]), self.operands[-1]._name.split('_')[0]))
        return self.hash
    
    # check if two operation are enough equal to be analized
    def __eq__(self, other: object):
        return self.hash == other.hash

# A dictionary used to store the passed operations
# OperationInfo is the key, Operation is the value
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

# This class drives the logic of the transformation
class HGEDriver:

    _rewriter: Rewriter
    _known_ops: KnownOps = KnownOps()
    
    def __init__(self):
        self._rewriter = Rewriter()
        self._known_ops = KnownOps()

    # delete an operation
    def _commit_erasure(self, op: Operation):
        if op.parent is not None:
            self._rewriter.erase_op(op)

    # replace the SSAValue of the current operation with the existing one and delete the current operation
    def _replace_and_delete(self, op: Operation, existing: Operation):

        # replace all future uses of the current operation results with the existing one
        for o, n in zip([op.results,], [existing.target,], strict=True):
            o[0].replace_by(n)

        # if there are no uses delete the operations
        # also remove op from the _know_ops to avoid getting matched again
        if all(not r.uses for r in op.results):
            self._known_ops.pop(op)
            self._commit_erasure(op)
            self._commit_erasure(existing)

    # simplify the operation
    def _simplify_operation(self, op: Operation):

        # never simplify these types of operations
        if isinstance(op, InitOp) or isinstance(op, ModuleOp) or isinstance(op, FuncOp):
            return
        
        # renaming of the state of the qubits if any trasformation has changed the temporal sequence
        if int(op.res._name.split('_')[1]) != int(op.target._name.split('_')[1]) + 1:
            op.res._name = op.res._name.split('_')[0] + '_' + str(int(op.target._name.split('_')[1]) + 1)

        # MeasureOp can need a rename but is never simplified
        if isinstance(op, MeasureOp):
            return

        # check if the operation is already known
        if existing := self._known_ops.get(op):

            # if the qubit is not used in between we can delete the operations
            if not has_uses_between(existing, op):
                self._replace_and_delete(op, existing)
                return
        
        # if the operation is not known we add it to the known operations
        self._known_ops[op] = op
        return

    # simplify the block, it sweeps all the operations in the block
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

                            ##### MAIN CLASS TO INVOKE THE TRANSFORMATION #####

# This class is used to apply the transformation to the MLIR in the main program
class HermitianGatesElimination(ModulePass):

    def apply(self, op: ModuleOp) -> None:
        HGEDriver().simplify(op)