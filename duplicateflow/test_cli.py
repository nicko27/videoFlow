#!/usr/bin/env python3
"""Test CLI without installation."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from duplicateflow.cli.main import cli

if __name__ == '__main__':
    cli()
