# qr/ CLAUDE.md

QR code-based secure code transfer system. Encodes source files into QR codes for manual transfer and decodes them back into the original structure.

## Quick Overview

**Main Components:**
- `encoder.py` – Reads files/directories, compresses them, generates HTML with QR codes
- `decoder.py` – Reads scanned QR data and reconstructs original files
- `config.py` – Centralized configuration (constants, encoding settings, delimiters)
- `test.py` – Unit tests

**Key Concept:** Files → compress → chunk → QR codes (HTML) → scan → reconstruct files

## Usage

```bash
# Encode files to QR codes
python encoder.py /path/to/file.py

# Decode scanned QR codes
python decoder.py
```

See **docs/qr.md** for:
- Architecture and flow diagrams
- Configuration reference
- Implementation details
