#!/bin/bash

#clear

# Check if a filename is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <filename> [-validate|-v] [-metrics|-m]"
    exit 1
fi

# Set the filename and shift it out of the arguments
filename="$1"
echo "Processing file: $filename"
shift
basefile=$(basename "$filename")
outname=${basefile%%.*}

# Navigate to the build directory
cd build

# Ensure output file is clean
rm -f ../test-outputs/${outname}.out
touch ../test-outputs/${outname}.out

# Start program
./verilog_to_json ../${filename} > ../test-outputs/${outname}.out
exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo "Error: verilog_to_json failed with exit code $exit_code"
    exit $exit_code
fi
# List of allowed filenames for validation
allowed_files=("test-inputs/and.sv" "test-inputs/cse.sv" "test-inputs/full_adder.sv" "test-inputs/inplace.sv" "test-inputs/not.sv" 
"test-inputs/proceduralBlock.sv" "test-inputs/remove_unused.sv" "test-inputs/xorInPlace.sv")

# Parse command-line arguments for optional steps
run_validate=false
run_metrics=false
# If no argument are provided simply run the program
if [ $# -eq 0 ];then
    cd ..
    echo ${filename} > "test-outputs/${outname}.out"
    (time python3 main.py) &>> "test-outputs/${outname}.out"
else # else decide based on the argument
    for arg in "$@"; do
        case $arg in
            -validate|-v)
                if [[ " ${allowed_files[@]} " =~ " ${filename} " ]]; then
                    run_validate=true
                else
                    echo "Validation is not enabled for this file."
                fi
                ;;
            -metrics|-m)
                run_metrics=true
                ;;
            *)
                echo "Unknown option: $arg"
                exit 1
                ;;
        esac
    done
fi
# Run optional steps
if $run_validate; then
    cd ..
    python3 validate.py ${outname} > "./test-outputs/${outname}.val"
fi

if $run_metrics; then
    cd ..
    python3 metrics.py > "./test-outputs/${outname}.out"
fi
