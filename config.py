"""Configuration and constants for QR encoder/decoder system."""

# Encoding and compression settings
ENCODING = "utf-8"
COMPRESSION_LEVEL = 9
QR_ERROR_CORRECTION = "ERROR_CORRECT_L"

# File handling
SUPPORTED_EXTENSIONS = {'.py', '.txt', '.json', '.md', '.sh', '.bat'}
ENCODING_ERRORS = "ignore"

# Delimiters and separators
FILE_HEADER = "###FILE:"
FILE_DELIMITER = "\n###END_OF_FILE###\n"
CHUNK_SEPARATOR = "|"
CHUNK_WRAPPER = "[{}]"

# Output files and directories
OUTPUT_HTML_FILENAME = "scan.html"
SCANS_INPUT_FILENAME = "scans_drop.txt"
RESTORED_WORKSPACE_DIR = "restored_workspace"

# QR configuration
DEFAULT_CHUNK_SIZE = 2100
SVG_IMAGE_MIME = "image/svg+xml;base64"

# UI constants
HEADER_WIDTH = 60
BADGE_FORMAT = "Segment {} sur {}"
SCANS_INSTRUCTION = "# Collez toutes les lignes de texte scannées par votre téléphone ici."
