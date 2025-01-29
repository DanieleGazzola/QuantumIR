# Quantum Intermediate Representation for SystemVerilog

This is the repository for the "Quantum IR" project of the Code Optimization and Transformation course (Politecnico di Milano, A.Y. 2023/2024). \
With this work, we aim to create a bridge between classical and quantum circuits through the creation of an Intermediate Representation (IR) that is elaborated from classical hardware descriptor languages, but is implementable on quantum hardware. 

## Prerequisites

- **slang**: a software library written in C++ that provides components for parsing SystemVerilog code
- **Python**: a versatile, easy-to-read programming language
- **xDSL**: a Python-native SSA compiler framework for building MLIR
- **Qiskit**: an open-source quantum computing framework for building, running, and optimizing quantum programs

## Program Pipeline

The input SystemVerilog file is processed with Slang, which parses it and creates the corresponding Abstract Syntax Tree (AST). \
The syntax tree is converted from JSON format to Python Dataclass objects. \
Then, it is traversed; each node is translated into MLIR operations thanks to xDSL. \
Finally, once the first output is obtained, different optimization passes are applied to save on qubits and gates.

## Getting Started

First of all, clone the repository and build the project:

```bash
git clone git@github.com:DanieleGazzola/QuantumIR.git

mkdir build
cd build/
cmake ..
cmake --build .
cd ..
chmod +x run.sh
```

The main executable is the `run.sh` script. \
Its basic usage is:
```bash
./run.sh <filename>
```

Two more flags are available:
- `-m`: after the creation of the final MLIR, it evaluates different metrics of the corresponding quantum circuit
- `-v`: perform validation against the available test files in the `/test-inputs` directory
