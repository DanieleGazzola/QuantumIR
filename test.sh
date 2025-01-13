#!/bin/bash

# Array to store failed circuits
failed_circuits=()

for file in "truth-tables"/*.csv
do
  # Get the base name of the file without the directory and extension
  base_name=$(basename "$file" .csv)

  cd build
  ./verilog_to_json ../test-inputs/$base_name.sv >> ../test-outputs/tested_circuits.txt
  cd ..
  
  if ! python3 validate.py "$base_name"; then
    failed_circuits+=("$base_name")
  fi

  echo
  echo "----------------------------------------"
  echo
done

if [ ${#failed_circuits[@]} -ne 0 ]; then
  echo "The following circuits didn't pass their tests:"
  for failed_circuit in "${failed_circuits[@]}"
  do
    echo "- $failed_circuit"
  done
else
  echo "All circuits passed their tests!"
fi
