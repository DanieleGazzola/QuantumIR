#!/bin/bash

# Specifica la directory contenente i file da elaborare
inputDir="test-inputs/crypto_benchmarks/"

# Loop su tutti i file .v nella directory di input
for file in "${inputDir}"*; do
    # Estrai il nome base del file (senza percorso e senza estensione)
    filename=$(basename -- "$file")
    totest="${filename%.*}"  # Rimuove l'estensione .v

    echo "Processing $file..."

    # Esegui il comando verilog_to_json
    ./build/verilog_to_json "$file" > "test-outputs/${totest}.out"

    # Controlla il codice di uscita
    exit_code=$?
    if [ $exit_code -eq 0 ]; then
        
        # Esegui lo script Python
        python3 main.py >> "test-outputs/${totest}.out" 2>&1
        echo "$file processed successfully."
    else
        echo "Error in SLANG compilation for $file."
        exit $exit_code
    fi
done

echo "All files processed."