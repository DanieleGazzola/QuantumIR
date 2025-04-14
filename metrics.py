from main import QuantumIR
import backend.JSON_to_DataClasses as JSON_to_DataClasses

from qiskit import QuantumCircuit

import sys
import time
import tracemalloc
import gc


######### FUNCTIONS #########

# Function to create a quantum circuit from the IR
def create_circuit(first_op, qubit_number, output_number):
    
    not_count = 0
    cnot_count = 0
    ccnot_count = 0
    tgate_count = 0
    tdagger_count = 0
    hgate_count = 0

    circuit = QuantumCircuit(qubit_number, output_number)
    current = first_op
    cbit_index = 0

    circuit.initialize(1)

    while(current is not None):
        operands_names = [op._name for op in current.operands]
        indexes = [int(name.split("_")[0][1:]) for name in operands_names]

        if current.name == "quantum.not":
            not_count += 1
            circuit.x(indexes[0])
        if current.name  == "quantum.cnot":
            cnot_count += 1
            circuit.cx(indexes[0], indexes[1])
        if current.name == "quantum.ccnot":
            ccnot_count += 1
            circuit.ccx(indexes[0], indexes[1], indexes[2])
        if current.name == "quantum.h":
            hgate_count += 1
            circuit.h(indexes[0])
        if current.name == "quantum.t":
            tgate_count += 1
            circuit.t(indexes[0])
        if current.name == "quantum.tdagger":
            tdagger_count += 1
            circuit.tdg(indexes[0])
        if current.name == "quantum.measure":
            circuit.measure(indexes[0], cbit_index)
            cbit_index += 1
        
        current = current.next_op
    
    gatelist ={}
    gatelist["Quantum Not"] = not_count
    gatelist["Quantum CNot"] = cnot_count
    gatelist["Quantum CCNot"] = ccnot_count
    gatelist["Quantum T"] = tgate_count
    gatelist["Quantum TDagger"] = tdagger_count
    gatelist["Quantum H"] = hgate_count

    return [circuit,gatelist]

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


# Generate basic IR, measure time and memory
tracemalloc.start()
basictime_start = time.perf_counter()
quantum_ir = QuantumIR()
quantum_ir.run_dataclass()
quantum_ir.run_generate_ir(print_output = False)
print("\nGenerating basic quantum circuit with CCNOT decomposition")
quantum_ir.metrics_transformation(print_output = False)
basictime_end = time.perf_counter()
_ , basic_mempeak = tracemalloc.get_traced_memory()
basic_ir = quantum_ir
tracemalloc.stop()

# Clean up memory
gc.collect()

# Generate optimized IR, measure time and memory
tracemalloc.start()
opttime_start = time.perf_counter()
quantum_ir = QuantumIR()
quantum_ir.run_dataclass()
quantum_ir.run_generate_ir(print_output = False)
print("\nGenerating optimized quantum circuit with CCNOT decomposition")
quantum_ir.run_transformations(print_output = False)
quantum_ir.metrics_transformation(print_output = False)
quantum_ir.run_transformations(print_output = False)
opttime_end = time.perf_counter()
_ , opt_mempeak = tracemalloc.get_traced_memory()
transformed_ir = quantum_ir
tracemalloc.stop()

# Metrics input file
print("\n\nInput file metrics:") 
print(f"    Number of inputs: {JSON_to_DataClasses.num_inputs}")
print(f"    Number of outputs: {JSON_to_DataClasses.num_outputs}")
print(f"    Number of local variables: {JSON_to_DataClasses.num_locals}")
print(f"    Number of AND gates: {JSON_to_DataClasses.num_ands}")
print(f"    Number of OR gates: {JSON_to_DataClasses.num_ors}")
print(f"    Number of NOT gates: {JSON_to_DataClasses.num_nots}")
print(f"    Number of XOR gates: {JSON_to_DataClasses.num_xors}")
# Metrics for basic circuit

module = basic_ir.module
funcOp = module.body.block._first_op

input_args = funcOp.body.block._args

first_op = funcOp.body.block._first_op

info_basic = get_quantum_circuit_info(input_args, first_op)

[circuit,basic_gatelist] = create_circuit(first_op, info_basic["qubit_number"], info_basic["output_number"])

basic_metrics = metrics(circuit)

# Metrics for optimized circuit

module = transformed_ir.module
funcOp = module.body.block._first_op

input_args = funcOp.body.block._args

first_op = funcOp.body.block._first_op

info_transformed = get_quantum_circuit_info(input_args, first_op)

[circuit,opt_gatelist] = create_circuit(first_op, info_transformed["qubit_number"], info_transformed["output_number"])

transformed_metrics = metrics(circuit)

# Calculate saving percentage
savings = {}
for key, value in basic_metrics.items():
    if key in transformed_metrics:
        savings[key] = (value - transformed_metrics[key]) / value * 100
    

# Output
print("\n################ BASIC CIRCUIT ################")
print("\nGate list for the basic circuit:")
for key, value in basic_gatelist.items():
    print(f"{key}: {value}")

print("\nMetrics for the basic circuit:")
for key, value in basic_metrics.items():
    print(f"{key}: {value}")

print("\nNumber of input qubits: ", info_basic["input_number"], 
      "\nNumber of support qubits: ", info_basic["init_number"], 
      "\nTotal qubits used: ", info_basic["qubit_number"], 
      "\nNumber of output bits: ", info_basic["output_number"])

print("\n################ OPTIMIZED CIRCUIT ################")
print("\nGate list for the optimized circuit:")
for key, value in opt_gatelist.items():
    print(f"{key}: {value}")

print("\nMetrics for the optimized circuit:")
for key, value in transformed_metrics.items():
    saving = savings.get(key, 0)
    print(f"{key}: {value} ({saving:.2f}%)")

print("\nNumber of input qubits: ", info_transformed["input_number"], 
      "\nNumber of support qubits: ", info_transformed["init_number"], 
      "\nTotal qubits used: ", info_transformed["qubit_number"], 
      "\nNumber of output bits: ", info_transformed["output_number"])

print("\n################ PERFORMANCE ################")
print(f"\nBasic circuit generation time: {basictime_end - basictime_start:.3f} seconds")
print(f"Optimized circuit generation time: {opttime_end - opttime_start:.3f} seconds")

print(f"\nBasic circuit memory peak: {basic_mempeak / 10**6:.3f} MB")
print(f"Optimized circuit memory peak: {opt_mempeak / 10**6:.3f} MB")
sys.exit(0)