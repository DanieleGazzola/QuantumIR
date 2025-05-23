import os

import backend.JSON_to_DataClasses as JSON_to_DataClasses
from xdsl.printer import Printer
from frontend.in_placing import InPlacing
from frontend.ir_gen import IRGen

from frontend.common_subexpr_elimination import CommonSubexpressionElimination
from frontend.remove_unused_op import RemoveUnusedOperations
from frontend.hermitian_gates_transformation import HermitianGatesElimination
from frontend.qubit_renumber import QubitRenumber
from frontend.ccnot_decomposition import CCnot_decomposition
from xdsl.pattern_rewriter import PatternRewriteWalker
from xdsl.dialects.builtin import ModuleOp

import cProfile
import pstats

from memory_profiler import profile
import resource
import psutil
                    ############# MAIN PROGRAM #############
                    
class QuantumIR():
    
    # Where to find the json
    json_path : str = 'build/output.json'
    # Where to output the dataclass AST
    dataclass_output: str = 'test-outputs/dataclass_ast.txt'
    # General output directory
    output_dir : str = 'test-outputs'
    # Dataclass AST root
    root : JSON_to_DataClasses.Root
    # MLIR root
    module : ModuleOp

    # Number of times each transformation is executed and number of gates it erases
    num_cse : int = 0
    cse_gate_elim: int = 0
    num_dce : int = 0
    dce_gate_elim: int = 0
    dce_init_elim: int = 0
    num_inplacing : int = 0
    inplacing_gate_elim: int = 0
    inplacing_init_elim: int = 0
    num_hge : int = 0
    hge_gate_elim: int = 0
    cse_samequbit : int = 0
    
    def __init__(self):
        pass

    def run_dataclass(self):
        # Read JSON file and fix last characters

        with open(self.json_path, 'r') as file:
            data = file.read()

        pos = data.rfind("}")
        
        # If you find last closed curly bracket remove everything after it
        if pos != -1:
            data = data[:pos + 1]
        # Rewrite the file
        with open(self.json_path, 'w') as file:
            file.write(data)

        json_data = JSON_to_DataClasses.read_json_file(self.json_path)

        # Convert JSON to DataClasses and write it to a file
        self.root = JSON_to_DataClasses.json_to_dataclass(json_data)
        
        os.makedirs(self.output_dir, exist_ok=True)
        with open(self.dataclass_output, 'w') as file:
            formatted_ast = JSON_to_DataClasses.format_root(self.root)
            file.write("\n".join(formatted_ast))

    def run_generate_ir(self, print_output = True):
        ir_gen = IRGen()

        module = ir_gen.ir_gen_module(self.root)
        self.module = module

        if print_output:
            print("\nIR:\n")
            Printer().print_op(self.module)

    def run_transformations(self, print_output = True, gateslist=[], qubitlist=[]):
        if print_output:
            print("\n\nTransformations:")

        module = self.module

        initOp_num = len(module.body.block._args)
        gate_num = 0
        for op in module.body.block._first_op.body.block.ops:
            if op.name == "quantum.init":
                initOp_num +=1
            elif op.name != "quantum.measure":
                gate_num += 1
        gateslist.append(gate_num)
        qubitlist.append(initOp_num)
        while True:

            start_len = len(module.body.block._first_op.body.block.ops)
            
            removeUnusedOp = RemoveUnusedOperations()
            PatternRewriteWalker(removeUnusedOp).rewrite_module(module)
            self.dce_gate_elim += removeUnusedOp.eliminations
            self.dce_init_elim += removeUnusedOp.init_eliminations
            # free up memory
            del removeUnusedOp

            # check if any unused operations were removed
            if start_len != len(module.body.block._first_op.body.block.ops): 
                self.num_dce += 1
                if print_output:
                    print("\n\nRemoved unused operations")
                    Printer().print_op(module)
            
            clone_len = len(module.body.block._first_op.body.block.ops)
            cse = CommonSubexpressionElimination()
            cse.apply(module)
            self.cse_samequbit += cse.same_qubit
            self.cse_gate_elim += cse.cse_eliminations
            # free up memory
            del cse

            # check if any common subexpressions were eliminated
            if clone_len != len(module.body.block._first_op.body.block.ops):
                self.num_cse += 1
                if print_output: 
                    print("\n\nCommon subexpression elimination")
                    Printer().print_op(module)
        
            clone_len = len(module.body.block._first_op.body.block.ops)

            hge = HermitianGatesElimination()
            hge.apply(module)
            self.hge_gate_elim += hge.hge_eliminations
            # free up memory
            del hge

            # check if any common subexpressions were eliminated
            if clone_len != len(module.body.block._first_op.body.block.ops): 
                self.num_hge += 1
                if print_output:
                    print("\n\nHermitian elimination")
                    Printer().print_op(module)


            clone_len = len(module.body.block._first_op.body.block.ops)
            inPlacing = InPlacing()
            # apply_recusively = False in order to not apply it to new operation inserted by the pattern itself
            PatternRewriteWalker(inPlacing,walk_regions_first=False,apply_recursively=False).rewrite_module(module)
            self.inplacing_gate_elim += inPlacing.inplacing_gate_elim
            self.inplacing_init_elim += inPlacing.inplacing_init_elim
            # free up memory
            del inPlacing

            # check if any inplacing has been done
            if clone_len != len(module.body.block._first_op.body.block.ops):
                self.num_inplacing += 1
                if print_output:
                    print("\n\nInplacing")
                    Printer().print_op(module)
        
            # renumber qubits after all transformations
            PatternRewriteWalker(QubitRenumber()).rewrite_module(module)
            
            initOp_num = len(module.body.block._args)
            gate_num = 0
            for op in module.body.block._first_op.body.block.ops:
                if op.name == "quantum.init":
                    initOp_num +=1
                elif op.name != "quantum.measure":
                    gate_num += 1
            
            # check if there were no changes in the last iteration
            if start_len == len(module.body.block._first_op.body.block.ops):
                break
            else:
                gateslist.append(gate_num)
                qubitlist.append(initOp_num)

        self.module = module
        # Final IR
        if print_output:
            print("\n\nFinal IR:\n")
            Printer().print_op(module)
            print("\n\n")
    
    # Transform ccnot gates in a composition of hadamard, tgate and cnot gates
    # in order to apply metrics for validation
    def metrics_transformation(self, print_output = False):

        #print("Performing CCNOT decomposition...")
        PatternRewriteWalker(CCnot_decomposition(),walk_regions_first=False,apply_recursively=False).rewrite_module(self.module)

        if print_output:
            print("\n\nCCNOT decomposition:\n")
            Printer().print_op(self.module)
            print("\n\n")

# @profile decorator to measure memory usage
# @profile
def main():
    gateslist = []
    qubitlist = []

    ccnot_gateslist = []
    ccnot_qubitlist = []
    try:
        quantum_ir = QuantumIR()
        quantum_ir.run_dataclass()
        quantum_ir.run_generate_ir()
        quantum_ir.run_transformations(False,gateslist,qubitlist)
        quantum_ir.metrics_transformation()
        quantum_ir.run_transformations(False,ccnot_gateslist,ccnot_qubitlist)
        print("\n",gateslist)
        print(ccnot_gateslist)
        print("\n",qubitlist)
        print(ccnot_qubitlist)
        
    except:
        print("Error in the execution of the program")
        raise

# Only run this if the file is executed directly, not imported
if __name__ == "__main__":
    main()
    peak_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(f"Picco massimo di memoria: {peak_memory / 1024:.2f} MB")

# inner psutil function
def process_memory():
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    return mem_info.rss

# decorator function
def profile(func):
    def wrapper(*args, **kwargs):

        mem_before = process_memory()
        result = func(*args, **kwargs)
        mem_after = process_memory()
        print("{}:consumed memory: {:,}".format(
            func.__name__,
            mem_before, mem_after, mem_after - mem_before))

        return result
    return wrapper