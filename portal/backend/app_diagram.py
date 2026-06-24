"""Generate a standalone draw.io diagram of how an application works.

Reads an app-inventory JSON (the application_map node/edge graph) and emits a
self-contained .drawio file. This is deliberately SEPARATE from the ArchiMate
strategic model and from the infra 4-layer view - it is the technical-plane
"how the app works" picture.

CLI:
  python -m portal.backend.app_diagram <app-inventory.json> <out.drawio>
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Column placement and styling per node kind (left -> right reading order).
KIND_ORDER = ["frontend", "api", "secret_store", "data_store", "storage", "external", "other"]
KIND_STYLE = {
    "frontend":     "fillColor=#DAE8FC;strokeColor=#6C8EBF",
    "api":          "fillColor=#D5E8D4;strokeColor=#82B366",
    "secret_store": "fillColor=#FFE6CC;strokeColor=#D79B00",
    "data_store":   "fillColor=#F8CECC;strokeColor=#B85450",
    "storage":      "fillColor=#E1D5E7;strokeColor=#9673A6",
    "external":     "fillColor=#F5F5F5;strokeColor=#666666",
    "other":        "fillColor=#FFFFFF;strokeColor=#999999",
}

COL_X = 60
COL_GAP = 320
NODE_W = 220
NODE_H = 90
ROW_GAP = 130
TOP_Y = 120


def _esc(text: str) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _label(parts: List[str]) -> str:
    """Join non-empty lines into a draw.io HTML label (first line bold).

    The value attribute is XML-escaped; draw.io (html=1) unescapes it and renders
    the resulting HTML, so the bold/line-break tags are emitted as entities.
    """
    clean = [p for p in parts if p]
    if not clean:
        return ""
    lines = ["&lt;b&gt;" + _esc(clean[0]) + "&lt;/b&gt;"] + [_esc(p) for p in clean[1:]]
    return "&lt;br&gt;".join(lines)


def _metrics_line(metrics: Optional[dict]) -> str:
    if not metrics:
        return ""
    return " · ".join(f"{k.replace('_', ' ')}: {v}" for k, v in metrics.items())


def build_drawio(inventory: dict) -> str:
    app_map = inventory.get("application_map", {}) or {}
    nodes = app_map.get("nodes", [])
    edges = app_map.get("edges", [])
    title = f"{inventory.get('application', 'Application')} — How the app works " \
            f"({inventory.get('environment', '')})"

    # Bucket nodes into columns by kind, preserving order.
    columns: Dict[str, List[dict]] = {}
    for node in nodes:
        columns.setdefault(node.get("kind", "other"), []).append(node)
    ordered_kinds = [k for k in KIND_ORDER if k in columns] + \
                    [k for k in columns if k not in KIND_ORDER]

    cells: List[str] = []
    pos: Dict[str, tuple] = {}
    for col_idx, kind in enumerate(ordered_kinds):
        x = COL_X + col_idx * COL_GAP
        for row_idx, node in enumerate(columns[kind]):
            y = TOP_Y + row_idx * ROW_GAP
            nid = node["id"]
            pos[nid] = (x, y)
            label = _label([node.get("label", nid), node.get("summary", ""),
                            _metrics_line(node.get("metrics"))])
            style = KIND_STYLE.get(kind, KIND_STYLE["other"])
            cells.append(
                f'<mxCell id="n_{_esc(nid)}" value="{label}" '
                f'style="rounded=1;whiteSpace=wrap;html=1;{style}" vertex="1" parent="1">'
                f'<mxGeometry x="{x}" y="{y}" width="{NODE_W}" height="{NODE_H}" as="geometry"/>'
                f'</mxCell>'
            )

    for i, edge in enumerate(edges):
        src, dst = edge.get("from"), edge.get("to")
        if src not in pos or dst not in pos:
            continue
        parts = [edge.get("label", "")]
        m = _metrics_line(edge.get("metrics"))
        if m:
            parts.append(m)
        label = _label(parts)
        cells.append(
            f'<mxCell id="e_{i}" value="{label}" '
            f'style="endArrow=block;html=1;rounded=1;fontSize=10;'
            f'edgeStyle=orthogonalEdgeStyle" edge="1" parent="1" '
            f'source="n_{_esc(src)}" target="n_{_esc(dst)}">'
            f'<mxGeometry relative="1" as="geometry"/></mxCell>'
        )

    title_cell = (
        f'<mxCell id="title" value="{_esc(title)}" '
        f'style="text;html=1;fontSize=16;fontStyle=1;align=left;verticalAlign=middle" '
        f'vertex="1" parent="1"><mxGeometry x="60" y="40" width="900" height="40" as="geometry"/></mxCell>'
    )

    body = "\n        ".join([title_cell] + cells)
    return (
        '<mxfile host="app.diagrams.net">\n'
        f'  <diagram name="{_esc(inventory.get("project", "app"))} app architecture">\n'
        '    <mxGraphModel dx="900" dy="600" grid="1" gridSize="10" guides="1" '
        'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
        'pageWidth="1600" pageHeight="900" math="0" shadow="0">\n'
        '      <root>\n'
        '        <mxCell id="0"/>\n'
        '        <mxCell id="1" parent="0"/>\n'
        f'        {body}\n'
        '      </root>\n'
        '    </mxGraphModel>\n'
        '  </diagram>\n'
        '</mxfile>\n'
    )


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
