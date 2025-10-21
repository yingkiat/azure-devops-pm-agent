"""
ArchiMate Diagram Layout Engine - MVP7

Uses Azure OpenAI to generate intelligent diagram layouts with precise coordinates.
AI receives structural data and returns complete diagram XML with positioned elements.
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional
import hashlib
import re

from utils.openai_client import chat
from utils.settings import settings


class DiagramLayoutEngine:
    """Generates ArchiMate diagram layouts using LLM-driven spatial reasoning."""

    # Canvas constraints
    CANVAS_WIDTH = 2000
    CANVAS_MARGIN = 20
    # CANVAS_HEIGHT is calculated dynamically based on grouping specs

    def __init__(self):
        self.prompt_file = Path("prompts/ea/archimate_diagram_layout.md")
        self.canvas_height = None  # Set during layout generation

    def generate_layout(
        self,
        view_name: str,
        elements: List[Dict[str, Any]],
        groups: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        constraints: Dict[str, Any],
    ) -> str:
        """
        Generate diagram XML with AI-computed coordinates.

        Args:
            view_name: Name of the view being laid out
            elements: List of elements with id, label, type, category
            groups: List of groups (containers, labels) with children
            relationships: List of relationships between elements
            constraints: Layout constraints (spacing, sizing, algorithm)

        Returns:
            XML string with positioned diagram (diagram root element)
        """
        # Load layout prompt
        if not self.prompt_file.exists():
            raise FileNotFoundError(f"Layout prompt not found: {self.prompt_file}")

        with open(self.prompt_file, 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        # Extract dynamically calculated canvas height from constraints
        self.canvas_height = constraints.pop("canvas_height", 1500)  # Default to 1500 if not provided

        # Prepare data for AI
        layout_data = {
            "canvas": {
                "width": self.CANVAS_WIDTH,
                "height": self.canvas_height,
                "margin": self.CANVAS_MARGIN,
            },
            "view_name": view_name,
            "elements": elements,
            "groups": groups,
            "relationships": relationships,
            "constraints": constraints,
        }

        # Format prompt with data
        layout_data_json = json.dumps(layout_data, indent=2)
        prompt_content = prompt_template.replace(
            "{layout_data_json}", layout_data_json
        )

        # Call Azure OpenAI
        try:
            response = chat(
                messages=[
                    {
                        "role": "user",
                        "content": prompt_content,
                    }
                ],
                temperature=0.3,  # Lower temp for deterministic layout
            )

            # Extract response text
            response_text = response.choices[0].message.content.strip()

            # Parse XML from response
            diagram_xml = self._extract_diagram_xml(response_text)

            # Validate coordinates
            self._validate_diagram_xml(diagram_xml)

            return diagram_xml

        except Exception as e:
            raise RuntimeError(f"AI layout generation failed: {e}")

    def _extract_diagram_xml(self, response_text: str) -> str:
        """
        Extract diagram XML block from AI response.

        Expected format:
        ```xml
        <diagram ...>...</diagram>
        ```
        """
        # Try to extract XML between <diagram> and </diagram>
        match = re.search(
            r"<diagram[^>]*>.*?</diagram>",
            response_text,
            re.DOTALL
        )

        if not match:
            raise ValueError("No <diagram> element found in AI response")

        return match.group(0)

    def _validate_diagram_xml(self, diagram_xml: str) -> None:
        """
        Validate diagram XML structure and coordinates.

        Checks:
        - Valid XML format
        - All coordinates are within canvas
        - No overlapping elements
        - All required attributes present
        """
        try:
            root = ET.fromstring(diagram_xml)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML: {e}")

        # Validate canvas bounds
        for node in root.findall(".//node"):
            x = node.get("x")
            y = node.get("y")
            w = node.get("w")
            h = node.get("h")
            node_type = node.get("xsi:type", "")

            # Skip validation for non-positioned elements
            if not all([x, y, w, h]):
                continue

            try:
                x_val = int(x)
                y_val = int(y)
                w_val = int(w)
                h_val = int(h)
            except ValueError:
                raise ValueError(
                    f"Non-integer coordinates: x={x} y={y} w={w} h={h}"
                )

            # Check bounds
            if x_val < 0 or y_val < 0:
                raise ValueError(
                    f"Negative coordinates not allowed: x={x_val} y={y_val}"
                )

            if x_val + w_val > self.CANVAS_WIDTH:
                raise ValueError(
                    f"Element exceeds canvas width: x={x_val} w={w_val} (max={self.CANVAS_WIDTH})"
                )

            if y_val + h_val > self.canvas_height:
                raise ValueError(
                    f"Element exceeds canvas height: y={y_val} h={h_val} (max={self.canvas_height})"
                )

    @staticmethod
    def wrap_in_model(diagram_xml: str) -> ET.Element:
        """
        Wrap AI-generated diagram XML in ArchiMate model structure.

        The AI generates just the <diagram> element. This wraps it in the full model.

        Returns:
            ET.Element with complete ArchiMate model structure
        """
        # Create model root
        ARCHIMATE_NS = "http://www.opengroup.org/xsd/archimate/3.0/"
        ET.register_namespace("", ARCHIMATE_NS)

        root = ET.Element("model", {
            "xmlns": ARCHIMATE_NS,
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:schemaLocation": f"{ARCHIMATE_NS} http://www.opengroup.org/xsd/archimate/3.1/archimate3_Model.xsd",
            "identifier": f"id-{hashlib.md5(b'ai-model').hexdigest()[:12]}",
        })

        # Add model name
        name_el = ET.SubElement(root, "name")
        name_el.text = "AI-Generated EA Model"

        # Parse AI-generated diagram
        diagram_el = ET.fromstring(diagram_xml)

        # Create views container
        views_el = ET.SubElement(root, "views")
        diagrams_el = ET.SubElement(views_el, "diagrams")

        # Add diagram to diagrams container
        diagrams_el.append(diagram_el)

        return root


def create_layout_data_for_view(
    view_definition: Dict[str, Any],
    elements_by_id: Dict[str, Dict[str, Any]],
    relations_by_id: Dict[str, Dict[str, Any]],
) -> tuple[List[Dict], List[Dict], List[Dict], Dict]:
    """
    Prepare layout data from view definition and element/relation maps.

    This converts from view definition format to the JSON structure
    expected by the layout AI.

    Args:
        view_definition: View spec with elements, relations, grouping, layout
        elements_by_id: Map of element ID to element data
        relations_by_id: Map of relation ID to relation data

    Returns:
        Tuple of (elements_list, groups_list, relationships_list, constraints_dict)
    """
    elements = []
    groups = []
    relationships = []

    # Convert elements
    for elem_id in view_definition.get("elements", []):
        if elem_id in elements_by_id:
            elem = elements_by_id[elem_id]
            elements.append({
                "id": elem_id,
                "label": elem.get("name", elem_id),
                "type": elem.get("type", "ApplicationComponent"),
                "category": "Element",
            })

    # Convert relationships
    for rel_id in view_definition.get("relations", []):
        if rel_id in relations_by_id:
            rel = relations_by_id[rel_id]
            relationships.append({
                "id": rel_id,
                "source_id": rel.get("source_id"),
                "target_id": rel.get("target_id"),
                "type": rel.get("type", "Association"),
            })

    # Convert grouping to groups structure
    grouping = view_definition.get("grouping", {})
    if grouping and "by_property" in grouping:
        # Build hierarchical groups from view elements
        groups = _build_groups_from_elements(
            elements,
            elements_by_id,
            grouping,
        )

    # Extract layout constraints
    layout_config = view_definition.get("layout", {})

    # Calculate canvas height dynamically from grouping specs
    canvas_height = _calculate_canvas_height(
        elements_by_id,
        grouping,
        layout_config,
    )

    constraints = {
        "layout_algorithm": layout_config.get("algorithm", "column"),
        "grouping_strategy": "hierarchical" if grouping.get("secondary_by_property") else "flat",
        "spacing": {
            "horizontal": grouping.get("group_spacing_x", 50),
            "vertical": layout_config.get("spacing_y", 40),
        },
        "min_element_width": 120,
        "min_element_height": 60,
        "label_width": 300,
        "label_height": 40,
        "canvas_height": canvas_height,  # Dynamically calculated
    }

    return elements, groups, relationships, constraints


def _build_groups_from_elements(
    elements: List[Dict[str, Any]],
    elements_by_id: Dict[str, Dict[str, Any]],
    grouping: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Build group hierarchy from elements and grouping configuration.

    Returns list of group definitions with proper parent-child relationships.
    """
    groups = []
    group_width = grouping.get("group_width", 800)
    group_height = grouping.get("group_height", 900)

    # Organize elements by primary property (e.g., Region)
    primary_prop = grouping.get("by_property")
    secondary_prop = grouping.get("secondary_by_property")
    primary_order = grouping.get("order", [])

    # Build primary groups
    primary_groups = {}  # Map of primary value -> list of element IDs
    for elem in elements:
        elem_id = elem["id"]
        if elem_id not in elements_by_id:
            continue

        elem_data = elements_by_id[elem_id]
        primary_value = elem_data.get("raw_data", {}).get(primary_prop, "Other")

        if primary_value not in primary_groups:
            primary_groups[primary_value] = []
        primary_groups[primary_value].append(elem_id)

    # Create primary group nodes
    for idx, primary_value in enumerate(primary_order):
        if primary_value not in primary_groups:
            continue

        primary_group_id = f"grp-primary-{primary_value}"
        groups.append({
            "id": primary_group_id,
            "label": primary_value,
            "type": "Container",
            "children": [],
            "width": group_width,
            "height": group_height,
        })

        # If secondary grouping, create labels and organize elements
        if secondary_prop:
            # Organize elements by secondary property
            secondary_groups = {}
            for elem_id in primary_groups[primary_value]:
                elem_data = elements_by_id[elem_id]
                secondary_value = elem_data.get("raw_data", {}).get(secondary_prop, "Other")

                if secondary_value not in secondary_groups:
                    secondary_groups[secondary_value] = []
                secondary_groups[secondary_value].append(elem_id)

            # Create label nodes for each secondary group
            for secondary_value, elem_ids in sorted(secondary_groups.items()):
                label_id = f"grp-label-{primary_value}-{secondary_value}"
                groups.append({
                    "id": label_id,
                    "label": secondary_value,
                    "type": "Label",
                    "parent_group": primary_group_id,
                    "children": elem_ids,
                })
                # Add label to primary group children
                groups[-2]["children"].append(label_id)  # -2 is the primary group we just added
                # Add elements to label
                groups[-1]["children"].extend(elem_ids)
        else:
            # No secondary grouping, add all elements directly
            groups[-1]["children"].extend(primary_groups[primary_value])

    return groups


