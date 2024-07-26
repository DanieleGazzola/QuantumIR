#!/bin/bash

clear

echo "Verilog to JSON AST"

echo

cd build

./verilog_to_json ../test-inputs/full_adder_extended.sv

echo 

echo "JSON AST to DataClasses"

echo

cd ..

python3 main.py