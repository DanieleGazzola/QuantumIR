#!/bin/bash

clear

cd build

filename='cse.sv'

outname=${filename%%.*}

rm -f ../test-outputs/${outname}.out

touch ../test-outputs/${outname}.out

./verilog_to_json ../test-inputs/${filename} > ../test-outputs/${outname}.out

exit_code=$?

if [ $exit_code -eq 0 ]; then
        cd ..

        python3 main.py > test-outputs/${outname}.out 2>&1
else
    echo "Error in SLANG compilation."
    exit $exit_code  
fi

