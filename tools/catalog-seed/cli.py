"""Punto de entrada: python3 -I tools/catalog-seed/cli.py <comando>."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from catalog_seed.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
