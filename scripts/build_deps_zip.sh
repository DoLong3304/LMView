#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# build_deps_zip.sh — Build deps.zip for PyFlink job submission
# ─────────────────────────────────────────────────────────────────────────────
# Creates /tmp/deps.zip with:
#   - common/          (shared modules: config, kafka_client, etc.)
#   - writers/         (flattened from processing/writers/ — PyFlink import path)
#
# Usage:
#   bash scripts/build_deps_zip.sh
#
# Must be run from the project root with /app/src as working directory
# (inside a container that has /app/src mapped).
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SRC_DIR="${SRC_DIR:-/app/src}"
OUTPUT_ZIP="${OUTPUT_ZIP:-/tmp/deps.zip}"

echo "[build_deps_zip] Building ${OUTPUT_ZIP} from ${SRC_DIR}..."

python3 -c "
import zipfile
import os

src = '${SRC_DIR}'
output = '${OUTPUT_ZIP}'

# Change to src directory for proper relative paths
orig_cwd = os.getcwd()
os.chdir(src)

with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zf:
    # Add common module with proper structure
    for root, dirs, files in os.walk('common'):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                zf.write(filepath, filepath)

    # Add processing/writers module — flatten to writers/ for PyFlink imports
    writers_init = 'processing/writers/__init__.py'
    if os.path.exists(writers_init):
        zf.write(writers_init, 'writers/__init__.py')
    else:
        zf.writestr('writers/__init__.py', '')

    for root, dirs, files in os.walk('processing/writers'):
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                filepath = os.path.join(root, file)
                # Write as writers/filename.py (flatten structure)
                zf.write(filepath, 'writers/' + file)

    print(f'Created {output} with:')
    for zi in zf.infolist():
        print(f'  {zi.filename} ({zi.compress_size}B -> {zi.file_size}B)')

os.chdir(orig_cwd)
"
echo "[build_deps_zip] Done: ${OUTPUT_ZIP}"
