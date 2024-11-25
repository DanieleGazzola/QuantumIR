#!/bin/bash

clear

cd build

./verilog_to_json ../test-inputs/hge.sv

exit_code=$?

if [ $exit_code -eq 0 ]; then
        cd ..

        python3 main.py
else
    echo "Error in SLANG compilation."
    exit $exit_code  
fi

