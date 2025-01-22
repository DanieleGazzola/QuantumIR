import os
import re

def check_files_in_folder(folder_path, regex_pattern):
    # Compila la regex
    pattern = re.compile(regex_pattern)

    # Controlla ogni file nella cartella
    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)

            # Controlla solo i file di testo
            if file.endswith('.out'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line_number, line in enumerate(f, start=1):
                            if pattern.search(line):
                                print(f"Match trovato in {file_path}, linea {line_number}: {line.strip()}")
                except Exception as e:
                    print(f"Errore nel leggere il file {file_path}: {e}")

if __name__ == "__main__":
    folder_path = "test-outputs/"
    regex_pattern = r"%q\d+_\d+_\d+"

    if os.path.isdir(folder_path):
        check_files_in_folder(folder_path, regex_pattern)
    else:
        print("Il percorso specificato non è una cartella valida.")