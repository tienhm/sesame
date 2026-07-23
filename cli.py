#!/usr/bin/env python3
"""Sesame CLI - Entry point.

Usage:
    python cli.py get tag1 tag2
    python cli.py list -c Work
    python cli.py add -n Gmail -u user@gmail.com
"""

from __future__ import annotations

import os
import sys

# Make sure the project root is on sys.path
sys.path.insert(0, os.path.dirname(__file__))

from app.cli.commands import cli

if __name__ == "__main__":
    cli()
