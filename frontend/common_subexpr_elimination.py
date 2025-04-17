from xdsl.ir import Operation, Block, Region, BlockArgument, OpResult
from xdsl.dialects.builtin import ModuleOp, UnregisteredOp, IntegerType
from xdsl.passes import ModulePass
from xdsl.builder import Builder
from xdsl.rewriter import Rewriter
from xdsl.traits import IsolatedFromAbove
from dataclasses import dataclass
from dialect.dialect import FuncOp, MeasureOp, InitOp, CCNotOp, CNotOp

import re
                            ##### SUPPORT FUNCTIONS #####

# check if the existing SSAValue(qubit) will be changed between the existing operation and the one we are substituting
def has_other_modifications(existingOp: Operation,passedOperation:set) -> bool:

    from_uses = existingOp.res.uses

    for use in from_uses:
        # operation using the SSAValue
        user_operation = use.operation
        if isinstance(user_operation, MeasureOp):
            continue
        if(user_operation.operands[-1] == existingOp.res): # if the SSAValue is used as a target
            if(user_operation in passedOperation): # and the use happens before the current operation
                return True
        else:
            continue

    return False
    
# if the current operation res SSAValue is written after the current operation and the existing operation res SSAValue
# is read after that write, we can't substitute the current operation with the existing one 
def has_read_after_write(currentOp: Operation, existingOp: Operation) -> bool:

    next_op = currentOp.next_op

    op_uses = currentOp.res.uses

    found = False
    for use in op_uses:
        user_operation = use.operation
        if isinstance(user_operation, MeasureOp):
            continue
        elif(user_operation.operands[-1] == currentOp.res): # result of current op is used as target
            operation_using = user_operation
            found=True
            break
        else:
            continue
    
    if not found:
        return False
    else:
        next_op = operation_using.next_op
         # check on every operation until the end
        while next_op != None:

            # if the operation is an InitOp surely it will not read the qubit 
            if not isinstance(next_op, InitOp):

                # if we find any use of the first qubit we cannot remap
                if any(attr == existingOp.res for attr in next_op.operands):
                    return True
                
            next_op = next_op.next_op

        return False
# if both results of the existing and of the current operation are measured we cannot substitute 
def both_measured(currentOp: Operation, existingOp: Operation) -> bool:
    current_res = currentOp.res
    existing_res = existingOp.res

    current_uses = current_res.uses
    existing_uses = existing_res.uses

    current_measured = False
    existing_measured = False

    for use in current_uses:
        if isinstance(use.operation, MeasureOp):
            current_measured = True
            break
    
    for use in existing_uses:
        if isinstance(use.operation, MeasureOp):
            existing_measured = True
            break
    
    if current_measured and existing_measured:
        return True
    else:
        return False


                            ##### CLASSES TO HELP CSE MANAGMENT #####
   
# OperationInfo is a class that contains the operation and some useful information about it.
# It is used to compute the hash of the operations for the knownOps dictionary and to implement transformation-specific logic when two
# operation are equal.
# The hash is used by the dictionary KnownOps to check if two OperationInfo are equal.      
@dataclass
class OperationInfo:
    # operation for which we store the info
    op: Operation
    # tuple containing the operands of the operation and their history in terms of operations generating
    # the SSAValues
    operandsHistory: tuple
    # hash of the operation
    _hash: int

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
    def sub_operand(self, operand: OpResult, qh : dict,qHashes:dict) -> tuple:
        all_operand = tuple() 
        all_hashes = tuple()
        all_operand += (operand.owner.name,) # take the name of the operation that use the operand
        all_hashes += (hash(operand.owner.name),) # hash the name of the operation that use the operand

        # order according to qubit number in order to catch the same operation with different operand order
        # sort only the operands, not the result
        operandlist = sorted(operand.owner.operands[:-1],key=lambda x: int(re.search(r'q(\d+)_',x._name).group(1))) + [operand.owner.operands[-1]]
                             
        # for every operand in the operation
        for sub_operand in operandlist:
            operandHistory = qh.get(sub_operand._name) 
            operandHashes = qHashes.get(sub_operand._name)
            # here the operand is in the dictionary since it is the result of an operation already passed in CSEDriver.
            if(operandHistory is not None and operandHashes is not None): 
                all_operand += operandHistory
                all_hashes += (operandHashes,)
            else:
                raise TypeError("Error, the operand is not in the dictionary",sub_operand._name, sub_operand, operandHistory,operandHashes)
                        
        return all_operand,all_hashes
    
    # Get the operands of the operation for which the OperationInfo is built
    def __init__(self,op: Operation,qh: dict, qHashes:dict):
        self.op=op

        all_operands = tuple()
        all_hashes = tuple()
        # order according to qubit number in order to catch the same operation with different operand order
        # sort only the operands, not the result
        operandlist = sorted(self.operands[:-1],key=lambda x: int(re.search(r'q(\d+)_',x._name).group(1))) + [self.operands[-1]]

        for operand in operandlist:
            operandHistory = qh.get(operand._name)
            operandHash = qHashes.get(operand._name)
            if(operandHistory is not None and operandHash is not None): # check if the operand history is already memorized
                all_operands += operandHistory
                all_hashes += (operandHash,)
            elif isinstance(operand, BlockArgument):# else if it is an input argument
                qh[operand._name] = (operand.index,) # add to dict
                currentHash = hash(operand.index)   
                qHashes[operand._name] = currentHash # add to dict

                all_operands += (operand.index,)
                all_hashes += (currentHash,)
            elif isinstance(operand, OpResult):
                if isinstance(operand.owner, InitOp):# if it is newly initialized
                    qh[operand._name] = (operand.owner.name,) # add to dict
                    currentHash = hash(operand.owner.name)
                    qHashes[operand._name] = currentHash # add to dict

                    all_operands += (operand.owner.name,)
                    all_hashes += (currentHash,)
                else:
                    sub_operands,sub_hashes = self.sub_operand(operand,qh,qHashes)
                    all_operands += sub_operands
                    all_hashes += sub_hashes
            else:
                raise TypeError("Operand not present in dictionary nor an input argumnent or a result of an operation")
        
        # add the result of the operation to the dict. Following operations using this result will find its
        # history already memorized
        qh[op.res._name] = (op.name,all_operands,)
        qHashes[op.res._name] = hash((op.name,all_hashes,))

        self.operandsHistory = all_operands

        self._hash= hash((self.name,self.result_types,all_hashes))

    def __hash__(self):
        return self._hash

    def __eq__(self, other: object):
        return self.name == other.name and self.operandsHistory == other.operandsHistory and self.result_types == other.result_types
    
