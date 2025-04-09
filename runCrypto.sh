#!/bin/bash

DIR="./test-inputs/crypto_benchmarks"  # Cambia con il percorso della cartella

for file in "$DIR"/*; do
    if [[ -f "$file" ]]; then
        ./run.sh "$file" -m
    fi
done
