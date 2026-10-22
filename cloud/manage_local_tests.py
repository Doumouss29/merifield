#!/usr/bin/env python3
"""Test the portal in isolation; does not start a fake production cloud."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'overlay'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.settings')
from django.core.management import execute_from_command_line
execute_from_command_line(sys.argv)
