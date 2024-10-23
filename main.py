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





                    ############# MAIN PROGRAM #############
                    
class QuantumIR():
    
    json_path : str = 'build/output.json'
    dataclass_output: str = 'test-outputs/dataclass_ast.txt'
    output_dir : str = 'test-outputs'
    ir_output_file: str = 'test-outputs/ir.txt'
    root : JSON_to_DataClasses.Root
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

    def run_generate_ir(self):
        # Generate IR
        ir_gen = IRGen()
        module = ir_gen.ir_gen_module(self.root)
        self.module = module
        print("\nIR:\n")
        Printer().print_op(self.module)

    def run_transformations(self):
        # Transformations
        print("\n\nTransformations:")
        module = self.module
        while True:

            start_module = module.clone()
            PatternRewriteWalker(RemoveUnusedOperations()).rewrite_module(module)

            # check if any unused operations were removed
            if len(start_module.body.block._first_op.body.block.ops) != len(module.body.block._first_op.body.block.ops):
                print("\n\nRemoved unused operations")
                Printer().print_op(module)

            PatternRewriteWalker(QubitRenumber()).rewrite_module(module)

            clone_module = module.clone()
            CommonSubexpressionElimination().apply(module)

            # check if any common subexpressions were eliminated
            if len(clone_module.body.block._first_op.body.block.ops) != len(module.body.block._first_op.body.block.ops):
                print("\n\nCommon subexpression elimination")
                Printer().print_op(module)

            clone_module = module.clone()
            HermitianGatesElimination().apply(module)

            # check if any common subexpressions were eliminated
            if len(clone_module.body.block._first_op.body.block.ops) != len(module.body.block._first_op.body.block.ops):
                print("\n\nHermitian elimination")
                Printer().print_op(module)

            clone_module = module.clone()
            PatternRewriteWalker(InPlacing()).rewrite_module(module)
            
            # check if any inplacing has been done
            if len(clone_module.body.block._first_op.body.block.ops) != len(module.body.block._first_op.body.block.ops):
                print("\n\nInplacing")
                Printer().print_op(module)
            
            PatternRewriteWalker(QubitRenumber()).rewrite_module(module)


            # check if there were no changes in the last iteration
            if len(start_module.body.block._first_op.body.block.ops) == len(module.body.block._first_op.body.block.ops):
                print("\n\nNo more transformations possible\n")
                break
        
         # Final IR
        print("\nFinal IR:\n")
        Printer().print_op(module)
        print("\n\n")
    
    def metric_transformation(self):

        PatternRewriteWalker(CCnot_decomposition()).rewrite_module(self.module)
        print("\n\nCCNOT decomposition:\n")
        Printer().print_op(self.module)
        print("\n\n")


# Run
quantum_ir = QuantumIR()
quantum_ir.run_dataclass()
quantum_ir.run_generate_ir()
quantum_ir.run_transformations()

quantum_ir.metric_transformation()