# A dictionary used to store the passed operations during the MLIR traversing.
# OperationInfo is the key, Operation is the value.
class KnownOps:

    _known_ops: dict[OperationInfo, Operation]

    def __init__(self, known_ops: "KnownOps | None" = None):
        if known_ops is None:
            self._known_ops = {}
        else:
            self._known_ops = dict(known_ops._known_ops)

    def __getitem__(self, k: OperationInfo):
        return self._known_ops[k]

    def __setitem__(self, k: OperationInfo, v: Operation):
        self._known_ops[k] = v

    def __contains__(self, k: OperationInfo):
        return k in self._known_ops

    def get(self, k: OperationInfo) -> Operation | None:
        if op := self._known_ops.get(k):
            return op
        return None

    def pop(self, k: OperationInfo):
        return self._known_ops.pop(k)



                            ##### CLASS TO MANAGE CSE TRANSFORMATIONS #####

class CSEDriver:
    # Rewriter used to modify MLIR
    _rewriter: Rewriter
    # Dict of the already passed operations
    _known_ops: KnownOps = KnownOps()

    # Dict with the history of the qubits in the program.
    # Key: qubit._name ; Value: tuple with the history
    qubitHistories : dict[str,tuple]

    # Dict memorizing the hash of the history of the qubits. Used in order to reduce hash computation time.
    #  History means what operation and input argument generate these qubits. Key: qubit._name ; Value: hash of the tuple of the history
    qubitHashes : dict[str,int]
    
    # Builder for inserting new operations
    builder: Builder
    # counter for keeping track of the current highest qubit number
    max_qubit: int = 0

    passedOperations : set

    same_qubit: int

    def __init__(self):
        self._rewriter = Rewriter()
        self._known_ops = KnownOps()
        self.qubitHistories = {}
        self.qubitHashes = {}
        self.passedOperations = set()
        self.same_qubit = 0

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

        self.passedOperations.add(op)

        # check if CCNotOp has two equal control qubits.
        # In that case we can replace it with a CNotOp
        if isinstance(op, CCNotOp) and (op.control1 == op.control2):
            self.same_qubit += 1
            self.builder = Builder.before(op)
            cnotOp = self.builder.insert(CNotOp.from_value(op.control1, op.target))
            self._replace_and_delete(op, cnotOp)
            cnotOp.res._name = op.res._name
        
        # check if CNotOp has equal control and target qubits.
        # In that case we can replace it with an InitOp
        if isinstance(op, CNotOp) and (op.control == op.target):
            self.same_qubit += 1
            self.builder= Builder.before(op)
            initOp = self.builder.insert(InitOp.from_value(IntegerType(1)))
            initOp.res._name = "q" + str(self.max_qubit + 1) + "_0"
            self.max_qubit += 1
            self._replace_and_delete(op, initOp)

        opInfo = OperationInfo(op,self.qubitHistories,self.qubitHashes)

        # check if the operation is already known
        if existing := self._known_ops.get(opInfo):

            # if the existing op(qubit) will not be changed in the future we can replace the current operation
            if not has_other_modifications(existing,self.passedOperations) and not has_read_after_write(op, existing) \
                and not both_measured(op, existing):

                self._replace_and_delete(op, existing)
                return
        
        # if the operation is not known we add it to the known operations
        self._known_ops[opInfo] = op
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
    same_qubit: int = 0 

    cseDriver: CSEDriver

    def apply(self, op: ModuleOp) -> None:
        self.cseDriver.simplify(op)
        self.same_qubit += self.cseDriver.same_qubit

    def __init__(self):
        self.cseDriver = CSEDriver()