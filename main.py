import os

import JSON_to_DataClasses
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

    def run_transformations(self, print_output = True):
        if print_output:
            print("\n\nTransformations:")

        module = self.module
        while True:

            start_len = len(module.body.block._first_op.body.block.ops)
            
            PatternRewriteWalker(RemoveUnusedOperations()).rewrite_module(module)

            # check if any unused operations were removed
            if print_output and start_len != len(module.body.block._first_op.body.block.ops):
                print("\n\nRemoved unused operations")
                Printer().print_op(module)
            else:
                print("\n\nNo unused operations to remove\n")

            PatternRewriteWalker(QubitRenumber()).rewrite_module(module)

            clone_len = len(module.body.block._first_op.body.block.ops)
            CommonSubexpressionElimination().apply(module)

            # check if any common subexpressions were eliminated
            if print_output and clone_len != len(module.body.block._first_op.body.block.ops):
                print("\n\nCommon subexpression elimination")
                Printer().print_op(module)
            else:
                print("\n\nNo common subexpressions to eliminate\n")
        
            clone_len = len(module.body.block._first_op.body.block.ops)
            HermitianGatesElimination().apply(module)

            # check if any common subexpressions were eliminated
            if print_output and clone_len != len(module.body.block._first_op.body.block.ops):
                print("\n\nHermitian elimination")
                Printer().print_op(module)
            else:
                print("\n\nNo Hermitian eliminations to be performed\n")

            clone_len = len(module.body.block._first_op.body.block.ops)
            # apply_recusively = False in order to not apply it to new operation inserted by the pattern itself
            PatternRewriteWalker(InPlacing(),walk_regions_first=False,apply_recursively=False).rewrite_module(module)

            # check if any inplacing has been done
            if print_output and clone_len != len(module.body.block._first_op.body.block.ops):
                print("\n\nInplacing")
                Printer().print_op(module)
            else:
                print("\n\nNo inplacing to be performed\n")
            
            PatternRewriteWalker(QubitRenumber()).rewrite_module(module)

            # check if there were no changes in the last iteration
            if start_len == len(module.body.block._first_op.body.block.ops):
                if print_output: 
                    print("\n\nNo more transformations possible\n")
                break
        
        # Final IR
        if print_output:
            print("\nFinal IR:\n")
            Printer().print_op(module)
            print("\n\n")
    
    # transform ccnot gates in a composition of hadamard, tgate and cnot gates
    # in order to apply metrics for validation
    def metrics_transformation(self, print_output = True):

        PatternRewriteWalker(CCnot_decomposition()).rewrite_module(self.module)

        if print_output:
            print("\n\nCCNOT decomposition:\n")
            Printer().print_op(self.module)
            print("\n\n")


# Only run this if the file is executed directly, not imported
if __name__ == "__main__":
    quantum_ir = QuantumIR()
    quantum_ir.run_dataclass()
    quantum_ir.run_generate_ir()
    cProfile.run("quantum_ir.run_transformations()","profile")
    p = pstats.Stats("profile")
    p.strip_dirs().sort_stats("cumulative").print_stats(20)
    p.strip_dirs().sort_stats("time").print_stats(20)
    p.print_callers()

# quantum_ir.metrics_transformation()
# quantum_ir.run_transformations()
