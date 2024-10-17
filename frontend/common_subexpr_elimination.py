from xdsl.ir import Operation, Block, Region, BlockArgument, OpResult
from xdsl.dialects.builtin import ModuleOp, UnregisteredOp, IntegerType
from xdsl.passes import ModulePass
from xdsl.builder import Builder
from xdsl.rewriter import Rewriter
from xdsl.traits import IsolatedFromAbove
from dataclasses import dataclass
from dialect.dialect import FuncOp, MeasureOp, InitOp, CCNotOp, CNotOp

                            ##### SUPPORT FUNCTIONS #####

# check if the existing SSAValue(qubit) will be changed in the future
def has_other_modifications(from_op: Operation) -> bool:

    next_op = from_op.next_op

    # check on every operation until the end
    while next_op != None:

        # if the operation is an InitOp surely it will not change the SSAValue 
        if not isinstance(next_op, InitOp):

            # if we find a modification of the qubit we don't substitute
            if next_op.target == from_op.res:
                return True
            
        next_op = next_op.next_op

    return False

# check if the existing SSAValue(qubit) will be read after the one we are substituting is modified
# if not we can remap the operation we have on the second qubit to the first one,
# deleting the second qubit
def has_read_after_write(op: Operation, from_op: Operation) -> bool:

    next_op = op.next_op

    # check on every operation until the end
    while next_op != None:

        # if the operation is an InitOp surely it will not change the qubit
        if not isinstance(next_op, InitOp):

            # if we find a modification of the second qubit we stop and now we check for reads on the first one
            if next_op.target == op.res:
                break

        next_op = next_op.next_op
    
    # if we didn't find any write we can safely remap qubits
    if next_op == None:
        return False
    
    next_op = next_op.next_op

    # check on every operation until the end
    while next_op != None:

        # if the operation is an InitOp surely it will not read the qubit 
        if not isinstance(next_op, InitOp):

            # if we find any use of the first qubit we cannot remap
            if any(attr == from_op.res for attr in next_op.operands):
                return True
            
        next_op = next_op.next_op

    return False


                            ##### CLASSES TO HELP CSE MANAGMENT #####
   
# OperationInfo is a class that contains the operation and some useful information about it.
# It is used to compute the hash of the operations for the knownOps dictionary and to implement transformation-specific logic when two
# operation are equal.
# The hash is used by the dictionary KnownOps to check if two OperationInfo are equal.      
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

    # recursive function to get all the operands of an operation
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
    
    # hash the operands of the operation
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

        return all_operands

    def __hash__(self):
        return hash(
            (
                self.name,
                self.result_types,
                self.hash_operands()
            )
        )

    def __eq__(self, other: object):
        return hash(self) == hash(other)
    
# A dictionary used to store the passed operations during the MLIR traversing.
# OperationInfo is the key, Operation is the value.
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
    builder: Builder
    max_qubit: int = 0

    def __init__(self):
        self._rewriter = Rewriter()
        self._known_ops = KnownOps()

    def _commit_erasure(self, op: Operation):
        if op.parent is not None:
            self._rewriter.erase_op(op)

    # replace the SSAValue of the current operation with the existing one
    # and delete the current operation
    def _replace_and_delete(self, op: Operation, existing: Operation):

        # replace all future uses of the current operation results with the existing one
        for o, n in zip(op.results, existing.results, strict=True):
            o.replace_by(n)

        next_op = op.next_op
        
        # change the name accordingly
        while next_op != None:
            if next_op.res._name.split('_')[0] == op.res._name.split('_')[0]:
                next_op.res._name = existing.res._name.split('_')[0] + "_" + next_op.res._name.split('_')[1]
            for attr in next_op.operands:
                if attr._name.split('_')[0] == op.results[0]._name.split('_')[0]:
                    attr._name = existing.results[0]._name.split('_')[0] + "_" + next_op.results[0]._name.split('_')[1]
            next_op = next_op.next_op

        # if there are no uses delete the operation
        if all(not r.uses for r in op.results):
            self._commit_erasure(op)

    # simplify the operation
    def _simplify_operation(self, op: Operation):

        # never simplify these types of operations
        if isinstance(op, InitOp) or isinstance(op, ModuleOp) or isinstance(op, FuncOp) or isinstance(op, MeasureOp):
            return

        # check if CCNotOp has two equal control qubits.
        # In that case we can replace it with a CNotOp
        if isinstance(op, CCNotOp) and (op.control1 == op.control2):
            self.builder = Builder.before(op)
            cnotOp = self.builder.insert(CNotOp.from_value(op.control1, op.target))
            self._replace_and_delete(op, cnotOp)
            cnotOp.res._name = op.res._name
        
        # check if CNotOp has equal control and target qubits.
        # In that case we can replace it with an InitOp
        if isinstance(op, CNotOp) and (op.control == op.target):
            self.builder= Builder.before(op)
            initOp = self.builder.insert(InitOp.from_value(IntegerType(1)))
            initOp.res._name = "q" + str(self.max_qubit + 1) + "_0"
            self.max_qubit += 1
            self._replace_and_delete(op, initOp)
    
        # check if the operation is already known
        if existing := self._known_ops.get(op):
            # if the existing op(qubit) will not be changed in the future we can replace the current operation
            if not has_other_modifications(existing) and not has_read_after_write(op, existing):
                self._replace_and_delete(op, existing)
                return
        
        # if the operation is not known we add it to the known operations
        self._known_ops[op] = op
        return

    # simplify the block
    def _simplify_block(self, block: Block):
        
        for op in block.ops:
            if isinstance(op, InitOp):
                self.max_qubit = max(self.max_qubit, int(op.res._name.split('_')[0][1:]))

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

class CommonSubexpressionElimination(ModulePass):

    def apply(self, op: ModuleOp) -> None:
        CSEDriver().simplify(op)