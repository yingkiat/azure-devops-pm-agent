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
    assert properties["Owner"] == "Product Team"

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
