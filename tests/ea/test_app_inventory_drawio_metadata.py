import json
import xml.etree.ElementTree as ET

from portal.backend.converter import DrawioToSvg
from src.ea.drawio_generator import DrawIOGenerator


def test_app_inventory_uses_explicit_groups_and_embeds_metadata(tmp_path):
    inventory = {
        "application": "Sample App",
        "environment": "dev",
        "components": [
            {
                "id": "web",
                "name": "Sample Web",
                "type": "react-spa",
                "path": "src/web",
                "dependsOn": ["api"],
                "uses_infra": ["webapp"],
                "summary": "React frontend.",
            }
        ],
        "build_outputs": [
            {
                "component": "web",
                "kind": "container_image",
                "base_image": "nginx:alpine",
                "build_base_image": "node:20-alpine",
            }
        ],
        "application_map": {
            "groups": [
                {"id": "fe", "label": "Frontend", "order": 1},
                {"id": "be", "label": "Backend", "order": 2},
            ],
            "nodes": [
                {
                    "id": "web",
                    "label": "Web UI",
                    "group": "fe",
                    "kind": "frontend",
                    "summary": "User-facing SPA",
                    "metrics": {"routes": 5},
                    "component": "web",
                    "metadata": {"Owner": "Product Team"},
                },
                {
                    "id": "api",
                    "label": "API",
                    "group": "be",
                    "kind": "api",
                    "summary": "Backend API",
                },
            ],
            "edges": [{"from": "web", "to": "api", "label": "HTTPS"}],
        },
    }

    xml = DrawIOGenerator().generate_app_inventory_drawio(inventory)
    root = ET.fromstring(xml)

    group_labels = [cell.get("value") for cell in root.findall(".//mxCell") if "swimlane" in (cell.get("style") or "")]
    assert group_labels == ["Frontend", "Backend"]

    web_cell = root.find(".//mxCell[@id='diagram-web']")
    assert web_cell is not None
    assert web_cell.get("data-name") == "Web UI"

    properties = json.loads(web_cell.get("data-properties"))
    assert properties["Architecture Group"] == "Frontend"
    assert properties["Component Path"] == "src/web"
    assert properties["Build Output 1 Base Image"] == "nginx:alpine"
    assert "Build Output 1 Build Base Image" not in properties
    assert properties["Owner"] == "Product Team"
    assert web_cell.get("value") == "Web UI"

    note_cells = [
        cell
        for cell in root.findall(".//mxCell")
        if "app_node_note" not in (cell.get("id") or "")
        and "fillColor=none;strokeColor=none" in (cell.get("style") or "")
    ]
    assert any(
        cell.get("value") == "User-facing SPA | routes: 5"
        for cell in note_cells
    )

    drawio_path = tmp_path / "sample.drawio"
    svg_path = tmp_path / "sample.svg"
    drawio_path.write_text(xml, encoding="utf-8")

    result = DrawioToSvg().convert(str(drawio_path), str(svg_path))
    assert result["success"]
    web_metadata = next(item for item in result["elements"] if item["id"] == "diagram-web")
    assert web_metadata["name"] == "Web UI"
    assert web_metadata["properties"]["Component Path"] == "src/web"


def test_app_inventory_missing_group_is_not_inferred_from_kind():
    inventory = {
        "application_map": {
            "groups": [{"id": "declared", "label": "Declared Group", "order": 1}],
            "nodes": [{"id": "api", "label": "API", "kind": "api"}],
            "edges": [],
        }
    }

    xml = DrawIOGenerator().generate_app_inventory_drawio(inventory)
    root = ET.fromstring(xml)

    group_labels = [cell.get("value") for cell in root.findall(".//mxCell") if "swimlane" in (cell.get("style") or "")]
    assert group_labels == ["ungrouped"]


def test_app_inventory_stacks_non_primary_groups_in_service_side_column():
    inventory = {
        "application_map": {
            "nodes": [
                {"id": "web", "label": "Web", "group": "frontend"},
                {"id": "api", "label": "API", "group": "backend"},
                {"id": "kv", "label": "Key Vault", "group": "security"},
                {"id": "db", "label": "Database", "group": "data"},
                {"id": "storage", "label": "Storage", "group": "storage"},
            ],
            "edges": [],
        }
    }

    xml = DrawIOGenerator().generate_app_inventory_drawio(inventory)
    root = ET.fromstring(xml)
    containers = {
        cell.get("value"): cell.find("mxGeometry")
        for cell in root.findall(".//mxCell")
        if "swimlane" in (cell.get("style") or "")
    }

    assert containers["frontend"].get("x") == "60"
    assert containers["backend"].get("x") == "435"

    service_x = containers["security"].get("x")
    assert service_x == "810"
    assert containers["data"].get("x") == service_x
    assert containers["storage"].get("x") == service_x
    assert int(containers["security"].get("y")) < int(containers["data"].get("y")) < int(containers["storage"].get("y"))


def test_app_inventory_edge_labels_are_placed_near_targets():
    inventory = {
        "application_map": {
            "nodes": [
                {"id": "api", "label": "API", "group": "backend"},
                {"id": "kv", "label": "Key Vault", "group": "security"},
                {"id": "db", "label": "Database", "group": "data"},
            ],
            "edges": [
                {"from": "api", "to": "kv", "label": "Reads secrets"},
                {"from": "api", "to": "db", "label": "SQL data access"},
            ],
        }
    }

    xml = DrawIOGenerator().generate_app_inventory_drawio(inventory)
    root = ET.fromstring(xml)
    cells = root.findall(".//mxCell")
    cell_by_id = {cell.get("id"): cell for cell in cells}
    api_cell = root.find(".//mxCell[@id='diagram-api']")
    kv_cell = root.find(".//mxCell[@id='diagram-kv']")
    assert api_cell is not None
    assert kv_cell is not None

    def absolute_x(cell):
        geometry = cell.find("mxGeometry")
        parent = cell_by_id.get(cell.get("parent"))
        parent_geometry = parent.find("mxGeometry") if parent is not None else None
        parent_x = int(parent_geometry.get("x")) if parent_geometry is not None else 0
        return parent_x + int(geometry.get("x"))

    api_right = absolute_x(api_cell) + int(api_cell.find("mxGeometry").get("width"))
    kv_left = absolute_x(kv_cell)
    labels = {
        cell.get("value"): cell.find("mxGeometry")
        for cell in cells
        if "fontStyle=1;fillColor=none;strokeColor=none" in (cell.get("style") or "")
    }

    reads_label_x = int(labels["Reads secrets"].get("x"))
    assert api_right < reads_label_x < kv_left
