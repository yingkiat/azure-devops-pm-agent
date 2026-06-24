"""Generate a standalone draw.io diagram of how an application works.

Reads an app-inventory JSON (the application_map node/edge graph) and delegates
rendering to the existing DrawIOGenerator app-inventory diagram type.

CLI:
  python -m portal.backend.app_diagram <app-inventory.json> <out.drawio>
"""

import json
import sys
from pathlib import Path
from typing import List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if SRC_ROOT.exists() and str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ea.drawio_generator import DrawIOGenerator


def build_drawio(inventory: dict) -> str:
    return DrawIOGenerator().generate_app_inventory_drawio(inventory)


def main(argv: Optional[List[str]] = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) < 2:
        print("usage: python -m portal.backend.app_diagram <app-inventory.json> <out.drawio>")
        return 2
    inventory = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    drawio = build_drawio(inventory)
    out = Path(argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(drawio, encoding="utf-8")
    nodes = len(inventory.get("application_map", {}).get("nodes", []))
    edges = len(inventory.get("application_map", {}).get("edges", []))
    print(f"      OK app diagram: {out} ({nodes} nodes, {edges} edges)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
