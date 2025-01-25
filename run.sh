#!/bin/bash

clear

cd build

input='crypto_benchmarks/mem_ctrl_untilsat.v'

rm -f ../test-outputs/${totest}.out

touch ../test-outputs/${totest}.out

./verilog_to_json ../test-inputs/${input} > ../test-outputs/${totest}.out

exit_code=$?

if [ $exit_code -eq 0 ]; then
        cd ..

        python3 main.py > test-outputs/${totest}.out 2>&1
else
    echo "Error in SLANG compilation."
    exit $exit_code  
fi

