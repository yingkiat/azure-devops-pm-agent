#!/usr/bin/env python3
"""Build the EA portal."""

import sys
from pathlib import Path

# Add parent to path so we can import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from portal.backend.builder import PortalBuilder


if __name__ == "__main__":
    builder = PortalBuilder(
        diagrams_dir="ea_diagrams",
        model_dir="archi_inputs",
        specs_dir="ea_inputs/views",
        output_dir="portal/dist"
    )
    result = builder.build()

    if not result["success"]:
        print(f"\nErrors: {result['errors']}")
        sys.exit(1)
    else:
        print(f"\n✨ Portal ready at: {Path(result['output_path']).absolute()}/index.html")
