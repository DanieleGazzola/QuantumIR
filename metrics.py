from main import QuantumIR

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit.converters import circuit_to_dag
from qiskit.dagcircuit import DAGOpNode

import numpy as np

import sys
import csv

######### FUNCTIONS #########

# Function to create a quantum circuit from the IR
def create_circuit(first_op, qubit_number, output_number):

    circuit = QuantumCircuit(qubit_number, output_number)
    current = first_op
    cbit_index = 0

    circuit.initialize(1)

    while(current is not None):
        operands_names = [op._name for op in current.operands]
        indexes = [int(name.split("_")[0][1:]) for name in operands_names]

        if current.name == "quantum.not":
            circuit.x(indexes[0])
        if current.name  == "quantum.cnot":
            circuit.cx(indexes[0], indexes[1])
        if current.name == "quantum.ccnot":
            circuit.ccx(indexes[0], indexes[1], indexes[2])
        if current.name == "quantum.h":
            circuit.h(indexes[0])
        if current.name == "quantum.t":
            circuit.t(indexes[0])
        if current.name == "quantum.tdagger":
            circuit.tdg(indexes[0])
        if current.name == "quantum.measure":
            circuit.measure(indexes[0], cbit_index)
            cbit_index += 1
        
        current = current.next_op
    
    return circuit

# Support function to return information about the quantum circuit under analysis
def get_quantum_circuit_info(input_args, first_op):
    # Scroll through the IR tree to count the number of (qu)bits numbers
    input_number = input_args.__len__()
    output_number = 0
    init_number = 0

    current = first_op
    while(current is not None):
        if current.name == "quantum.init":
            init_number += 1
        if current.name == "quantum.measure":
            output_number += 1
        current = current.next_op

    qubit_number = input_number + init_number
    
    return {
    "input_number": input_number,
    "output_number": output_number,
    "init_number": init_number,
    "qubit_number": qubit_number
    }

# Functions to calculate the metrics

def metrics(circuit):
    # Circuit depth
    depth = circuit.depth()

    # Circuit width (number of qubits)
    width = circuit.num_qubits

    # Gate count (total number of gates)
    gate_count = circuit.size()

    # Count T gates
    t_gate_count = circuit.count_ops()['t'] + circuit.count_ops()['tdg']

    # T gate depth 
    t_gate_depth = circuit.depth(lambda instr: instr.operation.name in ['t', 'tdg'])

    return {
        "Depth": depth,
        "Width": width,
        "Gate Count": gate_count,
        "T Gate Count": t_gate_count,
        "T Gate Depth": t_gate_depth
    }

######### MAIN #########

for i in range(2):

    # Generate IR
    quantum_ir = QuantumIR()
    quantum_ir.run_dataclass()
    quantum_ir.run_generate_ir(print_output = False)

    if i == 0:
        print("\nGenerating basic quantum circuit with CCNOT decomposition")
        quantum_ir.metrics_transformation(print_output = False)
        basic_ir = quantum_ir
    if i == 1:
        print("\nGenerating optimized quantum circuit with CCNOT decomposition")
        quantum_ir.run_transformations(print_output = False)
        quantum_ir.metrics_transformation(print_output = False)
        quantum_ir.run_transformations(print_output = False)
        transformed_ir = quantum_ir

# Metrics for basic circuit

module = basic_ir.module
funcOp = module.body.block._first_op

input_args = funcOp.body.block._args

first_op = funcOp.body.block._first_op

info_basic = get_quantum_circuit_info(input_args, first_op)

circuit = create_circuit(first_op, info_basic["qubit_number"], info_basic["output_number"])

basic_metrics = metrics(circuit)

# Metrics for optimized circuit

module = transformed_ir.module
funcOp = module.body.block._first_op

input_args = funcOp.body.block._args

first_op = funcOp.body.block._first_op

info_transformed = get_quantum_circuit_info(input_args, first_op)

circuit = create_circuit(first_op, info_transformed["qubit_number"], info_transformed["output_number"])

transformed_metrics = metrics(circuit)

# Output

print("\nMetrics for the basic circuit:")
for key, value in basic_metrics.items():
    print(f"{key}: {value}")

print("\nNumber of input qubits: ", info_basic["input_number"], 
      "\nNumber of support qubits: ", info_basic["init_number"], 
      "\nTotal qubits used: ", info_basic["qubit_number"], 
      "\nNumber of output bits: ", info_basic["output_number"])

print("\nMetrics for the optimized circuit:")
for key, value in transformed_metrics.items():
    print(f"{key}: {value}")

print("\nNumber of input qubits: ", info_transformed["input_number"], 
      "\nNumber of support qubits: ", info_transformed["init_number"], 
      "\nTotal qubits used: ", info_transformed["qubit_number"], 
      "\nNumber of output bits: ", info_transformed["output_number"])

sys.exit(0)