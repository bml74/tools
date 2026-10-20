import os
import sys
import zlib
import base64
import math
import qrcode
import qrcode.image.svg
from pathlib import Path
from config import (
    ENCODING, COMPRESSION_LEVEL, QR_ERROR_CORRECTION, SUPPORTED_EXTENSIONS,
    ENCODING_ERRORS, FILE_HEADER, FILE_DELIMITER, CHUNK_SEPARATOR, CHUNK_WRAPPER,
    OUTPUT_HTML_FILENAME, DEFAULT_CHUNK_SIZE, SVG_IMAGE_MIME, HEADER_WIDTH, BADGE_FORMAT
)

def minimize_source_code(code_text: str) -> str:
    """
    Supprime les espaces inutiles, les fins de ligne et les lignes vides
    pour maximiser la densité des données avant la compression.
    """
    clean_lines = []
    for line in code_text.splitlines():
        stripped = line.rstrip()
        if stripped.strip():
            clean_lines.append(stripped)
    return "\n".join(clean_lines)

def run_global_encoder(target_path: Path, chunk_size: int = DEFAULT_CHUNK_SIZE):
    payload_manifest = []

    # Cas A : Si la cible est un fichier unique
    if target_path.is_file():
        if target_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            with open(target_path, "r", encoding=ENCODING, errors=ENCODING_ERRORS) as f:
                raw = f.read()
            minified = minimize_source_code(raw)
            payload_manifest.append(f"{FILE_HEADER}{target_path.name}\n{minified}")

    # Cas B : Si la cible est un dossier complet
    elif target_path.is_dir():
        print(f"Analyse de l'arborescence du dossier : {target_path}")
        for file_ref in target_path.rglob('*'):
            if file_ref.is_file() and file_ref.suffix.lower() in SUPPORTED_EXTENSIONS:
                relative_name = file_ref.relative_to(target_path)
                with open(file_ref, "r", encoding=ENCODING, errors=ENCODING_ERRORS) as f:
                    raw = f.read()
                minified = minimize_source_code(raw)
                payload_manifest.append(f"{FILE_HEADER}{relative_name}\n{minified}")
    
    else:
        print(f"Erreur : Le chemin d'accès spécifié '{target_path}' est invalide.")
        return

    if not payload_manifest:
        print("Erreur : Aucun fichier de script transférable détecté.")
        return

    # Fusion de tous les fichiers avec des délimiteurs structurels
    combined_raw_data = FILE_DELIMITER.join(payload_manifest)

    # Compression et encodage en Base64
    compressed = zlib.compress(combined_raw_data.encode(ENCODING), level=COMPRESSION_LEVEL)
    b64_string = base64.b64encode(compressed).decode(ENCODING)
    total_chunks = math.ceil(len(b64_string) / chunk_size)

    # Structure du document HTML généré (Interface en Français)
    html_content = """
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body { font-family: sans-serif; text-align: center; background: #f4f6f9; padding: 20px; color: #333; }
            .container { max-width: 600px; margin: 0 auto; }
            .chunk-card { background: white; padding: 25px; margin: 25px auto; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
            img { width: 400px; height: 400px; margin: 15px 0; border: 1px solid #eee; }
            .badge { background: #007bff; color: white; padding: 4px 10px; border-radius: 20px; font-size: 14px; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Portail de Transfert de Code Sécurisé</h2>
            <p>Scannez les matrices visuelles suivantes dans l'ordre avec votre application mobile.</p>
    """

    for idx in range(total_chunks):
        start = idx * chunk_size
        end = start + chunk_size
        chunk_data = b64_string[start:end]
        formatted_payload = CHUNK_WRAPPER.format(f"{idx+1}/{total_chunks}{CHUNK_SEPARATOR}{chunk_data}")

        qr = qrcode.QRCode(version=None, error_correction=getattr(qrcode.constants, QR_ERROR_CORRECTION))
        qr.add_data(formatted_payload)
        qr.make(fit=True)

        svg_img = qr.make_image(image_factory=qrcode.image.svg.SvgPathImage)
        svg_bytes = svg_img.to_string()
        svg_b64 = base64.b64encode(svg_bytes).decode(ENCODING)
        
        html_content += f"""
        <div class="chunk-card">
            <h3><span class="badge">{BADGE_FORMAT.format(idx+1, total_chunks)}</span></h3>
            <img src="data:{SVG_IMAGE_MIME},{svg_b64}" />
            <p style="color: #777; font-size: 11px;">Taille du segment : {len(formatted_payload)} caractères</p>
        </div>
        """

    html_content += "</div></body></html>"

    output_html_path = Path.cwd() / OUTPUT_HTML_FILENAME
    with open(output_html_path, "w", encoding=ENCODING) as f:
        f.write(html_content)

    print("\n" + "=" * HEADER_WIDTH)
    print(f"EXPORTATION DU PIPELINE REUSSIE !")
    print(f"Cible traitée : {target_path.resolve()}")
    print(f"Double-cliquez pour ouvrir : '{output_html_path.name}'")
    print("=" * HEADER_WIDTH)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_path_string = sys.argv[1]
    else:
        input_path_string = input("Glissez-déposez un FICHIER/DOSSIER ici, puis appuyez sur [ENTRÉE] : ").strip()
        
    clean_path_string = input_path_string.strip("'\"")
    run_global_encoder(Path(clean_path_string))