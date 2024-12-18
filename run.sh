#!/bin/bash

clear

cd build

totest=and

rm -f ../test-outputs/${totest}.out

./verilog_to_json ../test-inputs/$totest.sv >> ../test-outputs/${totest}.out

exit_code=$?

if [ $exit_code -eq 0 ]; then
        cd ..

        python3 main.py >> test-outputs/${totest}.out
else
    echo "Error in SLANG compilation."
    exit $exit_code  
fi

