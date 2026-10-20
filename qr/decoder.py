import os
import base64
import zlib
from pathlib import Path
from config import (
    ENCODING, ENCODING_ERRORS, FILE_HEADER, FILE_DELIMITER, CHUNK_SEPARATOR,
    SCANS_INPUT_FILENAME, RESTORED_WORKSPACE_DIR, HEADER_WIDTH,
    SCANS_INSTRUCTION
)

def run_global_batch_decoder(scans_file_name: str = SCANS_INPUT_FILENAME):
    os.system('cls' if os.name == 'nt' else 'clear')

    print("=" * HEADER_WIDTH)
    print("DECODEUR GLOBAL EN RAFALE : INITIALISÉ")
    print("=" * HEADER_WIDTH)

    scans_file_path = Path.cwd() / scans_file_name
    output_root_directory = Path.cwd() / RESTORED_WORKSPACE_DIR

    if not scans_file_path.exists():
        with open(scans_file_path, "w", encoding=ENCODING) as f:
            f.write(f"{SCANS_INSTRUCTION}\n")
        print(f"Fichier de suivi créé à l'emplacement : '{scans_file_name}'")
        print("Collez vos segments scannés à l'intérieur, sauvegardez, puis relancez ce décodeur.")
        print("=" * HEADER_WIDTH)
        return

    with open(scans_file_path, "r", encoding=ENCODING) as f:
        raw_lines = f.readlines()

    fragments = []
    total_expected_chunks = None

    for idx, line in enumerate(raw_lines, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if CHUNK_SEPARATOR in line and "[" in line:
            try:
                header, b64_payload = line.split(CHUNK_SEPARATOR, 1)
                b64_payload = b64_payload.replace("]", "").strip()
                header_parts = header.replace("[", "").split("/")

                part_num = int(header_parts[0])
                total_expected_chunks = int(header_parts[1])
                fragments.append((part_num, b64_payload))
            except Exception:
                print(f"Ligne {idx} ignorée : Format de l'en-tête corrompu.")
                continue
        else:
            fragments.append((1, line))

    if not fragments:
        print("Erreur : Aucune matrice de données valide détectée dans le fichier.")
        return

    # Tri déterministe des segments selon leur index
    fragments.sort(key=lambda x: x[0])
    
    # Vérification de la continuité des fragments
    existing_parts = {item[0] for item in fragments}
    if total_expected_chunks and len(existing_parts) != total_expected_chunks:
        print(f"Segments manquants ! Trouvé {len(existing_parts)} sur {total_expected_chunks} attendus.")
        missing_ids = [i for i in range(1, total_expected_chunks + 1) if i not in existing_parts]
        print(f"Index des parties manquantes : {missing_ids}")
        return

    full_b64_stream = "".join([item[1] for item in fragments])

    try:
        print("Reconstruction des couches binaires à travers l'espace de stockage...")
        compressed_bytes = base64.b64decode(full_b64_stream)
        decompressed_text = zlib.decompress(compressed_bytes).decode(ENCODING)

        # Séparation des fichiers individuels regroupés dans le flux de données
        file_payloads = decompressed_text.split(FILE_DELIMITER)

        output_root_directory.mkdir(exist_ok=True)
        print(f"\nReconstruction de l'espace de travail dans : '{output_root_directory.name}/'")

        for payload in file_payloads:
            if not payload.strip() or not payload.startswith(FILE_HEADER):
                continue

            # Extraction des métadonnées du fichier
            header_line, file_content = payload.split("\n", 1)
            target_relative_path = header_line.replace(FILE_HEADER, "").strip()

            final_file_output_path = output_root_directory / target_relative_path

            # Création automatique des sous-dossiers si nécessaire
            final_file_output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(final_file_output_path, "w", encoding=ENCODING) as out_file:
                out_file.write(file_content)

            print(f"   Fichier restauré : {target_relative_path}")

        print("\n" + "=" * HEADER_WIDTH)
        print("PIPELINE EXTRACTION REUSSIE ! Tous les fichiers ont été déballés.")
        print("=" * HEADER_WIDTH)

    except Exception as e:
        print(f"\nÉchec de la reconstruction : {str(e)}")

if __name__ == "__main__":
    run_global_batch_decoder()