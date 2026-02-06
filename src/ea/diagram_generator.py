"""
Unified Diagram Generator (MVP8 + MVP9)

Generates diagrams from YAML view specs with AI-driven layout.
Supports both ArchiMate XML (for Archi tool) and draw.io XML output.

Key features (MVP8):
- Reads extended YAML spec (presentation, output sections)
- Applies ArchiMate layer colors
- Uses AI for intelligent layout
- Outputs to Archi XML, draw.io, or both

MVP9 additions:
- intent: question, audience, decision, key_message - passed to AI for context
- story: setup, tension, insight - enhances AI layout decisions
- visual: emphasis treatments (prominent/faded/highlighted/normal) applied to elements
- iterations: version history preserved in output metadata
"""

import json
import yaml
import csv
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import hashlib

from utils.openai_client import chat

from .drawio_export import (
    DrawIOExporter, DrawIOElement, DrawIOContainer, DrawIOEdge,
    get_element_color, calculate_element_width, get_relationship_style,
    LAYER_COLORS, ELEMENT_LAYERS, LIFECYCLE_COLORS
)
from .archi_layouts import MatrixLayout


class DiagramGenerator:
    """
    Unified diagram generator with AI-driven layout.

    Reads YAML view specs and generates diagrams in requested formats.
    """

    CANVAS_WIDTH = 2000
    CANVAS_HEIGHT = 1500
    CANVAS_MARGIN = 50

    def __init__(self, archi_dir: str = "archi_inputs", views_dir: str = "ea_inputs/views"):
        self.archi_dir = Path(archi_dir)
        self.views_dir = Path(views_dir)
        self.drawio_prompt_file = Path("prompts/ea/drawio_diagram_layout.md")
        self.archi_prompt_file = Path("prompts/ea/archimate_diagram_layout.md")

        # Load EA data
        self.elements = self._load_elements()
        self.relations = self._load_relations()
        self.properties = self._load_properties()

        # Create indexes
        self.element_by_id = {e['id']: e for e in self.elements}
        self.properties_by_elem = self._index_properties()

    def _load_elements(self) -> List[Dict[str, Any]]:
        """Load elements from CSV (discovered + diagram-specific)."""
        elements = []

        # Load discovered elements
        csv_file = self.archi_dir / "elements.csv"
        if csv_file.exists():
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    elements.append({
                        'id': row['ID'],
                        'type': row['Type'],
                        'name': row['Name'],
                        'documentation': row.get('Documentation', '')
                    })

        # Load diagram-specific elements
        diagram_csv_file = self.archi_dir / "diagram_elements.csv"
        if diagram_csv_file.exists():
            with open(diagram_csv_file, 'r', encoding='utf-8') as f:
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
        """Load relationships from CSV (discovered + diagram-specific)."""
        relations = []

        # Load discovered relationships
        csv_file = self.archi_dir / "relations.csv"
        if csv_file.exists():
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

        # Load diagram-specific relationships
        diagram_csv_file = self.archi_dir / "diagram_relationships.csv"
        if diagram_csv_file.exists():
            with open(diagram_csv_file, 'r', encoding='utf-8') as f:
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

    def _load_properties(self) -> List[Dict[str, Any]]:
        """Load properties from CSV (discovered + diagram-specific)."""
        properties = []

        # Load discovered properties
        csv_file = self.archi_dir / "properties.csv"
        if csv_file.exists():
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    properties.append({
                        'element_id': row['ID'],
                        'key': row['Key'],
                        'value': row['Value']
                    })

        # Load diagram-specific properties
        diagram_csv_file = self.archi_dir / "diagram_properties.csv"
        if diagram_csv_file.exists():
            with open(diagram_csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    properties.append({
                        'element_id': row['ID'],
                        'key': row['Key'],
                        'value': row['Value']
                    })

        return properties

        return properties

    def _index_properties(self) -> Dict[str, Dict[str, str]]:
        """Index properties by element ID."""
        props_by_elem = {}
        for prop in self.properties:
            elem_id = prop['element_id']
            if elem_id not in props_by_elem:
                props_by_elem[elem_id] = {}
            props_by_elem[elem_id][prop['key']] = prop['value']
        return props_by_elem

    def _check_data_quality(self, elements_config: Dict[str, Any],
                            grouping_config: Dict[str, Any]) -> List[str]:
        """
        Check data quality before diagram generation.

        Analyzes property coverage for WHERE clause filters and grouping properties.
        Returns list of warning messages.
        """
        warnings = []

        # Extract WHERE clause properties
        where_properties = set()
        target_type = None

        include_rules = elements_config.get('include', [])
        if not include_rules and 'where' in elements_config:
            include_rules = [{'where': elements_config['where']}]

        for rule in include_rules:
            where = rule.get('where', {})
            if 'type' in where:
                target_type = where['type']
                if isinstance(target_type, list):
                    target_type = target_type[0]  # Use first type for analysis
            for key in where.keys():
                if key != 'type':
                    where_properties.add(key)

        # Add grouping properties
        if grouping_config:
            if 'by_property' in grouping_config:
                where_properties.add(grouping_config['by_property'])
            if 'secondary_by_property' in grouping_config:
                where_properties.add(grouping_config['secondary_by_property'])

        # Analyze property coverage for target element type
        if target_type and where_properties:
            candidates = [e for e in self.elements if e['type'] == target_type]
            total_candidates = len(candidates)

            if total_candidates == 0:
                warnings.append(f"No elements of type '{target_type}' found in data")
            else:
                for prop in where_properties:
                    # Count elements with this property
                    with_prop = 0
                    prop_values = {}
                    for elem in candidates:
                        elem_props = self.properties_by_elem.get(elem['id'], {})
                        if prop in elem_props:
                            with_prop += 1
                            val = elem_props[prop]
                            prop_values[val] = prop_values.get(val, 0) + 1

                    missing = total_candidates - with_prop
                    coverage_pct = (with_prop / total_candidates) * 100

                    if missing > 0:
                        warnings.append(
                            f"Property '{prop}': {missing}/{total_candidates} {target_type}s "
                            f"({100-coverage_pct:.0f}%) missing this property"
                        )

                        # Show available values for context
                        if prop_values:
                            top_values = sorted(prop_values.items(), key=lambda x: -x[1])[:5]
                            val_str = ', '.join([f"{v}({c})" for v, c in top_values])
                            warnings.append(f"  Available '{prop}' values: {val_str}")

        return warnings

    def generate(self, spec_path: str) -> Dict[str, Any]:
        """
        Generate diagram from YAML spec.

        Args:
            spec_path: Path to YAML view spec

        Returns:
            Dict with:
            - 'drawio': draw.io XML string (if requested)
            - 'archi': ArchiMate XML string (if requested)
            - 'output_files': list of generated file paths
            - 'element_count': number of elements in diagram
            - 'warnings': list of data quality warnings (if any)
        """
        # Load spec
        spec = self._load_spec(spec_path)
        if not spec:
            return {'error': f'Failed to load spec: {spec_path}'}

        # Check if this is a freeform diagram
        is_freeform = spec.get('type') == 'freeform'

        # Extract configuration
        view_config = spec.get('view', {})
        view_name = view_config.get('name', 'Diagram')

        elements_config = spec.get('elements', {})
        grouping_config = spec.get('grouping', {})
        layout_config = spec.get('layout', {})
        presentation_config = spec.get('presentation', {})
        output_config = spec.get('output', {'format': 'drawio'})
        structure_config = spec.get('structure', {})
        annotations_config = spec.get('annotations', [])

        # MVP9: Intent-driven sections
        intent_config = spec.get('intent', {})
        story_config = spec.get('story', {})
        visual_config = spec.get('visual', {})
        iterations_config = spec.get('iterations', [])

        # Run data quality check before selection
        warnings = self._check_data_quality(elements_config, grouping_config)

        # Select elements (may be extended by structure config)
        selected_elements = self._select_elements(elements_config)

        # If structure config exists, build hierarchy and extend element selection
        structure_hierarchy = None
        if structure_config:
            structure_hierarchy, additional_elements = self._build_structure_hierarchy(
                selected_elements, structure_config
            )
            # Add child elements discovered via relationships
            for elem in additional_elements:
                if elem not in selected_elements:
                    selected_elements.append(elem)

        if not selected_elements:
            return {'error': 'No elements selected by spec'}

        # Filter relationships and create diagram-specific ones if needed
        relationships_config = spec.get('relationships', {})
        selected_relations = self._filter_relations(selected_elements, relationships_config)

        # Create diagram relationships from YAML spec (for freeform diagrams)
        if is_freeform and relationships_config:
            diagram_relations = self._create_diagram_relationships(
                selected_elements, relationships_config
            )
            selected_relations.extend(diagram_relations)

        # Enrich elements with presentation data and MVP9 visual emphasis
        enriched_elements = self._enrich_elements(selected_elements, presentation_config, visual_config)

        # MVP9: Write enriched elements to diagram_elements.csv for portal builder
        self._write_diagram_elements(enriched_elements)

        # Determine output format
        output_format = output_config.get('format', 'drawio')

        result = {
            'view_name': view_name,
            'element_count': len(selected_elements),
            'relationship_count': len(selected_relations),
            'output_files': [],
            'warnings': warnings
        }

        # Print warnings for visibility
        if warnings:
            print("\n[DATA QUALITY WARNINGS]")
            for w in warnings:
                print(f"  - {w}")

        # Generate requested format(s)
        if output_format in ['drawio', 'both']:
            # Pass grouping_spec to AI - let AI handle grouping logic
            # MVP9: Also pass intent/story for AI context
            drawio_xml = self._generate_drawio(
                view_name, enriched_elements, selected_relations,
                layout_config, presentation_config, grouping_config,
                structure_hierarchy, annotations_config,
                intent_config, story_config
            )
            result['drawio'] = drawio_xml

            # Write to file
            output_path = self._write_output(spec_path, drawio_xml, 'drawio')
            result['output_files'].append(str(output_path))

        if output_format in ['archi', 'both']:
            archi_xml = self._generate_archi(
                view_name, enriched_elements, groups, selected_relations,
                layout_config, presentation_config
            )
            result['archi'] = archi_xml

            # Write to file
            output_path = self._write_output(spec_path, archi_xml, 'xml')
            result['output_files'].append(str(output_path))

        return result

    def _load_spec(self, spec_path: str) -> Optional[Dict[str, Any]]:
        """Load YAML spec file."""
        try:
            with open(spec_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading spec: {e}")
            return None

    def _select_elements(self, elements_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Select elements based on WHERE clauses or inline definitions.

        MVP9 Data Stocktake Workflow:
        - Try to find elements in combined data store (elements.csv + diagram_elements.csv)
        - For missing elements, create synthetic diagram elements with auto-generated IDs
        - Generate data stocktake report showing official vs diagram-only elements
        - Persist new diagram elements to diagram_elements.csv and diagram_properties.csv
        """
        selected = []
        include_rules = elements_config.get('include', [])
        official_elements = []  # Track which came from elements.csv
        diagram_only_elements = []  # Track which were created as diagram elements

        # If no include rules, check for direct 'where' clause
        if not include_rules and 'where' in elements_config:
            include_rules = [{'where': elements_config['where']}]

        for rule in include_rules:
            # Check if this is an inline element definition (has 'name' field)
            if 'name' in rule:
                # Try to find by name in the combined data store
                elem_name = rule['name']
                matched = False

                # Try to find in existing elements (elements.csv + diagram_elements.csv)
                for elem in self.elements:
                    if elem['name'] == elem_name:
                        # Found in data store - use it with any overrides applied
                        if elem not in selected:
                            # Apply property overrides from YAML
                            if 'override' in rule:
                                if elem['id'] not in self.properties_by_elem:
                                    self.properties_by_elem[elem['id']] = {}
                                self.properties_by_elem[elem['id']].update(rule['override'])
                            selected.append(elem)
                            official_elements.append(elem_name)
                        matched = True
                        break

                # If not found, create synthetic diagram element
                if not matched:
                    synthetic_elem = self._create_synthetic_diagram_element(elem_name, rule)
                    if synthetic_elem:
                        selected.append(synthetic_elem)
                        diagram_only_elements.append(elem_name)

            else:
                # WHERE clause - match from existing elements
                where = rule.get('where', {})
                for elem in self.elements:
                    if self._element_matches(elem, where):
                        if elem not in selected:
                            selected.append(elem)
                            official_elements.append(elem['name'])

        # Generate and print data stocktake report
        self._print_data_stocktake(len(include_rules), official_elements, diagram_only_elements)

        # Persist diagram elements to CSV
        if diagram_only_elements:
            self._persist_diagram_elements(selected, official_elements)

        return selected

    def _create_synthetic_diagram_element(self, elem_name: str, rule: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a diagram-only synthetic element for elements referenced in YAML but not in database.

        MVP9: Automatically creates diagram elements when specs reference non-existent elements.

        Args:
            elem_name: Element name from YAML spec
            rule: YAML rule containing optional 'override' properties and 'type' hint

        Returns:
            Synthetic element dict with auto-generated deterministic ID
        """
        # Generate deterministic ID from name (same element always gets same ID)
        elem_id = f"diagram-{hashlib.md5(elem_name.encode()).hexdigest()[:12]}"

        # Infer type - use provided type or default to ApplicationComponent
        elem_type = rule.get('type', 'ApplicationComponent')

        # Create synthetic element
        synthetic_elem = {
            'id': elem_id,
            'type': elem_type,
            'name': elem_name,
            'documentation': f"Diagram element for {elem_name} (not in official EA model)"
        }

        # Extract properties from YAML override (if present)
        override_props = rule.get('override', {})

        # Add to internal lookups so it can be referenced
        self.element_by_id[elem_id] = synthetic_elem
        if override_props:
            self.properties_by_elem[elem_id] = override_props

        return synthetic_elem

    def _print_data_stocktake(self, total_spec_elements: int, official: List[str], diagram_only: List[str]) -> None:
        """
        Print MVP9 data stocktake report showing element inventory.

        Shows:
        - Total elements in YAML spec
        - How many found in official EA model (elements.csv)
        - How many created as diagram-only elements
        - Detailed breakdown of each category

        Args:
            total_spec_elements: Total element references in YAML spec
            official: List of element names found in elements.csv
            diagram_only: List of element names created as diagram elements
        """
        print("\n" + "="*70)
        print("MVP9 DATA STOCKTAKE REPORT")
        print("="*70)

        print(f"\nYAML Spec Elements: {total_spec_elements}")

        if official:
            print(f"\n✓ {len(official)} found in elements.csv (official EA model)")
            for name in official:
                print(f"  - {name}")

        if diagram_only:
            print(f"\n→ {len(diagram_only)} created as diagram_elements.csv (curated for diagram)")
            for name in diagram_only:
                print(f"  - {name}")

        if not diagram_only:
            print("\n✓ Status: READY - All elements available")
        else:
            print("\n⚠ Status: Generated missing elements")
            print(f"  - Added {len(diagram_only)} new entries to diagram_elements.csv")
            print(f"  - These will be available for next generation")

        print("\nFor details see:")
        print("  - Official model: archi_inputs/elements.csv")
        print("  - Diagram elements: archi_inputs/diagram_elements.csv")
        print("  - Diagram properties: archi_inputs/diagram_properties.csv")
        print("="*70 + "\n")

    def _persist_diagram_elements(self, selected_elements: List[Dict], official_names: List[str]) -> None:
        """
        Persist newly created diagram elements to diagram_elements.csv and diagram_properties.csv.

        Only writes elements that are NOT in the official model (to avoid duplicates).

        Args:
            selected_elements: All selected elements (mix of official and diagram-only)
            official_names: Names of elements that came from elements.csv
        """
        diagram_elements_file = self.archi_dir / "diagram_elements.csv"
        diagram_properties_file = self.archi_dir / "diagram_properties.csv"

        # Load existing diagram elements to avoid duplicates
        existing_ids = set()
        if diagram_elements_file.exists():
            with open(diagram_elements_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    existing_ids.add(row['ID'])

        # Collect diagram-only elements (not in official model)
        new_elements = []
        new_properties = []

        for elem in selected_elements:
            # Skip if this is from official model
            if elem['name'] in official_names:
                continue

            # Skip if already in diagram_elements.csv
            if elem['id'] in existing_ids:
                continue

            # Add new diagram element
            new_elements.append({
                'ID': elem['id'],
                'Type': elem['type'],
                'Name': elem['name'],
                'Documentation': elem.get('documentation', '')
            })
            existing_ids.add(elem['id'])

            # Add properties for this element (from override)
            props = self.properties_by_elem.get(elem['id'], {})
            for prop_name, prop_value in props.items():
                new_properties.append({
                    'ID': elem['id'],
                    'Key': prop_name,
                    'Value': str(prop_value) if prop_value else ''
                })

        # Write new elements to diagram_elements.csv
        if new_elements:
            with open(diagram_elements_file, 'a', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['ID', 'Type', 'Name', 'Documentation'])
                # Write header if file is empty or new
                if diagram_elements_file.stat().st_size == 0:
                    writer.writeheader()
                writer.writerows(new_elements)

        # Write new properties to diagram_properties.csv
        if new_properties:
            with open(diagram_properties_file, 'a', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['ID', 'Key', 'Value'])
                # Write header if file is empty or new
                if diagram_properties_file.stat().st_size == 0:
                    writer.writeheader()
                writer.writerows(new_properties)

    def _create_inline_element(self, rule: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a synthetic element from inline definition in YAML spec.

        Args:
            rule: Element definition with 'name', 'type', 'properties'

        Returns:
            Synthetic element dict or None if invalid
        """
        elem_name = rule.get('name')
        elem_type = rule.get('type')
        elem_props = rule.get('properties', {})
        override_props = rule.get('override', {})

        if not elem_name or not elem_type:
            print(f"Warning: Inline element missing name or type: {rule}")
            return None

        # Generate deterministic ID from name
        elem_id = f"id-{hashlib.md5(elem_name.encode()).hexdigest()[:12]}"

        # Merge properties with overrides
        final_props = {**elem_props, **override_props}

        # Create synthetic element
        synthetic_elem = {
            'id': elem_id,
            'type': elem_type,
            'name': elem_name,
            'documentation': rule.get('description', '')
        }

        # Add to internal lookups so it can be referenced
        self.element_by_id[elem_id] = synthetic_elem
        self.properties_by_elem[elem_id] = final_props

        print(f"Created inline element: {elem_name} ({elem_type}) [not in model]")

        return synthetic_elem

    def _element_matches(self, elem: Dict[str, Any], where: Dict[str, Any]) -> bool:
        """Check if element matches WHERE clause."""
        # Type filter
        if 'type' in where:
            type_val = where['type']
            if isinstance(type_val, list):
                if elem['type'] not in type_val:
                    return False
            else:
                if elem['type'] != type_val:
                    return False

        # Property filters
        elem_props = self.properties_by_elem.get(elem['id'], {})
        for key, value in where.items():
            if key == 'type':
                continue
            if key not in elem_props:
                return False
            if isinstance(value, list):
                if elem_props[key] not in value:
                    return False
            else:
                if elem_props[key] != value:
                    return False

        return True

    def _filter_relations(self, selected_elements: List[Dict],
                          relations_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter relationships between selected elements."""
        selected_ids = {e['id'] for e in selected_elements}
        filtered = []

        for rel in self.relations:
            if rel['source'] in selected_ids and rel['target'] in selected_ids:
                filtered.append(rel)

        return filtered

    def _create_diagram_relationships(self, selected_elements: List[Dict],
                                       relationships_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Create diagram-specific relationships from YAML spec.

        For freeform diagrams where relationships are defined inline with source_name/target_name.
        Converts name-based references to ID-based relationships and persists to diagram_relationships.csv.

        Args:
            selected_elements: Elements selected for the diagram
            relationships_config: Relationships section from YAML spec

        Returns:
            List of relationship dicts ready for diagram generation
        """
        # Build name-to-ID lookup
        name_to_id = {elem['name']: elem['id'] for elem in selected_elements}

        # Extract relationship definitions
        include_rules = relationships_config.get('include', [])
        if not include_rules:
            return []

        diagram_relations = []
        new_relations_for_csv = []

        for rel_def in include_rules:
            source_name = rel_def.get('source_name')
            target_name = rel_def.get('target_name')
            rel_type = rel_def.get('type', 'Flow')
            label = rel_def.get('label', '')
            description = rel_def.get('description', '')

            # Resolve names to IDs
            source_id = name_to_id.get(source_name)
            target_id = name_to_id.get(target_name)

            if not source_id or not target_id:
                print(f"Warning: Could not resolve relationship {source_name} -> {target_name}")
                continue

            # Generate deterministic ID
            rel_id = f"rel-{hashlib.md5(f'{source_id}-{target_id}-{rel_type}'.encode()).hexdigest()[:12]}"

            # Create relationship object
            rel_obj = {
                'id': rel_id,
                'type': rel_type,
                'source': source_id,
                'target': target_id,
                'documentation': description,
                'label': label
            }

            diagram_relations.append(rel_obj)
            new_relations_for_csv.append({
                'ID': rel_id,
                'Type': rel_type,
                'Source': source_id,
                'Target': target_id,
                'Documentation': description
            })

        # Persist to diagram_relationships.csv
        if new_relations_for_csv:
            self._persist_diagram_relationships(new_relations_for_csv)

        return diagram_relations

    def _persist_diagram_relationships(self, new_relations: List[Dict]) -> None:
        """
        Persist diagram relationships to diagram_relationships.csv.

        Args:
            new_relations: List of relationship dicts to persist
        """
        diagram_relationships_file = self.archi_dir / "diagram_relationships.csv"

        # Load existing IDs to avoid duplicates
        existing_ids = set()
        if diagram_relationships_file.exists():
            with open(diagram_relationships_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    existing_ids.add(row['ID'])

        # Filter out already-existing relationships
        to_write = [rel for rel in new_relations if rel['ID'] not in existing_ids]

        if to_write:
            # Append to file
            with open(diagram_relationships_file, 'a', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['ID', 'Type', 'Source', 'Target', 'Documentation'])
                # Write header if file is new/empty
                if not diagram_relationships_file.exists() or diagram_relationships_file.stat().st_size == 0:
                    writer.writeheader()
                writer.writerows(to_write)

            print(f"Added {len(to_write)} relationships to diagram_relationships.csv")

    def _build_structure_hierarchy(self, selected_elements: List[Dict],
                                    structure_config: Dict[str, Any]) -> Tuple[List[Dict], List[Dict]]:
        """
        Build parent-child hierarchy from relationships (MVP8 enhancement).

        Args:
            selected_elements: Elements already selected by the spec
            structure_config: Structure configuration from YAML spec
                - parent: {type: "Capability"}
                - children: {type: "ApplicationComponent", via: "Serving", direction: "inbound"}
                - layout: "column" or "grid"

        Returns:
            Tuple of:
            - List of parent elements with their children attached
            - List of additional child elements discovered via relationships
        """
        parent_spec = structure_config.get('parent', {})
        children_spec = structure_config.get('children', {})
        child_layout = structure_config.get('layout', 'column')

        parent_type = parent_spec.get('type')
        child_type = children_spec.get('type')
        relationship_type = children_spec.get('via')
        direction = children_spec.get('direction', 'outbound')  # 'inbound' or 'outbound'

        if not parent_type or not child_type:
            return [], []

        # Find parent elements from selected elements
        parents = [e for e in selected_elements if e['type'] == parent_type]

        # Build hierarchy
        hierarchy = []
        additional_children = []

        for parent in parents:
            parent_id = parent['id']

            # Find children based on relationship direction (deduplicated)
            children_ids = set()
            if direction == 'inbound':
                # Children point TO parent (e.g., App -Serving-> Capability)
                # So parent is target, children are sources
                for rel in self.relations:
                    if rel['target'] == parent_id:
                        if not relationship_type or rel['type'] == relationship_type:
                            child_elem = self.element_by_id.get(rel['source'])
                            if child_elem and child_elem['type'] == child_type:
                                children_ids.add(rel['source'])
            else:
                # Parent points TO children (e.g., BusinessFunction -Composition-> Capability)
                # So parent is source, children are targets
                for rel in self.relations:
                    if rel['source'] == parent_id:
                        if not relationship_type or rel['type'] == relationship_type:
                            child_elem = self.element_by_id.get(rel['target'])
                            if child_elem and child_elem['type'] == child_type:
                                children_ids.add(rel['target'])

            # Get child element details
            children = []
            for child_id in children_ids:
                child_elem = self.element_by_id.get(child_id)
                if child_elem:
                    children.append(child_elem)
                    if child_elem not in additional_children:
                        additional_children.append(child_elem)

            hierarchy.append({
                'parent': parent,
                'children': children,
                'layout': child_layout
            })

        return hierarchy, additional_children

    def _enrich_elements(self, elements: List[Dict],
                         presentation: Dict[str, Any],
                         visual: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Enrich elements with presentation data (colors, sizes) and MVP9 emphasis."""
        enriched = []
        color_by = presentation.get('color_by')
        size_by = presentation.get('size_by')

        # MVP9: Build emphasis lookup from visual config
        emphasis_map = {}
        if visual and 'emphasis' in visual:
            for emp in visual.get('emphasis', []):
                elem_name = emp.get('element', '').lower()
                emphasis_map[elem_name] = {
                    'treatment': emp.get('treatment', 'normal'),
                    'role': emp.get('role', '')
                }

        for elem in elements:
            props = self.properties_by_elem.get(elem['id'], {})

            # Determine layer from type
            layer = ELEMENT_LAYERS.get(elem['type'], 'Application')

            # Determine color
            if color_by and color_by in props:
                # Use specified property for coloring
                lifecycle = props.get(color_by, '')
                color = get_element_color(elem, lifecycle)
            else:
                # Default to lifecycle if available, else layer color
                lifecycle = props.get('Lifecycle Status', '')
                color = get_element_color(elem, lifecycle)

            # Calculate width
            width = calculate_element_width(elem['name'])

            # MVP9: Apply emphasis treatment
            emphasis = emphasis_map.get(elem['name'].lower(), {'treatment': 'normal', 'role': ''})

            enriched.append({
                **elem,
                'layer': layer,
                'color': color,
                'width': width,
                'height': 60,
                'properties': props,
                'emphasis': emphasis['treatment'],  # MVP9: prominent, faded, highlighted, normal
                'emphasis_role': emphasis['role']   # MVP9: description of why emphasized
            })

        return enriched

    def _organize_groups(self, elements: List[Dict],
                         grouping: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Organize elements into hierarchical groups."""
        if not grouping or 'by_property' not in grouping:
            # No grouping - single container
            return [{
                'id': 'grp-all',
                'label': 'All',
                'type': 'Container',
                'children': [e['id'] for e in elements],
                'secondary_groups': []
            }]

        primary_prop = grouping.get('by_property')
        secondary_prop = grouping.get('secondary_by_property')
        order = grouping.get('order', [])

        # Group by primary property
        primary_groups = {}
        for elem in elements:
            props = elem.get('properties', {})
            primary_val = props.get(primary_prop, '_ungrouped')

            if primary_val not in primary_groups:
                primary_groups[primary_val] = []
            primary_groups[primary_val].append(elem)

        # Build group structure
        groups = []

        # Build ordered list: first items from order that exist, then remaining groups
        if order:
            # Start with ordered items that exist in data
            ordered_keys = [k for k in order if k in primary_groups]
            # Add remaining groups not in the order list
            remaining = [k for k in primary_groups.keys() if k not in order]
            ordered_keys.extend(sorted(remaining))
        else:
            ordered_keys = sorted(primary_groups.keys())

        for primary_val in ordered_keys:
            group_elems = primary_groups[primary_val]
            group_id = f"grp-{primary_val.lower().replace(' ', '-')}"

            group = {
                'id': group_id,
                'label': primary_val,
                'type': 'Container',
                'children': [e['id'] for e in group_elems],
                'secondary_groups': []
            }

            # Add secondary grouping if specified
            if secondary_prop:
                secondary_groups = {}
                for elem in group_elems:
                    props = elem.get('properties', {})
                    secondary_val = props.get(secondary_prop, '_ungrouped')

                    if secondary_val not in secondary_groups:
                        secondary_groups[secondary_val] = []
                    secondary_groups[secondary_val].append(elem['id'])

                for sec_val, elem_ids in sorted(secondary_groups.items()):
                    group['secondary_groups'].append({
                        'id': f"{group_id}-{sec_val.lower().replace(' ', '-')}",
                        'label': sec_val,
                        'children': elem_ids
                    })

            groups.append(group)

        return groups

    def _generate_drawio(self, view_name: str, elements: List[Dict],
                         relations: List[Dict], layout: Dict,
                         presentation: Dict, grouping_spec: Dict,
                         structure_hierarchy: Optional[List[Dict]] = None,
                         annotations: Optional[List[Dict]] = None,
                         intent: Optional[Dict] = None,
                         story: Optional[Dict] = None) -> str:
        """Generate draw.io XML using AI layout or fallback to deterministic."""
        # Check if matrix layout requested
        algorithm = layout.get('algorithm', 'grid')
        has_secondary = grouping_spec.get('secondary_by_property') is not None

        if algorithm == 'matrix' and has_secondary:
            # Use deterministic matrix layout
            return self._generate_drawio_matrix(
                view_name, elements, relations, grouping_spec,
                layout, annotations, intent
            )

        # Pre-compute groups for narrative generation and fallback
        groups = self._organize_groups(elements, grouping_spec)

        # Build layout data for AI - pass raw grouping spec, let AI handle grouping
        # MVP9: Also pass intent/story for AI context
        layout_data = self._build_layout_data(
            view_name, elements, relations, layout, presentation, grouping_spec,
            structure_hierarchy, annotations, intent, story
        )

        # Try AI-driven layout with sufficient tokens for large diagrams
        try:
            xml_output = self._generate_drawio_ai(layout_data, len(elements))
            # Add narrative textbox to AI output (MVP9: include intent for key_message)
            narrative = self._generate_narrative(view_name, elements, groups, relations, intent)
            return self._embed_narrative_in_drawio(xml_output, narrative, 1400)
        except Exception as e:
            print(f"AI layout failed, using fallback: {e}")
            return self._generate_drawio_fallback(
                view_name, elements, groups, relations, annotations, intent
            )

    def _build_layout_data(self, view_name: str, elements: List[Dict],
                           relations: List[Dict], layout: Dict,
                           presentation: Dict, grouping_spec: Dict,
                           structure_hierarchy: Optional[List[Dict]] = None,
                           annotations: Optional[List[Dict]] = None,
                           intent: Optional[Dict] = None,
                           story: Optional[Dict] = None) -> Dict[str, Any]:
        """Build JSON data for AI layout prompt.

        Passes raw elements and grouping spec to AI - lets AI handle grouping logic.
        Also includes structure hierarchy (parent-child via relationships) and annotations.
        MVP9: Includes intent/story for AI context and emphasis treatments per element.
        """
        # Build element list with all needed data
        elem_list = []
        for elem in elements:
            elem_list.append({
                'id': elem['id'],
                'label': elem['name'],
                'type': elem['type'],
                'layer': elem.get('layer', 'Application'),
                'lifecycle': elem.get('properties', {}).get('Lifecycle Status', ''),
                'color': elem.get('color', '#B5D4E8'),
                'width': elem.get('width', 120),
                'properties': elem.get('properties', {}),
                # MVP9: Emphasis treatment
                'emphasis': elem.get('emphasis', 'normal'),
                'emphasis_role': elem.get('emphasis_role', '')
            })

        # Build relationship list
        rel_list = []
        for rel in relations:
            rel_list.append({
                'id': rel['id'],
                'source': rel['source'],
                'target': rel['target'],
                'type': rel['type']
            })

        data = {
            'canvas': {
                'width': self.CANVAS_WIDTH,
                'height': self.CANVAS_HEIGHT,
                'margin': self.CANVAS_MARGIN
            },
            'view_name': view_name,
            'elements': elem_list,
            'grouping_spec': grouping_spec,
            'relationships': rel_list,
            'layout': layout,  # Pass full layout config to AI (includes algorithm, direction, layer_width, layers, etc.)
            'constraints': {
                'spacing_x': layout.get('spacing_x', 50),
                'spacing_y': layout.get('spacing_y', 40),
                'group_width': layout.get('group_width', 800),
                'min_element_width': 120,
                'max_element_width': 300
            },
            'presentation': presentation
        }

        # Add structure hierarchy if present (MVP8 enhancement)
        if structure_hierarchy:
            data['structure_hierarchy'] = structure_hierarchy

        # Add annotations if present (MVP8 enhancement)
        if annotations:
            data['annotations'] = annotations

        # MVP9: Add intent and story for AI context
        if intent:
            data['intent'] = intent
        if story:
            data['story'] = story

        return data

    def _generate_drawio_ai(self, layout_data: Dict[str, Any], element_count: int = 10) -> str:
        """Generate draw.io XML using AI with dynamic token allocation."""
        if not self.drawio_prompt_file.exists():
            raise FileNotFoundError(f"Prompt not found: {self.drawio_prompt_file}")

        with open(self.drawio_prompt_file, 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        # Insert layout data
        layout_json = json.dumps(layout_data, indent=2)
        prompt = prompt_template.replace('{layout_data_json}', layout_json)

        # Calculate max_tokens based on diagram complexity
        # ~200 tokens per element (mxCell with geometry) + ~100 per relationship + base overhead
        estimated_tokens = 2000 + (element_count * 250) + (len(layout_data.get('relationships', [])) * 150)
        max_tokens = min(16000, max(4096, estimated_tokens))  # Cap at 16K, floor at 4K

        # Call AI with sufficient tokens
        response = chat(
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.3,
            max_tokens=max_tokens
        )

        # Debug: Log API response metadata to diagnose truncation
        finish_reason = response.choices[0].finish_reason
        usage = response.usage
        print(f"[AI DEBUG] max_tokens requested: {max_tokens}")
        print(f"[AI DEBUG] finish_reason: {finish_reason}")
        print(f"[AI DEBUG] prompt_tokens: {usage.prompt_tokens}, completion_tokens: {usage.completion_tokens}, total: {usage.total_tokens}")
        if finish_reason == 'length':
            print(f"[AI DEBUG] WARNING: Response truncated! completion_tokens ({usage.completion_tokens}) hit limit.")

        xml_output = response.choices[0].message.content.strip()

        # Strip markdown code fences if present (AI sometimes wraps in ```xml ... ```)
        if xml_output.startswith('```'):
            # Find the end of the opening fence line
            first_newline = xml_output.find('\n')
            if first_newline != -1:
                xml_output = xml_output[first_newline + 1:]
            # Remove closing fence
            if xml_output.endswith('```'):
                xml_output = xml_output[:-3].strip()

        # Validate it's XML
        if not xml_output.startswith('<?xml') and not xml_output.startswith('<mxfile'):
            raise ValueError(f"AI did not return valid draw.io XML. First 100 chars: {xml_output[:100]}")

        return xml_output

    def _generate_drawio_fallback(self, view_name: str, elements: List[Dict],
                                   groups: List[Dict], relations: List[Dict],
                                   annotations: Optional[List[Dict]] = None,
                                   intent: Optional[Dict] = None) -> str:
        """Fallback deterministic draw.io generation with full element rendering."""
        exporter = DrawIOExporter()

        containers = []
        drawio_elements = []
        elem_id_map = {}
        elem_positions = {}  # Track positions for annotations

        container_y = 50
        for group in groups:
            container_id = group['id']
            group_elems = [e for e in elements if e['id'] in group['children']]

            if not group_elems:
                continue

            # Create container
            container = DrawIOContainer(
                id=container_id,
                label=group['label'],
                x=50,
                y=container_y,
                width=1200,
                height=max(200, len(group_elems) * 100)
            )
            containers.append(container)

            # Position elements (coordinates relative to container)
            cols = 4
            for idx, elem in enumerate(group_elems):
                row = idx // cols
                col = idx % cols
                x = 80 + col * 280
                y = 60 + row * 100  # Relative to container, not absolute

                drawio_elem = DrawIOElement(
                    id=elem['id'],
                    name=elem['name'],
                    x=x,
                    y=y,
                    width=elem.get('width', 180),
                    height=60,
                    elem_type=elem['type'],
                    parent_id=container_id,
                    color=elem.get('color', '#B5D4E8'),
                    emphasis=elem.get('emphasis', 'normal')  # MVP9
                )
                drawio_elements.append(drawio_elem)
                elem_id_map[elem['id']] = drawio_elem
                # Track absolute position for annotations
                elem_positions[elem['name'].lower()] = {
                    'x': container.x + x,
                    'y': container.y + y,
                    'width': elem.get('width', 180)
                }

            container_y += container.height + 80

        # Add relationships (deduplicated by source-target pair)
        drawio_edges = []
        seen_edges = set()
        for rel in relations:
            if rel['source'] in elem_id_map and rel['target'] in elem_id_map:
                edge_key = (rel['source'], rel['target'])
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    drawio_edges.append(DrawIOEdge(
                        from_id=rel['source'],
                        to_id=rel['target'],
                        label=rel['type'],
                        edge_type=rel['type']
                    ))

        # Generate narrative and add as textbox
        xml_output = exporter.export(
            elements=drawio_elements,
            edges=drawio_edges,
            containers=containers,
            view_name=view_name
        )

        # Add annotations if present
        if annotations:
            xml_output = self._embed_annotations_in_drawio(xml_output, annotations, elem_positions)

        # Add narrative textbox to XML (MVP9: include intent for key_message)
        narrative = self._generate_narrative(view_name, elements, groups, relations, intent)
        xml_with_narrative = self._embed_narrative_in_drawio(xml_output, narrative, container_y)

        return xml_with_narrative

    def _embed_annotations_in_drawio(self, xml_output: str, annotations: List[Dict],
                                      elem_positions: Dict[str, Dict]) -> str:
        """Embed annotation labels in draw.io XML near specified elements."""
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(xml_output)
            root_elem = root.find(".//root")
            if root_elem is None:
                return xml_output

            for idx, ann in enumerate(annotations):
                text = ann.get('text', '')
                near = ann.get('near', '').lower()

                # Find element position
                pos = elem_positions.get(near)
                if not pos:
                    # Try partial match
                    for name, p in elem_positions.items():
                        if near in name or name in near:
                            pos = p
                            break

                if pos:
                    # Position annotation above the element
                    ann_x = pos['x']
                    ann_y = pos['y'] - 25  # Above the element
                    ann_width = max(80, len(text) * 7)

                    textbox = ET.Element('mxCell')
                    textbox.set('id', f'ann-{idx}')
                    textbox.set('value', text)
                    textbox.set('vertex', '1')
                    textbox.set('parent', '1')
                    textbox.set('style', 'text;html=1;align=left;verticalAlign=middle;'
                                        'fontSize=9;fontStyle=2;fillColor=#E8F5E9;'
                                        'strokeColor=none;rounded=1;spacing=4;')

                    geometry = ET.SubElement(textbox, 'mxGeometry')
                    geometry.set('x', str(int(ann_x)))
                    geometry.set('y', str(int(ann_y)))
                    geometry.set('width', str(int(ann_width)))
                    geometry.set('height', '20')
                    geometry.set('as', 'geometry')

                    root_elem.append(textbox)

            xml_str = ET.tostring(root, encoding='unicode')
            return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str

        except Exception as e:
            print(f"Failed to embed annotations: {e}")
            return xml_output

    def _generate_drawio_matrix(self, view_name: str, elements: List[Dict],
                                 relations: List[Dict], grouping_spec: Dict,
                                 layout: Dict, annotations: Optional[List[Dict]] = None,
                                 intent: Optional[Dict] = None) -> str:
        """
        Generate draw.io XML with proper matrix layout (rows × columns).

        Creates:
        - Row headers (primary grouping) on the left
        - Column headers (secondary grouping) at the top
        - Cells at intersections containing elements
        """
        exporter = DrawIOExporter()

        # Get grouping config
        primary_prop = grouping_spec.get('by_property', 'Horizon')
        secondary_prop = grouping_spec.get('secondary_by_property')
        row_order = grouping_spec.get('order', [])
        column_order = grouping_spec.get('secondary_order', [])
        row_labels = grouping_spec.get('labels', {})

        # Organize elements into nested groups using element properties
        grouped_elements = {}  # row -> col -> [element_ids]
        for elem in elements:
            props = elem.get('properties', {})
            row_val = props.get(primary_prop, '_ungrouped')
            col_val = props.get(secondary_prop, '_ungrouped') if secondary_prop else '_ungrouped'

            if row_val not in grouped_elements:
                grouped_elements[row_val] = {}
            if col_val not in grouped_elements[row_val]:
                grouped_elements[row_val][col_val] = []
            grouped_elements[row_val][col_val].append(elem['id'])

        # Use MatrixLayout to calculate positions
        matrix_layout = MatrixLayout(
            row_height=layout.get('row_height', 120),
            column_width=layout.get('column_width', 200)
        )

        layout_result = matrix_layout.calculate_matrix_layout(
            elements=elements,
            grouped_elements=grouped_elements,
            row_order=row_order,
            column_order=column_order,
            row_labels=row_labels
        )

        # Build containers from layout result
        containers = []

        # Column headers (styled as header cells)
        for col_header in layout_result.column_headers:
            containers.append(DrawIOContainer(
                id=col_header.container_id,
                label=col_header.label,
                x=col_header.x,
                y=col_header.y,
                width=col_header.w,
                height=col_header.h,
                style="swimlane;startSize=30;fillColor=#E3F2FD;strokeColor=#1976D2;fontStyle=1"
            ))

        # Row headers (styled as header cells)
        for row_header in layout_result.row_headers:
            containers.append(DrawIOContainer(
                id=row_header.container_id,
                label=row_header.label,
                x=row_header.x,
                y=row_header.y,
                width=row_header.w,
                height=row_header.h,
                style="swimlane;horizontal=0;startSize=30;fillColor=#E8F5E9;strokeColor=#388E3C;fontStyle=1"
            ))

        # Cells (light background)
        for cell in layout_result.cells:
            containers.append(DrawIOContainer(
                id=cell.container_id,
                label="",
                x=cell.x,
                y=cell.y,
                width=cell.w,
                height=cell.h,
                style="rounded=0;fillColor=#FAFAFA;strokeColor=#E0E0E0;strokeWidth=1"
            ))

        # Build elements from layout result
        drawio_elements = []
        elem_by_id = {e['id']: e for e in elements}
        elem_positions = {}

        for pos in layout_result.elements:
            elem = elem_by_id.get(pos.element_id)
            if elem:
                drawio_elements.append(DrawIOElement(
                    id=elem['id'],
                    name=elem['name'],
                    x=pos.x,
                    y=pos.y,
                    width=pos.w,
                    height=pos.h,
                    elem_type=elem['type'],
                    parent_id=None,  # Absolute positioning
                    color=elem.get('color', '#B5D4E8'),
                    emphasis=elem.get('emphasis', 'normal')
                ))
                # Track for annotations
                elem_positions[elem['name'].lower()] = {
                    'x': pos.x,
                    'y': pos.y,
                    'width': pos.w
                }

        # Build edges
        drawio_edges = []
        elem_ids_in_view = {e['id'] for e in elements}
        seen_edges = set()

        for rel in relations:
            source_id = rel.get('source')
            target_id = rel.get('target')
            if source_id in elem_ids_in_view and target_id in elem_ids_in_view:
                edge_key = (source_id, target_id)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    drawio_edges.append(DrawIOEdge(
                        from_id=source_id,
                        to_id=target_id,
                        label=rel.get('type', ''),
                        edge_type=rel.get('type', 'Flow')
                    ))

        # Generate XML
        xml_output = exporter.export(
            elements=drawio_elements,
            edges=drawio_edges,
            containers=containers,
            view_name=view_name
        )

        # Add annotations relative to elements
        if annotations:
            xml_output = self._embed_annotations_in_drawio(xml_output, annotations, elem_positions)

        # Add narrative
        max_y = max(
            (c.y + c.h for c in layout_result.cells),
            default=500
        )
        narrative = self._generate_narrative(view_name, elements, [], relations, intent)
        xml_output = self._embed_narrative_in_drawio(xml_output, narrative, max_y + 50)

        return xml_output

    def _generate_archi(self, view_name: str, elements: List[Dict],
                        groups: List[Dict], relations: List[Dict],
                        layout: Dict, presentation: Dict) -> str:
        """Generate ArchiMate XML (placeholder - uses existing MVP7 logic)."""
        # For now, return a message indicating Archi export should use existing pipeline
        # Full implementation would integrate with archi_export.py
        return f"<!-- ArchiMate XML for '{view_name}' - use ea_generate_views_from_specs for full output -->"

    def _write_diagram_elements(self, enriched_elements: List[Dict[str, Any]]) -> None:
        """
        MVP9: Write enriched elements to diagram_elements.csv and their properties to diagram_properties.csv.

        This ensures that elements with property overrides from the view spec are available
        for the portal builder to read.

        Args:
            enriched_elements: List of enriched element dicts with properties and overrides applied
        """
        # Load existing diagram elements to avoid duplicates
        diagram_elements_file = self.archi_dir / "diagram_elements.csv"
        existing_ids = set()

        if diagram_elements_file.exists():
            with open(diagram_elements_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    existing_ids.add(row['ID'])

        # Load existing diagram properties to avoid duplicates
        diagram_properties_file = self.archi_dir / "diagram_properties.csv"
        existing_props = set()

        if diagram_properties_file.exists():
            with open(diagram_properties_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    existing_props.add((row['ID'], row['Key']))

        # Collect new elements and properties
        new_elements = []
        new_properties = []

        for elem in enriched_elements:
            elem_id = elem['id']

            # Add element if not already in diagram_elements.csv
            if elem_id not in existing_ids:
                new_elements.append({
                    'ID': elem_id,
                    'Type': elem['type'],
                    'Name': elem['name'],
                    'Documentation': elem.get('documentation', '')
                })
                existing_ids.add(elem_id)

            # Add properties for this element
            props = elem.get('properties', {})
            for prop_name, prop_value in props.items():
                prop_key = (elem_id, prop_name)
                if prop_key not in existing_props:
                    new_properties.append({
                        'Element ID': elem_id,
                        'Property Name': prop_name,
                        'Property Value': str(prop_value) if prop_value else ''
                    })
                    existing_props.add(prop_key)

        # Append new elements to diagram_elements.csv
        if new_elements:
            with open(diagram_elements_file, 'a', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['ID', 'Type', 'Name', 'Documentation'])
                # Only write header if file is new/empty
                if diagram_elements_file.stat().st_size == 0 or not diagram_elements_file.exists():
                    writer.writeheader()
                writer.writerows(new_elements)

        # Append new properties to diagram_properties.csv
        if new_properties:
            with open(diagram_properties_file, 'a', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['Element ID', 'Property Name', 'Property Value'])
                # Only write header if file is new/empty
                if diagram_properties_file.stat().st_size == 0 or not diagram_properties_file.exists():
                    writer.writeheader()
                writer.writerows(new_properties)

    def _write_output(self, spec_path: str, content: str, extension: str) -> Path:
        """Write generated content to file, preserving directory structure from spec."""
        spec_path_obj = Path(spec_path)

        # Extract relative path from ea_inputs/views/
        try:
            # Get the path relative to ea_inputs/views/
            relative_to_views = spec_path_obj.relative_to(Path("ea_inputs/views"))
            # Preserve subdirectory structure in output
            output_subdir = relative_to_views.parent
            spec_name = spec_path_obj.stem

            output_dir = Path("ea_diagrams") / output_subdir
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{spec_name}.{extension}"
        except ValueError:
            # Fallback: spec not in ea_inputs/views/, use flat structure
            output_dir = Path("ea_diagrams")
            output_dir.mkdir(exist_ok=True)
            spec_name = spec_path_obj.stem
            output_path = output_dir / f"{spec_name}.{extension}"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return output_path

    def _generate_narrative(self, view_name: str, elements: List[Dict],
                           groups: List[Dict], relations: List[Dict],
                           intent: Optional[Dict] = None) -> str:
        """Generate narrative description of the diagram."""
        lines = [f"📊 {view_name}"]
        lines.append("")

        # MVP9: Show key message if available
        if intent and intent.get('key_message'):
            lines.append(f"💡 {intent['key_message']}")
            lines.append("")

        # Summary counts
        lines.append(f"Elements: {len(elements)} | Relationships: {len(relations)}")
        lines.append("")

        # Group summary
        if len(groups) > 1:
            lines.append("Groups:")
            for group in groups:
                group_size = len(group.get('children', []))
                lines.append(f"  • {group['label']}: {group_size} elements")
            lines.append("")

        # Color legend (lifecycle)
        lifecycle_colors = {}
        for elem in elements:
            props = elem.get('properties', {})
            lifecycle = props.get('Lifecycle Status', 'Not specified')
            if lifecycle not in lifecycle_colors:
                lifecycle_colors[lifecycle] = 0
            lifecycle_colors[lifecycle] += 1

        if lifecycle_colors:
            lines.append("Lifecycle Status:")
            for status, count in sorted(lifecycle_colors.items()):
                lines.append(f"  • {status}: {count} systems")
            lines.append("")

        # Relationships summary
        if relations:
            rel_types = {}
            for rel in relations:
                rel_type = rel.get('type', 'Unknown')
                if rel_type not in rel_types:
                    rel_types[rel_type] = 0
                rel_types[rel_type] += 1

            lines.append("Relationships:")
            for rel_type, count in sorted(rel_types.items()):
                lines.append(f"  • {rel_type}: {count} connections")
            lines.append("")

        # Key insights
        lines.append("Color coding:")
        lines.append("  • Green = Strategic | Orange = Maintain | Red = Sunset | Blue = Standard")

        return "\n".join(lines)

    def _embed_narrative_in_drawio(self, xml_output: str, narrative: str,
                                  bottom_y: int) -> str:
        """Embed narrative as textbox in draw.io XML."""
        import xml.etree.ElementTree as ET

        # Parse XML
        root = ET.fromstring(xml_output)

        # Find the root element that contains mxCells (diagram or mxGraphModel)
        root_elem = root.find(".//root")

        if root_elem is None:
            # XML structure not as expected, return original
            return xml_output

        # Calculate height based on number of lines (approximately 16px per line)
        line_count = len(narrative.split('\n'))
        text_height = max(100, line_count * 16 + 20)

        # Create narrative textbox mxCell
        # Position it below all the diagram elements
        text_y = bottom_y + 100
        textbox = ET.Element('mxCell')
        textbox.set('id', f'narrative-{abs(hash(narrative)) % 1000000}')
        textbox.set('value', narrative)
        textbox.set('vertex', '1')
        textbox.set('parent', '1')
        textbox.set('style', 'text;html=1;align=left;verticalAlign=top;whiteSpace=wrap;'
                             'overflow=hidden;fontSize=10;fontFamily=Courier;fillColor=#F5F5F5;'
                             'strokeColor=#999999;rounded=1;spacing=5;')

        # Add geometry with calculated height
        geometry = ET.SubElement(textbox, 'mxGeometry')
        geometry.set('x', '50')
        geometry.set('y', str(text_y))
        geometry.set('width', '1350')
        geometry.set('height', str(text_height))
        geometry.set('as', 'geometry')

        # Append textbox to root element
        root_elem.append(textbox)

        # Convert back to string with XML declaration
        xml_str = ET.tostring(root, encoding='unicode')
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str


def generate_diagram(spec_path: str) -> Dict[str, Any]:
    """
    Generate diagram from YAML spec (convenience function).

    Args:
        spec_path: Path to YAML view spec

    Returns:
        Dict with generated content and metadata
    """
    generator = DiagramGenerator()
    return generator.generate(spec_path)
