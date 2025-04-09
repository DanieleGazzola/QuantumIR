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

if [ $exit_code -eq 0 ]; then
    cd ..
    echo ${filename} > "test-outputs/${outname}.out"
    (time python3 main.py) &>> "test-outputs/${outname}.out"
else
    echo "Error in SLANG compilation."
    exit $exit_code
fi

# List of allowed filenames for validation
allowed_files=("and.sv" "cse.sv" "full_adder.sv" "inplace.sv" "not.sv" "proceduralBlock.sv" "remove_unused.sv" "xorInPlace.sv")

# Parse command-line arguments for optional steps
run_validate=false
run_metrics=false

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

# Run optional steps
if $run_validate; then
    python3 validate.py ${outname} >> "test-outputs/${outname}.out"
fi

if $run_metrics; then
    python3 metrics.py >> "test-outputs/${outname}.out"
fi
