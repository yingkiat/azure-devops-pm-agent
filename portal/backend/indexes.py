"""Generate JSON indexes for interactive portal."""

import json
import csv
from pathlib import Path
from typing import Dict, List
from collections import defaultdict


def _mask_it_owner(value: str) -> str:
    if not value:
        return value
    if "." in value:
        first, _ = value.split(".", 1)
        return first[:3] + "*.***"
    return value[:3] + "***"


def _mask_properties(props: dict) -> dict:
    return {k: _mask_it_owner(v) if k == "It Owner" else v for k, v in props.items()}


class PortalIndexGenerator:
    """Generate element index, relationship graph, and view registry."""

    def __init__(self):
        self.elements = {}
        self.relations = {}
        self.properties = {}

    def load_archi_model(self, model_dir: str) -> bool:
        """Load ArchiMate model from CSV files (both core and diagram-specific)."""
        try:
            model_path = Path(model_dir)

            # Load both core elements and diagram-specific concepts
            element_files = [
                model_path / "elements.csv",
                model_path / "diagram_elements.csv"
            ]
            property_files = [
                model_path / "properties.csv",
                model_path / "diagram_properties.csv"
            ]
            relation_files = [
                model_path / "relations.csv",
                model_path / "diagram_relationships.csv"
            ]

            # Load all elements (core + diagram-specific)
            for elem_file in element_files:
                if elem_file.exists():
                    with open(elem_file, encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            elem_id = row.get("ID")
                            if elem_id:
                                self.elements[elem_id] = {
                                    "id": elem_id,
                                    "type": row.get("Type", ""),
                                    "name": row.get("Name", ""),
                                    "documentation": row.get("Documentation", ""),
                                }

            # Load all properties (core + diagram-specific)
            # Properties CSV format: ID,Key,Value (each row is one property)
            for prop_file in property_files:
                if prop_file.exists():
                    with open(prop_file, encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            elem_id = row.get("ID")
                            prop_key = row.get("Key")
                            prop_value = row.get("Value")
                            if elem_id and prop_key and prop_value:
                                if elem_id not in self.properties:
                                    self.properties[elem_id] = {}
                                self.properties[elem_id][prop_key] = prop_value

            # Load all relations (core + diagram-specific)
            for rel_file in relation_files:
                if rel_file.exists():
                    with open(rel_file, encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            source = row.get("Source")
                            target = row.get("Target")
                            rel_type = row.get("Type", "")
                            if source and target:
                                if source not in self.relations:
                                    self.relations[source] = []
                                self.relations[source].append(
                                    {"target": target, "type": rel_type}
                                )

            return True
        except Exception as e:
            print(f"Error loading ArchiMate model: {e}")
            return False

    def generate_element_index(self, diagram_data: Dict) -> Dict:
        """Generate element index with appearances in views (deduplicated)."""
        appearances = defaultdict(dict)  # Use dict to auto-deduplicate by view_id
        referenced_elements = set()  # Track all elements referenced in views

        for view in diagram_data.get("views", []):
            view_id = view.get("view_id")
            view_name = view.get("name", view_id)
            for elem_id in view.get("elements", []):
                referenced_elements.add(elem_id)
                # Track appearance regardless of whether element exists in self.elements
                appearances[elem_id][view_id] = {
                    "view_id": view_id,
                    "view_name": view_name,
                    "context": view.get("context", ""),
                }

        # Convert dict values back to list
        appearances_list = defaultdict(list)
        for elem_id, view_dict in appearances.items():
            appearances_list[elem_id] = list(view_dict.values())

        index = {}

        # Add all ArchiMate model elements
        for elem_id, elem_data in self.elements.items():
            index[elem_id] = {
                "id": elem_id,
                "name": elem_data["name"],
                "type": elem_data["type"],
                "properties": _mask_properties(self.properties.get(elem_id, {})),
                "appears_in": appearances_list.get(elem_id, []),
                "documentation": elem_data.get("documentation", ""),
            }

        # Add stub entries for diagram elements not in ArchiMate model
        # These are elements generated during diagram creation (diagram-specific or manual)
        for elem_id in referenced_elements:
            if elem_id not in index:
                # Create stub entry for diagram-only element
                index[elem_id] = {
                    "id": elem_id,
                    "name": f"Diagram Element {elem_id}",
                    "type": "DiagramComponent",
                    "properties": _mask_properties(self.properties.get(elem_id, {})),
                    "appears_in": appearances_list.get(elem_id, []),
                    "documentation": "Diagram-specific element",
                }

        return index

    def generate_relationship_graph(self, element_index: Dict = None) -> Dict:
        """Generate relationship graph for element navigation."""
        inbound = defaultdict(list)
        for source, targets in self.relations.items():
            for rel in targets:
                target = rel["target"]
                inbound[target].append(
                    {
                        "source_id": source,
                        "source_name": self.elements.get(source, {}).get("name", ""),
                        "type": rel["type"],
                    }
                )

        graph = {}

        # Create graph entries for all ArchiMate model elements
        for elem_id in self.elements:
            graph[elem_id] = {
                "outbound": [
                    {
                        "target_id": rel["target"],
                        "target_name": self.elements.get(rel["target"], {}).get(
                            "name", ""
                        ),
                        "type": rel["type"],
                    }
                    for rel in self.relations.get(elem_id, [])
                ],
                "inbound": inbound.get(elem_id, []),
            }

        # Create empty graph entries for diagram-only elements
        if element_index:
            for elem_id in element_index:
                if elem_id not in graph:
                    graph[elem_id] = {
                        "outbound": [],
                        "inbound": [],
                    }

        return graph

    def generate_view_registry(self, diagrams_info: List[Dict]) -> Dict:
        """Generate view registry from diagram info."""
        registry = {}
        for diag in diagrams_info:
            view_id = diag["view_id"]
            registry[view_id] = {
                "id": view_id,
                "name": diag.get("name", view_id),
                "diagram_path": diag["diagram_file"],
                "preview_path": diag.get("preview_file", diag["diagram_file"]),
                "category": diag.get("category", ""),
                "domain": diag.get("domain", ""),
                "region": diag.get("region", ""),
                "project": diag.get("project", ""),
                "project_key": diag.get("project_key", ""),
                "view_kind": diag.get("view_kind", ""),
                "view_type": diag.get("view_type", "diagram"),
                "iframe_src": diag.get("iframe_src", ""),
                "elements": diag.get("elements", []),
                "metadata": {
                    "element_count": len(diag.get("elements", [])),
                    "created": diag.get("created", ""),
                    "updated_at": diag.get("updated_at", ""),
                    "domain": diag.get("domain", ""),
                    "region": diag.get("region", ""),
                    "project": diag.get("project", ""),
                    "project_key": diag.get("project_key", ""),
                    "view_kind": diag.get("view_kind", ""),
                },
            }
        return registry

    def save_indexes(
        self, output_dir: str, element_index: Dict, relationship_graph: Dict, view_registry: Dict
    ) -> bool:
        """Save generated indexes to JSON files."""
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)

            with open(
                Path(output_dir) / "element_index.json", "w", encoding="utf-8"
            ) as f:
                json.dump(element_index, f, indent=2)

            with open(
                Path(output_dir) / "relationship_graph.json", "w", encoding="utf-8"
            ) as f:
                json.dump(relationship_graph, f, indent=2)

            with open(
                Path(output_dir) / "view_registry.json", "w", encoding="utf-8"
            ) as f:
                json.dump(view_registry, f, indent=2)

            return True
        except Exception as e:
            print(f"Error saving indexes: {e}")
            return False
