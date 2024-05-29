#!/bin/bash

clear

echo "Verilog to JSON AST"

echo

cd build

./test ../input_simple.sv

echo 

echo "JSON AST to DataClasses"

echo

cd ..

python3 test.py