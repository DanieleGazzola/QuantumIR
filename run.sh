#!/bin/bash

clear

cd build

./verilog_to_json ../test-inputs/input.sv

cd ..

python3 main.py