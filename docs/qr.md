# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a QR code-based secure code transfer system. It allows encoding source files into QR codes for manual transfer and decoding them back into the original file structure.

**Main Components:**
- `encoder.py` – Reads files/directories, compresses them, and generates an HTML page with QR codes
- `decoder.py` – Reads scanned QR data and reconstructs the original files
- `config.py` – Centralized configuration (constants, encoding settings, delimiters, file extensions)

## Architecture

### Encoding Flow
1. **File Collection** – Walks directory tree or reads single file, filtering by `SUPPORTED_EXTENSIONS`
2. **Minification** – Strips unnecessary whitespace to maximize data density
3. **Bundling** – Concatenates files with `FILE_HEADER` and `FILE_DELIMITER` markers
4. **Compression** – zlib compress at `COMPRESSION_LEVEL`, then base64 encode
5. **Chunking** – Splits encoded data into `DEFAULT_CHUNK_SIZE` chunks
6. **QR Generation** – Creates SVG QR code for each chunk with format `[chunk_num/total|data]`
7. **HTML Output** – Generates `scan.html` with all QR codes for scanning

### Decoding Flow
1. **Input Parsing** – Reads `scans_drop.txt` and extracts base64 payloads using `CHUNK_SEPARATOR`
2. **Validation** – Ensures all chunks are present and ordered
3. **Reconstruction** – Concatenates all chunk data, base64 decodes, then zlib decompresses
4. **File Extraction** – Splits by `FILE_DELIMITER`, parses headers, and writes files to `RESTORED_WORKSPACE_DIR`
5. **Directory Restoration** – Recreates original folder structure using relative paths from headers

## Configuration System

All hardcoded values are centralized in `config.py`. Key settings:

- **Encoding:** `ENCODING = "utf-8"`, `COMPRESSION_LEVEL = 9`
- **File Support:** `SUPPORTED_EXTENSIONS` (default: `.py`, `.txt`, `.json`, `.md`, `.sh`, `.bat`)
- **Delimiters:** `FILE_HEADER = "###FILE:"`, `FILE_DELIMITER = "\n###END_OF_FILE###\n"`, `CHUNK_SEPARATOR = "|"`
- **Output:** `OUTPUT_HTML_FILENAME = "scan.html"`, `SCANS_INPUT_FILENAME = "scans_drop.txt"`, `RESTORED_WORKSPACE_DIR = "restored_workspace"`
- **QR:** `DEFAULT_CHUNK_SIZE = 2100`, `QR_ERROR_CORRECTION = "ERROR_CORRECT_L"`

To modify behavior (file types, chunk size, compression), update `config.py` only.

## Usage

### Encoding
```bash
python encoder.py
# Or pass file/directory as argument:
python encoder.py /path/to/file.py
```
Output: `scan.html` with QR codes

### Decoding
```bash
python decoder.py
```
1. First run creates `scans_drop.txt`
2. Paste scanned QR text lines into that file
3. Run again to extract files into `restored_workspace/`

## Key Implementation Details

- **Error Handling in I/O:** `errors="ignore"` suppresses encoding issues when reading diverse text files
- **Minification:** `minimize_source_code()` preserves logical structure (no aggressive minification)
- **Directory Structure:** Relative paths are preserved in headers so folder hierarchies are restored exactly
- **SVG Embedding:** QR codes are embedded as base64 data URIs in HTML (no external dependencies)
- **Fragment Ordering:** Decoder sorts fragments by index to handle out-of-order input

## Refactoring Notes

Previous hardcoding of UTF-8, file extensions, delimiters, and filenames has been consolidated into `config.py`. This eliminates repetition and makes the system maintainable — changing output format or supported file types requires only one edit.
