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

    # Number of times each transformation is executed
    num_cse : int = 0
    num_dce : int = 0
    num_inplacing : int = 0
    num_hge : int = 0
    
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
        # Print input file metrics
        print("\n\nInput file metrics:") 
        print(f"    Number of inputs: {JSON_to_DataClasses.num_inputs}")
        print(f"    Number of outputs: {JSON_to_DataClasses.num_outputs}")
        print(f"    Number of local variables: {JSON_to_DataClasses.num_locals}")
        print(f"    Number of AND gates: {JSON_to_DataClasses.num_ands}")
        print(f"    Number of OR gates: {JSON_to_DataClasses.num_ors}")
        print(f"    Number of NOT gates: {JSON_to_DataClasses.num_nots}")
        print(f"    Number of XOR gates: {JSON_to_DataClasses.num_xors}")
        
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

    def run_transformations(self, print_output = True):
        if print_output:
            print("\n\nTransformations:")

        module = self.module
        while True:

            start_len = len(module.body.block._first_op.body.block.ops)
            
            #print("\nPerforming Remove Unused Operations...")
            PatternRewriteWalker(RemoveUnusedOperations()).rewrite_module(module)

            # check if any unused operations were removed
            if print_output and start_len != len(module.body.block._first_op.body.block.ops):
                self.num_dce += 1
                print("\n\nRemoved unused operations")
                Printer().print_op(module)
            #elif start_len == len(module.body.block._first_op.body.block.ops):   
                #print("No unused operations to remove\n")

            PatternRewriteWalker(QubitRenumber()).rewrite_module(module)

            clone_len = len(module.body.block._first_op.body.block.ops)
            #print("\nPerforming Common Subexpression Elimination...")
            CommonSubexpressionElimination().apply(module)

            # check if any common subexpressions were eliminated
            if print_output and clone_len != len(module.body.block._first_op.body.block.ops):
                self.num_cse += 1
                print("\n\nCommon subexpression elimination")
                Printer().print_op(module)
            #elif clone_len == len(module.body.block._first_op.body.block.ops):
                #print("No common subexpressions to eliminate\n")
        
            clone_len = len(module.body.block._first_op.body.block.ops)
            #print("\nPerforming Hermitian Gates Elimination...")
            HermitianGatesElimination().apply(module)

            # check if any common subexpressions were eliminated
            if print_output and clone_len != len(module.body.block._first_op.body.block.ops):
                self.num_hge += 1
                #print("\n\nHermitian elimination")
                Printer().print_op(module)
            #elif clone_len == len(module.body.block._first_op.body.block.ops):
                #print("No Hermitian eliminations to be performed\n")

            clone_len = len(module.body.block._first_op.body.block.ops)
            #print("\nPerforming Inplacing...")
            # apply_recusively = False in order to not apply it to new operation inserted by the pattern itself
            PatternRewriteWalker(InPlacing(),walk_regions_first=False,apply_recursively=False).rewrite_module(module)

            # check if any inplacing has been done
            if print_output and clone_len != len(module.body.block._first_op.body.block.ops):
                self.num_inplacing += 1
                #print("\n\nInplacing")
                Printer().print_op(module)
            #elif clone_len == len(module.body.block._first_op.body.block.ops):
                #print("No inplacing to be performed\n")
            
            # renumber qubits after all transformations
            PatternRewriteWalker(QubitRenumber()).rewrite_module(module)

            # check if there were no changes in the last iteration
            if start_len == len(module.body.block._first_op.body.block.ops):
                #if print_output: 
                    #print("\nNo more transformations possible\n")
                break


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
    try:
        quantum_ir = QuantumIR()
        quantum_ir.run_dataclass()
        quantum_ir.run_generate_ir()
        quantum_ir.run_transformations()
        quantum_ir.metrics_transformation()
        quantum_ir.run_transformations()

        print("\n\nTransformation summary:")
        print(f"    Number of CSE: {quantum_ir.num_cse}")
        print(f"    Number of DCE: {quantum_ir.num_dce}")
        print(f"    Number of Inplacing: {quantum_ir.num_inplacing}")
        print(f"    Number of HGE: {quantum_ir.num_hge}")
        print("\n\n")
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