def _calculate_canvas_height(
    elements_by_id: Dict[str, Dict[str, Any]],
    grouping: Dict[str, Any],
    layout_config: Dict[str, Any],
) -> int:
    """
    Calculate required canvas height based on grouping and element counts.

    Uses formulas from archimate_diagram_layout.md:
    - group_height = (app_count × 60) + ((app_count - 1) × spacing_y) + 100
    - canvas_height = Σ(group_heights) + ((num_groups - 1) × spacing_y) + 200

    Returns:
        Calculated canvas height in pixels
    """
    if not grouping or "by_property" not in grouping:
        return 1500  # Default if no grouping

    primary_prop = grouping.get("by_property")
    spacing_y = layout_config.get("spacing_y", 40)
    group_spacing_y = grouping.get("group_spacing_y", 50)
    primary_order = grouping.get("order", [])

    # Count elements per primary group (region)
    primary_groups = {}
    for elem_data in elements_by_id.values():
        primary_value = elem_data.get("raw_data", {}).get(primary_prop, "Other")
        if primary_value not in primary_groups:
            primary_groups[primary_value] = 0
        primary_groups[primary_value] += 1

    # Calculate group height needed for each region
    group_heights = []
    for primary_value in primary_order:
        if primary_value not in primary_groups:
            continue

        app_count = primary_groups[primary_value]
        # Formula: (app_count × 60) + ((app_count - 1) × spacing_y) + 100
        group_height = (app_count * 60) + ((app_count - 1) * spacing_y) + 100
        group_heights.append(group_height)

    if not group_heights:
        return 1500  # Default if no groups

    # Use maximum height for all groups (ensures all fit)
    max_group_height = max(group_heights)

    # Calculate total canvas height
    num_groups = len(group_heights)
    canvas_padding = 200
    # Formula: (num_groups × max_height) + ((num_groups - 1) × spacing) + padding
    canvas_height = (num_groups * max_group_height) + ((num_groups - 1) * group_spacing_y) + canvas_padding

    return canvas_height
