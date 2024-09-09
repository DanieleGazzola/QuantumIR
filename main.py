import os

import JSON_to_DataClasses
from xdsl.printer import Printer
from frontend.ir_gen import IRGen

from frontend.ir_transform import RemoveUnusedOperations, CommonSubexpressionElimination
from xdsl.pattern_rewriter import PatternRewriteWalker

# Main Program

# Read JSON file
file_path = 'build/output.json'
json_data = JSON_to_DataClasses.read_json_file(file_path)
json_data = json_data[:-2]

# Output JSON file
output_dir = 'test-outputs'
output_path = 'test-outputs/json_ast.txt'
os.makedirs(output_dir, exist_ok=True)
with open(output_path, 'w') as file:
    file.write(json_data)

# Convert JSON to DataClasses
ast = JSON_to_DataClasses.json_to_ast(json_data)

# Output DataClasses file
output_path = 'test-outputs/dataclass_ast.txt'
with open(output_path, 'w') as file:
    formatted_ast = JSON_to_DataClasses.format_ast(ast)
    file.write("\n".join(formatted_ast))

# Generate MLIR
mlir_gen = IRGen()
module_op = mlir_gen.ir_gen_module(ast)
Printer().print_op(module_op)

# Transformations
print("")
print("")
print("Transformations:")
print("")

while True:
    start_op = module_op.clone()

    PatternRewriteWalker(RemoveUnusedOperations()).rewrite_module(module_op)
    if len(start_op.body.block._first_op.body.block.ops) != len(module_op.body.block._first_op.body.block.ops):
        print("")
        print("Removed unused operations")
        print("")
        Printer().print_op(module_op)
        print("")

    middle_op = module_op.clone()
    
    CommonSubexpressionElimination().apply(module_op)
    if len(middle_op.body.block._first_op.body.block.ops) != len(module_op.body.block._first_op.body.block.ops):
        print("")
        print("Common subexpression elimination")
        print("")
        Printer().print_op(module_op)
        print("")

    if len(start_op.body.block._first_op.body.block.ops) == len(module_op.body.block._first_op.body.block.ops):
        print("")
        print("No more transformations possible")
        print("")
        break

# Final IR
print("")
print("Final IR:")
print("")
Printer().print_op(module_op)
print("")