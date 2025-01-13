#!/bin/bash

for file in "truth-tables"/*.csv
do
  # Get the base name of the file without the directory and extension
  base_name=$(basename "$file" .csv)
  
  echo "Processing $base_name..."

  cd build
  ./verilog_to_json ../test-inputs/$base_name.sv >> ../test-outputs/tested_circuits.txt
  cd ..
  
  python3 validate.py "$base_name"

  echo
  echo "----------------------------------------"
  echo
done
