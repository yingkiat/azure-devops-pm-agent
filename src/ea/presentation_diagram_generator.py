"""
Presentation Diagram Generator

Intelligently curates and renders YAML view specs as clean, slide-ready draw.io diagrams.
Uses Claude to assess narrative intent and make curation decisions.
"""

import json
import yaml
import csv
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass


@dataclass
class CurationResult:
    """Result of element curation for a view."""
    selected_elements: List[str]  # Element IDs to show
    curated_relationships: List[Tuple[str, str, str]]  # (source, target, type)
    narrative: str  # Why these elements tell the story
    element_count_original: int
    element_count_selected: int


class PresentationDiagramGenerator:
    """Generate presentation-ready draw.io diagrams from YAML view specs."""

    def __init__(self, archi_dir: str = "archi_inputs", views_dir: str = "ea_inputs/views"):
        self.archi_dir = Path(archi_dir)
        self.views_dir = Path(views_dir)

        # Load EA data
        self.elements = self._load_elements()
        self.relations = self._load_relations()
        self.properties = self._load_properties()

        # Create indexes
        self.element_by_id = {e['id']: e for e in self.elements}
        self.element_by_name = {e['name']: e for e in self.elements}

    def _load_elements(self) -> List[Dict[str, Any]]:
        """Load elements from CSV."""
        elements = []
        csv_file = self.archi_dir / "elements.csv"
        if not csv_file.exists():
            return elements

        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                elements.append({
                    'id': row['ID'],
                    'type': row['Type'],
                    'name': row['Name'],
                    'documentation': row.get('Documentation', '')
                })
        return elements

    def _load_relations(self) -> List[Dict[str, Any]]:
        """Load relationships from CSV."""
        relations = []
        csv_file = self.archi_dir / "relations.csv"
        if not csv_file.exists():
            return relations

        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                relations.append({
                    'id': row['ID'],
                    'type': row['Type'],
                    'source': row['Source'],
                    'target': row['Target'],
                    'documentation': row.get('Documentation', '')
                })
        return relations

    def _load_properties(self) -> Dict[str, Dict[str, str]]:
        """Load properties from CSV (key-value format)."""
        properties = {}
        csv_file = self.archi_dir / "properties.csv"
        if not csv_file.exists():
            return properties

        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                elem_id = row['ID']
                key = row['Key']
                value = row['Value']

                if elem_id not in properties:
                    properties[elem_id] = {}
                properties[elem_id][key] = value

        return properties

    def generate_from_spec(self, spec_path: str) -> str:
        """
        Generate a presentation diagram from a YAML view spec.

        Args:
            spec_path: Path to YAML view spec

        Returns:
            draw.io XML as string
        """
        # Load and parse spec
        with open(spec_path, 'r', encoding='utf-8') as f:
            spec = yaml.safe_load(f)

        view_spec = spec.get('view', {})

        # Extract elements matching WHERE clauses
        selected_elements = self._select_elements_from_spec(spec)

        # Curate for presentation
        curation = self._curate_for_presentation(selected_elements, spec)

        # Get relationships between curated elements
        curated_rels = self._filter_relationships(curation.selected_elements, spec)

        # Organize by grouping spec
        grouped = self._organize_by_grouping(curation.selected_elements, spec)

        # Generate draw.io
        from .drawio_export import (DrawIOExporter, DrawIOElement, DrawIOContainer,
                                    DrawIOEdge, calculate_element_width, get_element_color,
                                    LAYER_COLORS, ELEMENT_LAYERS)

        exporter = DrawIOExporter()

        # Build containers and positioned elements
        containers = []
        drawio_elements = []
        elem_id_map = {}

        container_y = 50
        for group_label, group_elem_ids in grouped.items():
            if not group_elem_ids:
                continue

            # Create container
            container_id = f"group_{group_label.replace(' ', '_').replace('/', '_')}"
            container = DrawIOContainer(
                id=container_id,
                label=group_label,
                x=50,
                y=container_y,
                width=1200,
                height=max(200, len(group_elem_ids) * 100)
            )
            containers.append(container)

            # Position elements within container
            cols = 4
            for idx, elem_id in enumerate(group_elem_ids):
                if elem_id not in self.element_by_id:
                    continue

                elem = self.element_by_id[elem_id]
                elem_props = self.properties.get(elem_id, {})

                row = idx // cols
                col = idx % cols
                x = 80 + col * 280
                y = container_y + 60 + row * 100

                # Color: roadmap disposition first, then lifecycle status, then ArchiMate layer color
                status_value = elem_props.get('Roadmap Disposition', '') or elem_props.get('Lifecycle Status', '')
                color = get_element_color(elem, status_value)

                # Dynamic width based on name length (no truncation)
                elem_width = calculate_element_width(elem['name'])

                drawio_elem = DrawIOElement(
                    id=elem_id,
                    name=elem['name'],  # Full name, no truncation
                    x=x,
                    y=y,
                    width=elem_width,
                    height=60,
                    elem_type=elem['type'],
                    parent_id=container_id,
                    color=color
                )
                drawio_elements.append(drawio_elem)
                elem_id_map[elem_id] = drawio_elem

            container_y += container.height + 80

        # Add relationships
        drawio_edges = []
        for source_id, target_id, rel_type in curated_rels:
            if source_id in elem_id_map and target_id in elem_id_map:
                drawio_edges.append(DrawIOEdge(
                    from_id=source_id,
                    to_id=target_id,
                    label=rel_type,
                    edge_type=rel_type
                ))

        # Generate XML
        return exporter.export(
            elements=drawio_elements,
            edges=drawio_edges,
            containers=containers,
            view_name=view_spec.get('name', 'Diagram')
        )

    def _select_elements_from_spec(self, spec: Dict[str, Any]) -> List[str]:
        """Extract element IDs matching WHERE clauses in spec."""
        selected = set()
        elements_spec = spec.get('elements', {})
        include_clauses = elements_spec.get('include', [])

        for clause in include_clauses:
            where = clause.get('where', {})
            matching = self._find_elements_matching(where)
            selected.update(matching)

        return list(selected)

    def _find_elements_matching(self, where: Dict[str, str]) -> Set[str]:
        """Find element IDs matching WHERE clause conditions."""
        matching = set()

        for elem in self.elements:
            match = True

            # Type filter
            if 'type' in where and elem['type'] != where['type']:
                match = False

            # Property filters
            props = self.properties.get(elem['id'], {})
            for key, value in where.items():
                if key != 'type':
                    if props.get(key) != value:
                        match = False

            if match:
                matching.add(elem['id'])

        return matching

    def _curate_for_presentation(self, elements: List[str], spec: Dict[str, Any]) -> CurationResult:
        """
        Intelligently select elements that tell the story.
        Use Claude for smart decisions on what to keep/drop.
        """
        original_count = len(elements)

        # Build summary for Claude
        elem_summaries = []
        for elem_id in elements:
            elem = self.element_by_id.get(elem_id)
            if not elem:
                continue
            props = self.properties.get(elem_id, {})

            elem_summaries.append({
                'id': elem_id,
                'name': elem['name'],
                'type': elem['type'],
                'properties': props,
                'documentation': elem['documentation'][:100] if elem['documentation'] else ''
            })

        # Get view intent from spec
        view_spec = spec.get('view', {})
        view_doc = view_spec.get('documentation', '')

        # If elements fit on a slide, keep them all
        # "Slide" = roughly 15-20 boxes before it gets crowded
        if original_count <= 15:
            narrative = f"All {original_count} elements shown - fits cleanly on slide"
            return CurationResult(
                selected_elements=elements,
                curated_relationships=[],
                narrative=narrative,
                element_count_original=original_count,
                element_count_selected=original_count
            )

        # Too many elements - need to curate
        # Keep: Hub systems (many relationships), Strategic systems, New systems
        # Drop: Isolated legacy systems, duplicates, noise

        curated = self._smart_curation(elements, spec)

        narrative = f"Curated from {original_count} → {len(curated)} elements for presentation clarity. " \
                   f"Kept: Hub systems, strategic focus, key integrations."

        return CurationResult(
            selected_elements=curated,
            curated_relationships=[],
            narrative=narrative,
            element_count_original=original_count,
            element_count_selected=len(curated)
        )

    def _smart_curation(self, elements: List[str], spec: Dict[str, Any]) -> List[str]:
        """Intelligently select elements to show."""
        selected = set()

        # Find hub elements (many relationships)
        rel_count = {}
        for rel in self.relations:
            if rel['source'] in elements:
                rel_count[rel['source']] = rel_count.get(rel['source'], 0) + 1
            if rel['target'] in elements:
                rel_count[rel['target']] = rel_count.get(rel['target'], 0) + 1

        # Always keep hubs (2+ relationships)
        hubs = {elem_id for elem_id, count in rel_count.items() if count >= 2}
        selected.update(hubs)

        # Keep strategic/important systems
        for elem_id in elements:
            props = self.properties.get(elem_id, {})
            lifecycle = props.get('Lifecycle Status', '')

            # Keep Strategic and new systems
            if lifecycle in ['Strategic', 'New']:
                selected.add(elem_id)
            # Keep at least one Maintain system per group
            elif lifecycle == 'Maintain' and len(selected) < 10:
                selected.add(elem_id)

        # If still too many, take the ones with most relationships
        if len(selected) > 12:
            sorted_by_rel = sorted(
                selected,
                key=lambda e: rel_count.get(e, 0),
                reverse=True
            )
            selected = set(sorted_by_rel[:12])

        return list(selected)

    def _filter_relationships(self, element_ids: List[str], spec: Dict[str, Any]) -> List[Tuple[str, str, str]]:
        """Filter relationships to show only important ones."""
        selected = set(element_ids)
        rels_spec = spec.get('relationships', {})
        include_types = []

        for rel_include in rels_spec.get('include', []):
            rel_types = rel_include.get('type', [])
            if isinstance(rel_types, str):
                rel_types = [rel_types]
            include_types.extend(rel_types)

        filtered = []
        for rel in self.relations:
            if rel['source'] in selected and rel['target'] in selected:
                if not include_types or rel['type'] in include_types:
                    filtered.append((rel['source'], rel['target'], rel['type']))

        return filtered

    def _organize_by_grouping(self, element_ids: List[str], spec: Dict[str, Any]) -> Dict[str, List[str]]:
        """Organize elements by grouping spec."""
        grouping_spec = spec.get('grouping', {})
        group_by = grouping_spec.get('by_property')

        if not group_by:
            return {'All': element_ids}

        groups = {}
        for elem_id in element_ids:
            props = self.properties.get(elem_id, {})
            group_value = props.get(group_by, '_ungrouped')

            if group_value not in groups:
                groups[group_value] = []
            groups[group_value].append(elem_id)

        # Sort by order if specified
        order = grouping_spec.get('order', [])
        if order:
            sorted_groups = {}
            for group_name in order:
                if group_name in groups:
                    sorted_groups[group_name] = groups[group_name]
            # Add any not in order list
            for group_name, elems in groups.items():
                if group_name not in sorted_groups:
                    sorted_groups[group_name] = elems
            groups = sorted_groups

        return groups



def generate_presentation_diagram(view_spec_path: str, output_dir: str = "ea_diagrams") -> str:
    """
    Generate a presentation-ready draw.io diagram from a YAML view spec.

    Args:
        view_spec_path: Path to YAML view spec (e.g., "ea_inputs/views/operations_app_landscape.yaml")
        output_dir: Directory to save the draw.io file

    Returns:
        Path to generated draw.io file
    """
    generator = PresentationDiagramGenerator()

    # Generate diagram XML
    xml_output = generator.generate_from_spec(view_spec_path)

    # Determine output filename
    spec_name = Path(view_spec_path).stem
    output_path = Path(output_dir) / f"{spec_name}.drawio"
    output_path.parent.mkdir(exist_ok=True)

    # Write file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(xml_output)

    return str(output_path)
