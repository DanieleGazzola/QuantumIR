start_file="sha-256_untilsat.v"
end_file="sha-256_untilsat.v"

start=false
for file in "$dir"/*; do
    filename=$(basename "$file")
    basefile=${filename%%.*}
    outname=${basefile%%.*}

    if [[ "$start" == false ]]; then
      if [[ "$(basename "$file")" == "$start_file" ]]; then
        start=true
      else
        continue
      fi
    fi

    echo "Processing $filename"
    ./run.sh "crypto_benchmarks/$filename" -m > test-outputs/${outname}.metrics
    exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo "Error processing $filename"
        exit $exit_code
    fi

    if [[ "$(basename "$file")" == "$end_file" ]]; then
      break
    fi
done