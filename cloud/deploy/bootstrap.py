#!/usr/bin/env python3
"""Fetch a pinned engine and apply the tracked Mérifield overlay.

Does not start services, change DNS, or overwrite an existing installation.
"""
import argparse
import shutil
import subprocess
from pathlib import Path

UPSTREAM_COMMIT = '46f0292db3c7786cbd291f19d2a7ced87db05517'
ROOT = Path(__file__).resolve().parents[1]


def prepare(destination):
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError('Le dossier destination existe déjà : choisir un dossier vide inexistant.')
    subprocess.run(['git', 'clone', '--no-checkout', 'https://github.com/opengisch/QFieldCloud.git', str(destination)], check=True)
    subprocess.run(['git', '-C', str(destination), 'checkout', '--detach', UPSTREAM_COMMIT], check=True)
    subprocess.run(['git', '-C', str(destination), 'submodule', 'update', '--init', '--recursive'], check=True)
    for path in (ROOT / 'overlay').iterdir():
        target = destination / 'docker-app' / path.name
        if path.is_dir():
            shutil.copytree(path, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        else:
            shutil.copy2(path, target)
    shutil.copytree(ROOT / 'deploy', destination / 'merifield-deploy', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copy2(ROOT / 'UPSTREAM_LICENSE', destination / 'MERIFIELD_UPSTREAM_LICENSE')
    print('Sources préparées :', destination)
    print('Prochaine étape : python3 merifield-deploy/configure.py (dans ce dossier).')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    prepare(args.destination)
