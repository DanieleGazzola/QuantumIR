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
def create_circuit(first_op, qubit_number, output_number, state):

    circuit = QuantumCircuit(qubit_number, output_number)
    current = first_op
    cbit_index = 0

    qubit_list = [i for i in range(qubit_number)]

    circuit.initialize(state, qubit_list)

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

# Function to generate the quantum truth table
def generate_quantum_truth_table(first_op, qubit_number, init_number, output_number, istates):
    counts = {}
    quantum_truth_table = {}
    backend = AerSimulator()

    for i in range(2**qubit_number):
        circuit = create_circuit(first_op, qubit_number, output_number, istates[i])

        job = backend.run(circuit, shots=2000)
        result = job.result()

        # Consider only the entries where the support output qubits are set to zero.
        if istr[i][:init_number] == '0' * init_number:
            counts[istr[i][init_number:]] = result.get_counts()

        for outer_key, inner_dict in counts.items():
            for inner_key, value in inner_dict.items():
                quantum_truth_table[outer_key] = inner_key

    return quantum_truth_table

# Function to generate the classical truth table
def generate_classical_truth_table(circuit_name):
    classical_truth_table = {}

    with open(f'test-inputs/truth-tables/{circuit_name}.csv', 'r') as file:
        csv_reader = csv.DictReader(file)
        
        out_columns = [col for col in csv_reader.fieldnames if col.startswith('out')]
        
        for row in csv_reader:
            flipped_value = ''.join(str(row[col]) for col in reversed(out_columns))
            classical_truth_table[row['Inputs']] = flipped_value

    return classical_truth_table

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

    print("\nNumber of input qubits: ", input_number, 
          "\nNumber of support qubits: ", init_number, 
          "\nTotal qubits used: ", qubit_number, 
          "\nNumber of output bits: ", output_number)
    
    return {
    "input_number": input_number,
    "output_number": output_number,
    "init_number": init_number,
    "qubit_number": qubit_number
    }

# Support function to generate all possible bit strings of length N
def bit_strings_iterative(N):
    bit_list = ['']
    for _ in range(N):
        bit_list = ['0' + bit_string for bit_string in bit_list] + \
                   ['1' + bit_string for bit_string in bit_list]
    return bit_list

######### MAIN #########

if len(sys.argv) != 2:
    print("Please, provide exaclty one argument: the name of the circuit to be tested.")
    sys.exit(1)

circuit_name = sys.argv[1]
print(f"Testing {circuit_name} circuit...")

classical_truth_table = generate_classical_truth_table(circuit_name)

print('\nThe truth table of the equivalent classical circuit is:')
for key, value in classical_truth_table.items():
    print(f"{key}: {value}")

print("\n=========================================")

passed_tests = 0

for i in range(4):

    # Generate IR
    quantum_ir = QuantumIR()
    quantum_ir.run_dataclass()
    quantum_ir.run_generate_ir(print_output = False)

    if i == 0:
        print("\nTest 1: Basic quantum circuit")
        print("Testing...")
    if i == 1:
        print("\nTest 2: Optimized quantum circuit")
        print("Testing...")
        quantum_ir.run_transformations(print_output = False)
    if i == 2:
        print("\nTest 3: Basic quantum circuit with CCNOT decomposition")
        print("Testing...")
        quantum_ir.metrics_transformation(print_output = False)
    if i == 3:
        print("\nTest 4: Optimized quantum circuit with CCNOT decomposition")
        print("Testing...")
        quantum_ir.run_transformations(print_output = False)
        quantum_ir.metrics_transformation(print_output = False)
        quantum_ir.run_transformations(print_output = False)

    module = quantum_ir.module
    funcOp = module.body.block._first_op

    input_args = funcOp.body.block._args

    first_op = funcOp.body.block._first_op

    info = get_quantum_circuit_info(input_args, first_op)

    # Generate all possible inputs
    istr = bit_strings_iterative(info["qubit_number"])
    istates = np.eye(2**info["qubit_number"])

    quantum_truth_table = generate_quantum_truth_table(first_op, info["qubit_number"], info["init_number"], info["output_number"], istates)

    # Compare the truth tables
    valid = quantum_truth_table == classical_truth_table

    if valid:
        print("\nTest passed!")
        passed_tests += 1
    else:
        for key in quantum_truth_table:
            if quantum_truth_table[key] != classical_truth_table.get(key):
                print(f"Difference found at input {key}: quantum circuit returns {quantum_truth_table[key]}, ") 
                print(f"classical circuit returns {classical_truth_table.get(key)}")

    if (i < 3):
        print("\n-----------------------------------------")

print("\n=========================================")
print(f"\n{passed_tests} out of 4 tests passed.")

if passed_tests != 4:
    sys.exit(1)  # Failure: one or more tests failed

sys.exit(0)  # Success: all tests passed