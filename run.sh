#!/bin/bash

clear

cd build

dirinput=''

totest=xorInPlace

rm -f ../test-outputs/${totest}.out

touch ../test-outputs/${totest}.out

./verilog_to_json ../test-inputs/${dirinput}${totest}.sv >> ../test-outputs/${totest}.out

exit_code=$?

if [ $exit_code -eq 0 ]; then
        cd ..

        python3 main.py >> test-outputs/${totest}.out
else
    echo "Error in SLANG compilation."
    exit $exit_code  
fi

