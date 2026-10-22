#!/usr/bin/env python3
from pathlib import Path
import sys
import zipfile
root = Path(__file__).resolve().parent
output = Path(sys.argv[1]) if len(sys.argv) > 1 else root / 'Merifield_Cloud_Starter.zip'
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(root.rglob('*')):
        if (path.is_file() and '__pycache__' not in path.parts and
                not any(part.startswith('.') for part in path.relative_to(root).parts) and
                path.suffix not in ('.pyc', '.zip', '.sqlite3')):
            archive.write(path, Path('Merifield_Cloud') / path.relative_to(root))
print(output.resolve())
