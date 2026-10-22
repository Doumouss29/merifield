"""Atomic ZIP creation for a prepared terrain folder (standard library only)."""
# SPDX-License-Identifier: GPL-3.0-or-later
import os
import tempfile
import zipfile
from pathlib import Path

IGNORED = {'.git', '__pycache__', '.DS_Store', 'Thumbs.db'}


def folder_files(folder):
    folder = Path(folder).resolve()
    if not folder.is_dir():
        raise ValueError('Dossier terrain introuvable.')
    files = []
    for directory, dirs, names in os.walk(folder, followlinks=False):
        for name in dirs + names:
            p = Path(directory) / name
            if p.is_symlink():
                raise ValueError('Les liens symboliques ne sont pas pris en charge : ' + str(p))
        dirs[:] = [d for d in dirs if d not in IGNORED]
        for name in names:
            if name in IGNORED or name.endswith(('.qgs~', '.qgz~', '.pyc')):
                continue
            path = Path(directory) / name
            if path.is_file():
                files.append(path)
    if not any(p.suffix.lower() in ('.qgs', '.qgz') for p in files):
        raise ValueError('Le dossier doit contenir un projet QGIS préparé (.qgs ou .qgz).')
    return sorted(files)


def create_zip(folder, destination):
    folder = Path(folder).resolve()
    destination = Path(destination).resolve()
    if destination == folder or folder in destination.parents:
        raise ValueError('Enregistrer le ZIP en dehors du dossier terrain.')
    files = folder_files(folder)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(suffix='.zip', dir=str(destination.parent))
    os.close(fd)
    try:
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
            for path in files:
                archive.write(path, str(Path(folder.name) / path.relative_to(folder)))
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return len(files)
