import os
import json
from xdsl.ir import Dialect, Operation
from xdsl.dialects.builtin import StringAttr
from xdsl.printer import Printer
from frontend.ir_gen import IRGen

import JSON_to_DataClasses
from xdsl.printer import Printer
from frontend.ir_gen import IRGen

# Main Program
file_path = 'build/output.json'
json_data = JSON_to_DataClasses.read_json_file(file_path)
json_data = json_data[:-2]
output_dir = 'test-outputs'
output_path = 'test-outputs/json_ast.txt'
os.makedirs(output_dir, exist_ok=True)
with open(output_path, 'w') as file:
    file.write(json_data)
ast = JSON_to_DataClasses.json_to_ast(json_data)

# Write DataClasses
output_path = 'test-outputs/dataclass_ast.txt'
with open(output_path, 'w') as file:
    formatted_ast = JSON_to_DataClasses.format_ast(ast)
    file.write("\n".join(formatted_ast))

mlir_gen = IRGen()
module_op = mlir_gen.ir_gen_module(ast)
Printer().print_op(module_op)


# ------------------------------------------------------

# class VerilogDialect(Dialect):
#     _name = "verilog"

#     def __init__(self):
#         super().__init__(self._name)

# class ModuleOp(Operation):
#     name = "verilog.module"
#     name_attr: StringAttr

#     def __init__(self, name: StringAttr):
#         super().__init__(attributes=[("name", name)])

# class PortOp(Operation):
#     name = "verilog.port"
#     name_attr: StringAttr
#     type_attr: StringAttr
#     direction_attr: StringAttr

#     def __init__(self, name: StringAttr, port_type: StringAttr, direction: StringAttr):
#         super().__init__(attributes=[("name", name), ("type", port_type), ("direction", direction)])

# class VariableOp(Operation):
#     name = "verilog.variable"
#     name_attr: StringAttr
#     type_attr: StringAttr

#     def __init__(self, name: StringAttr, var_type: StringAttr):
#         super().__init__(attributes=[("name", name), ("var_type", var_type)])

# class ContinuousAssignOp(Operation):
#     name = "verilog.continuous_assign"
#     lhs_attr: StringAttr
#     rhs_attr: StringAttr

#     def __init__(self, lhs: StringAttr, rhs: StringAttr):
#         super().__init__(attributes=[("lhs", lhs), ("rhs", rhs)])

# # Conversion functions
# def convert_port(port):
#     return PortOp(StringAttr(port.name), StringAttr(port.type), StringAttr(port.direction))

# def convert_variable(variable):
#     return VariableOp(StringAttr(variable.name), StringAttr(variable.type))

# def convert_continuous_assign(assign):
#     lhs = assign.assignment.left.symbol
#     rhs_left = assign.assignment.right.left.symbol
#     rhs_right = assign.assignment.right.right.symbol
#     rhs_op = assign.assignment.right.op
#     rhs = f"{rhs_left} {rhs_op} {rhs_right}"
#     return ContinuousAssignOp(StringAttr(lhs), StringAttr(rhs))

# def convert_instance_body(body):
#     ops = []
#     for member in body.members:
#         if member.kind == "Port":
#             ops.append(convert_port(member))
#         elif member.kind == "Variable":
#             ops.append(convert_variable(member))
#         elif member.kind == "ContinuousAssign":
#             ops.append(convert_continuous_assign(member))
#     return ops

# def convert_instance(instance):
#     body_ops = convert_instance_body(instance.body)
#     return body_ops

# def convert_root(root):
#     ops = []
#     for member in root.members:
#         if member.kind == "Instance":
#             ops.extend(convert_instance(member))
#     return ops

# def read_json_file(file_path: str) -> str:
#     with open(file_path, 'r') as file:
#         return file.read()


# # Convert Data to MLIR
# mlir_representation = convert_root(ast)

# # Print or use the MLIR representation
# for op in mlir_representation:
#     print(op)
