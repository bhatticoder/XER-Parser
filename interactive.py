#!/usr/bin/env python
"""Interactive XER File Parser

Provides an interactive command-line interface for exploring XER files.

Usage:
    python interactive.py
"""

import sys
from xerparser.src.commands import XerCommand


def main():
    """Start interactive XER parser"""
    cmd = XerCommand()
    cmd.interactive()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
