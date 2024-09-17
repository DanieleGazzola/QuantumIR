import os

import JSON_to_DataClasses
from xdsl.printer import Printer
from frontend.ir_gen import IRGen

from frontend.common_subexpr_elimination import CommonSubexpressionElimination
from frontend.remove_unused_op import RemoveUnusedOperations
from frontend.hermitian_gates_transformation import HermitianGatesElimination
from xdsl.pattern_rewriter import PatternRewriteWalker

                    ############# MAIN PROGRAM #############

# Read JSON file and fix last characters
file_path = 'build/output.json'
with open(file_path, 'r') as file:
    data = file.read()

pos = data.rfind("}")
# If you find last closed curly bracket remove everything after it
if pos != -1:
    data = data[:pos + 1]
# Rewrite the file
with open(file_path, 'w') as file:
    file.write(data)

json_data = JSON_to_DataClasses.read_json_file(file_path)

# Output JSON file
output_dir = 'test-outputs'
output_path = 'test-outputs/json_ast.txt'
os.makedirs(output_dir, exist_ok=True)
with open(output_path, 'w') as file:
    file.write(json_data)

# Convert JSON to DataClasses
root = JSON_to_DataClasses.json_to_ast(json_data)

# Output DataClasses file
output_path = 'test-outputs/dataclass_ast.txt'
with open(output_path, 'w') as file:
    formatted_ast = JSON_to_DataClasses.format_root(root)
    file.write("\n".join(formatted_ast))

# Generate IR
ir_gen = IRGen()
module = ir_gen.ir_gen_module(root)
print("\nIR:\n")
Printer().print_op(module)

# Transformations
print("\n\nTransformations:")

while True:

    start_module = module.clone()
    PatternRewriteWalker(RemoveUnusedOperations()).rewrite_module(module)

    # check if any unused operations were removed
    if len(start_module.body.block._first_op.body.block.ops) != len(module.body.block._first_op.body.block.ops):
        print("\n\nRemoved unused operations")
        Printer().print_op(module)

    middle_module = module.clone()
    CommonSubexpressionElimination().apply(module)

    # check if any common subexpressions were eliminated
    if len(middle_module.body.block._first_op.body.block.ops) != len(module.body.block._first_op.body.block.ops):
        print("\n\nCommon subexpression elimination")
        Printer().print_op(module)

    end_module = module.clone()
    HermitianGatesElimination().apply(module)

    # check if any common subexpressions were eliminated
    if len(end_module.body.block._first_op.body.block.ops) != len(module.body.block._first_op.body.block.ops):
        print("\n\nHermitian elimination")
        Printer().print_op(module)

    # check if there were no changes in the last iteration
    if len(start_module.body.block._first_op.body.block.ops) == len(module.body.block._first_op.body.block.ops):
        print("\n\nNo more transformations possible\n")
        break

# Final IR
print("\nFinal IR:\n")
Printer().print_op(module)