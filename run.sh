#!/bin/bash

clear

cd build

./verilog_to_json ../test-inputs/xor.sv

cd ..

python3 main.py