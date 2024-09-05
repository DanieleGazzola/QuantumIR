#!/bin/bash

clear

cd build

./verilog_to_json ../test-inputs/full_adder.sv

cd ..

python3 main.py