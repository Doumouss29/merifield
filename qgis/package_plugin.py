#!/usr/bin/env python3
"""Build a QGIS-installable ZIP with one top-level package directory."""
from pathlib import Path
import sys
import zipfile

root = Path(__file__).resolve().parent
output = Path(sys.argv[1]) if len(sys.argv) > 1 else root / 'Merifield_Sync_QGIS_0.1.0.zip'
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as z:
    for path in sorted((root / 'merifield_sync').rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
            z.write(path, path.relative_to(root))
    z.write(root / 'README.md', 'merifield_sync/README.md')
print(output.resolve())
