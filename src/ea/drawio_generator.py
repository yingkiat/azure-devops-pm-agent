"""
Draw.io Generator (MVP8 + MVP9)

Generates draw.io diagrams from YAML view specs with AI-driven layout.
Delegates element selection and property overrides to ElementSelector.

Key features (MVP8):
- Reads extended YAML spec (presentation, output sections)
- Applies ArchiMate layer colors
- Uses AI for intelligent layout
- Outputs to draw.io XML

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
from .element_selector import ElementSelector


class DrawIOGenerator:
    """
    Draw.io diagram generator with AI-driven layout.

    Reads YAML view specs and generates draw.io diagrams.
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

        # Element selector with shared selection logic
        self.selector = ElementSelector(self.elements, self.properties, str(self.archi_dir))

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

        # Select elements (delegates to ElementSelector)
        selected_element_ids = self.selector.select_elements(elements_config)
        # Use selector's element_by_id which includes synthetic elements created during selection
        selected_elements = [self.selector.element_by_id[eid] for eid in selected_element_ids if eid in self.selector.element_by_id]

        # Build relation pool (existing + explicit YAML relations) before structure processing
        selected_relations = self._filter_relations(selected_elements, spec.get('relationships', {}))

        # If structure config exists, build hierarchy and extend element selection
        structure_hierarchy = None
        if structure_config:
            structure_hierarchy, additional_elements = self._build_structure_hierarchy(
                selected_elements, structure_config, selected_relations
            )
            # Add child elements discovered via relationships
            for elem in additional_elements:
                if elem not in selected_elements:
                    selected_elements.append(elem)

        if not selected_elements:
            return {'error': 'No elements selected by spec'}

        # Re-filter relationships after structure expansion so any discovered children are included
        selected_relations = self._filter_relations(selected_elements, spec.get('relationships', {}))

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

    # Element selection delegated to ElementSelector (shared with archi_generator)

    def _filter_relations(self, selected_elements: List[Dict],
                          relations_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter relationships between selected elements, including explicit YAML relations."""
        selected_ids = {e['id'] for e in selected_elements}
        name_to_id = {e['name'].strip().lower(): e['id'] for e in selected_elements}
        include_rules = relations_config.get('include', []) if relations_config else []
        include_types = set()

        for rule in include_rules:
            if 'between' in rule or ('source_name' not in rule and 'target_name' not in rule):
                types = rule.get('type', [])
                if isinstance(types, str):
                    include_types.add(types)
                else:
                    include_types.update(types)

        filtered = []
        seen = set()

        # Existing model relationships between selected elements
        for rel in self.relations:
            if rel['source'] in selected_ids and rel['target'] in selected_ids:
                if include_types and rel['type'] not in include_types:
                    continue
                key = (rel['type'], rel['source'], rel['target'], rel.get('documentation', ''))
                if key not in seen:
                    seen.add(key)
                    filtered.append(rel)

        # Explicit YAML relationships for ad hoc cooperation views
        for idx, rule in enumerate(include_rules):
            source_name = rule.get('source_name')
            target_name = rule.get('target_name')
            rel_type = rule.get('type')
            if not source_name or not target_name or not rel_type:
                continue

            source_id = name_to_id.get(source_name.strip().lower())
            target_id = name_to_id.get(target_name.strip().lower())
            if not source_id or not target_id:
                continue

            documentation = rule.get('description', '')
            label = rule.get('label', rel_type)
            key = (rel_type, source_id, target_id, documentation)
            if key in seen:
                continue

            seen.add(key)
            filtered.append({
                'id': f"spec-rel-{idx}",
                'type': rel_type,
                'source': source_id,
                'target': target_id,
                'documentation': documentation,
                'label': label
            })

        return filtered

    def _edge_label(self, rel: Dict[str, Any], elements_by_id: Dict[str, Dict[str, Any]]) -> str:
        """Return a non-redundant edge label."""
        if 'label' in rel:
            label = (rel.get('label') or '').strip()
        else:
            label = (rel.get('type') or '').strip()
        if not label:
            return ''

        source_name = elements_by_id.get(rel.get('source'), {}).get('name', '').strip().lower()
        target_name = elements_by_id.get(rel.get('target'), {}).get('name', '').strip().lower()
        norm_label = label.lower()

        if norm_label == source_name or norm_label == target_name:
            return ''

        return label

    def _build_structure_hierarchy(self, selected_elements: List[Dict],
                                    structure_config: Dict[str, Any],
                                    relations: Optional[List[Dict[str, Any]]] = None) -> Tuple[List[Dict], List[Dict]]:
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
        relation_pool = relations if relations is not None else self.relations

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
                for rel in relation_pool:
                    if rel['target'] == parent_id:
                        if not relationship_type or rel['type'] == relationship_type:
                            child_elem = self.element_by_id.get(rel['source'])
                            if child_elem and child_elem['type'] == child_type:
                                children_ids.add(rel['source'])
            else:
                # Parent points TO children (e.g., BusinessFunction -Composition-> Capability)
                # So parent is source, children are targets
                for rel in relation_pool:
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
            # Get properties with override support from ElementSelector
            props = dict(self.properties_by_elem.get(elem['id'], {}))
            # Apply property overrides from view spec
            if elem['id'] in self.selector.property_overrides:
                props.update(self.selector.property_overrides[elem['id']])

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
                'display_name': props.get('Display Name', elem['name']),
                'layer': layer,
                'color': color,
                'width': calculate_element_width(props.get('Display Name', elem['name'])),
                'height': 60,
                'properties': props,  # Now includes property overrides
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

        if algorithm == 'hub_spoke':
            return self._generate_drawio_hub_spoke(
                view_name, elements, relations, structure_hierarchy,
                layout, annotations, intent
            )

        if algorithm == 'flow_left_right':
            return self._generate_drawio_flow_left_right(
                view_name, elements, relations, layout, annotations, intent
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
            # Post-process: shrink containers to fit content (fix AI whitespace issue)
            xml_output = self._shrink_containers_to_fit(xml_output)
            # Calculate actual bottom Y after shrinking
            bottom_y = self._get_diagram_bottom_y(xml_output)
            # Add narrative textbox to AI output (MVP9: include intent for key_message)
            narrative = self._generate_narrative(view_name, elements, groups, relations, intent)
            return self._embed_narrative_in_drawio(xml_output, narrative, bottom_y)
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
        elements_by_id = {e['id']: e for e in elements}

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

            # Position elements in a grid layout
            cols = 4
            rows_needed = (len(group_elems) + cols - 1) // cols  # ceil division

            # Create container with height based on actual rows needed
            container = DrawIOContainer(
                id=container_id,
                label=group['label'],
                x=50,
                y=container_y,
                width=1200,
                height=max(200, rows_needed * 100 + 80)  # +80 for header and padding
            )
            containers.append(container)
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
                        label=self._edge_label(rel, elements_by_id),
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

    def _generate_drawio_hub_spoke(self, view_name: str, elements: List[Dict],
                                   relations: List[Dict],
                                   structure_hierarchy: Optional[List[Dict]],
                                   layout: Dict,
                                   annotations: Optional[List[Dict]] = None,
                                   intent: Optional[Dict] = None) -> str:
        """Generate deterministic hub-and-spoke application cooperation layout."""
        exporter = DrawIOExporter()
        elements_by_id = {elem['id']: elem for elem in elements}

        if not structure_hierarchy:
            groups = self._organize_groups(elements, {})
            return self._generate_drawio_fallback(view_name, elements, groups, relations, annotations, intent)

        hub_entry = structure_hierarchy[0]
        hub = elements_by_id.get(hub_entry['parent']['id'], hub_entry['parent'])
        child_ids = {child['id'] for child in hub_entry.get('children', [])}
        child_by_id = {child_id: elements_by_id.get(child_id, child) for child_id, child in ((c['id'], c) for c in hub_entry.get('children', []))}
        hub_prop = layout.get('core_group_by', 'Internal Group')
        spoke_side_prop = layout.get('spoke_side_property', 'Spoke Side')

        containers = []
        drawio_elements = []
        elem_positions = {}

        center_x = layout.get('center_x', 700)
        center_y = layout.get('center_y', 260)
        hub_width = layout.get('hub_width', 560)
        hub_height = layout.get('hub_height', 300)
        hub_x = center_x - (hub_width // 2)
        hub_y = center_y - (hub_height // 2)

        # Use the hub element id as the outer container id so future edges can target it if needed.
        containers.append(DrawIOContainer(
            id=hub['id'],
            label=hub['name'],
            x=hub_x,
            y=hub_y,
            width=hub_width,
            height=hub_height,
            style="swimlane;startSize=42;fillColor=#E3F2FD;strokeColor=#1565C0;fontStyle=1;strokeWidth=2;"
        ))
        elem_positions[hub['name'].lower()] = {'x': hub_x + 20, 'y': hub_y + 20, 'width': hub_width - 40}

        children = [child_by_id[cid] for cid in child_ids]
        grouped_children = {}
        for child in children:
            group_name = child.get('properties', {}).get(hub_prop, '_ungrouped')
            grouped_children.setdefault(group_name, []).append(child)

        ordered_group_names = list(grouped_children.keys())
        requested_group_order = layout.get('core_group_order', [])
        if requested_group_order:
            ordered_group_names = [g for g in requested_group_order if g in grouped_children] + [
                g for g in ordered_group_names if g not in requested_group_order
            ]
        group_count = max(1, len(ordered_group_names))
        subgroup_gap = layout.get('core_group_spacing', 20)
        subgroup_inner_margin = layout.get('core_inner_margin', 24)
        subgroup_top = 54
        subgroup_height = hub_height - subgroup_top - subgroup_inner_margin
        subgroup_width = int((hub_width - (2 * subgroup_inner_margin) - ((group_count - 1) * subgroup_gap)) / group_count)
        subgroup_container_by_child = {}
        subgroup_meta = {}

        for idx, group_name in enumerate(ordered_group_names):
            subgroup_id = f"{hub['id']}-grp-{idx}"
            subgroup_x = subgroup_inner_margin + idx * (subgroup_width + subgroup_gap)
            subgroup_y = subgroup_top
            containers.append(DrawIOContainer(
                id=subgroup_id,
                label=group_name if group_name != '_ungrouped' else '',
                x=subgroup_x,
                y=subgroup_y,
                width=subgroup_width,
                height=subgroup_height,
                parent_id=hub['id'],
                style="swimlane;startSize=28;fillColor=#F8FBFF;strokeColor=#90CAF9;fontStyle=1;"
            ))
            subgroup_meta[subgroup_id] = {
                'index': idx,
                'group_name': group_name
            }

            child_y = 38
            for child in grouped_children[group_name]:
                subgroup_container_by_child[child['id']] = subgroup_id
                child_width = min(child.get('width', 180), subgroup_width - 24)
                child_x = int((subgroup_width - child_width) / 2)
                drawio_elements.append(DrawIOElement(
                    id=child['id'],
                    name=child['name'],
                    x=child_x,
                    y=child_y,
                    width=child_width,
                    height=60,
                    elem_type=child['type'],
                    parent_id=subgroup_id,
                    color=child.get('color', '#B5D4E8'),
                    emphasis=child.get('emphasis', 'normal')
                ))
                elem_positions[child['name'].lower()] = {
                    'x': hub_x + subgroup_x + child_x,
                    'y': hub_y + subgroup_y + child_y,
                    'width': child_width
                }
                child_y += 84

        external_elements = [e for e in elements if e['id'] not in child_ids and e['id'] != hub['id']]

        ext_w = layout.get('external_width', 210)
        ext_h = 60
        ext_gap = layout.get('external_spacing', 30)
        ext_offset = layout.get('external_offset', 120)
        external_group_prop = layout.get('external_group_by', 'External Group')
        external_group_order = layout.get('external_group_order', [])
        external_group_side_map = {
            k: v.lower() for k, v in layout.get('external_group_side_map', {}).items()
        }

        def group_external_elems(elems: List[Dict]) -> List[Tuple[str, List[Dict], str]]:
            grouped = {}
            for elem in elems:
                group_name = elem.get('properties', {}).get(external_group_prop, '').strip() or 'Other'
                grouped.setdefault(group_name, []).append(elem)
            ordered_names = [g for g in external_group_order if g in grouped] + [
                g for g in sorted(grouped.keys()) if g not in external_group_order
            ]
            result = []
            for name in ordered_names:
                elems_for_group = grouped[name]
                side = external_group_side_map.get(name)
                if not side:
                    counts = {}
                    for elem in elems_for_group:
                        elem_side = elem.get('properties', {}).get(spoke_side_prop, '').strip().lower() or 'right'
                        counts[elem_side] = counts.get(elem_side, 0) + 1
                    side = sorted(counts.items(), key=lambda x: (-x[1], x[0]))[0][0]
                result.append((name, elems_for_group, side))
            return result

        grouped_external = group_external_elems(external_elements)
        by_side = {'top': [], 'right': [], 'bottom': [], 'left': []}
        for group_name, group_elems, side in grouped_external:
            if side not in by_side:
                side = 'right'
            by_side[side].append((group_name, group_elems))

        def place_stack(side: str, elems: List[Dict]) -> None:
            if not elems:
                return
            if side in ('left', 'right'):
                group_dims = []
                for group_name, group_elems in elems:
                    group_height = 34 + (len(group_elems) * ext_h) + ((len(group_elems) - 1) * 16) + 20
                    group_width = ext_w + 30
                    group_dims.append((group_name, group_elems, group_width, group_height))
                total_h = sum(dim[3] for dim in group_dims) + ((len(group_dims) - 1) * ext_gap)
                start_y = int(center_y - (total_h / 2))
                x = hub_x - ext_offset - (ext_w + 30) if side == 'left' else hub_x + hub_width + ext_offset
                current_y = start_y
                for idx, (group_name, group_elems, group_width, group_height) in enumerate(group_dims):
                    group_id = f"ext-{side}-{idx}"
                    containers.append(DrawIOContainer(
                        id=group_id,
                        label=group_name,
                        x=x,
                        y=current_y,
                        width=group_width,
                        height=group_height,
                        style="swimlane;startSize=28;fillColor=#F5F5F5;strokeColor=#9E9E9E;fontStyle=1;"
                    ))
                    inner_y = 38
                    for elem in group_elems:
                        drawio_elements.append(DrawIOElement(
                            id=elem['id'],
                            name=elem['name'],
                            x=15,
                            y=inner_y,
                            width=ext_w,
                            height=ext_h,
                            elem_type=elem['type'],
                            parent_id=group_id,
                            color=elem.get('color', '#B5D4E8'),
                            emphasis=elem.get('emphasis', 'normal')
                        ))
                        elem_positions[elem['name'].lower()] = {'x': x + 15, 'y': current_y + inner_y, 'width': ext_w}
                        inner_y += ext_h + 16
                    current_y += group_height + ext_gap
            else:
                group_dims = []
                for group_name, group_elems in elems:
                    group_width = max(ext_w + 30, 30 + len(group_elems) * ext_w + max(0, len(group_elems) - 1) * 16)
                    group_height = 34 + ext_h + 20
                    group_dims.append((group_name, group_elems, group_width, group_height))
                total_w = sum(dim[2] for dim in group_dims) + ((len(group_dims) - 1) * ext_gap)
                start_x = int(center_x - (total_w / 2))
                y = hub_y - ext_offset - (34 + ext_h + 20) if side == 'top' else hub_y + hub_height + ext_offset
                current_x = start_x
                for idx, (group_name, group_elems, group_width, group_height) in enumerate(group_dims):
                    group_id = f"ext-{side}-{idx}"
                    containers.append(DrawIOContainer(
                        id=group_id,
                        label=group_name,
                        x=current_x,
                        y=y,
                        width=group_width,
                        height=group_height,
                        style="swimlane;startSize=28;fillColor=#F5F5F5;strokeColor=#9E9E9E;fontStyle=1;"
                    ))
                    inner_x = 15
                    for elem in group_elems:
                        drawio_elements.append(DrawIOElement(
                            id=elem['id'],
                            name=elem['name'],
                            x=inner_x,
                            y=38,
                            width=ext_w,
                            height=ext_h,
                            elem_type=elem['type'],
                            parent_id=group_id,
                            color=elem.get('color', '#B5D4E8'),
                            emphasis=elem.get('emphasis', 'normal')
                        ))
                        elem_positions[elem['name'].lower()] = {'x': current_x + inner_x, 'y': y + 38, 'width': ext_w}
                        inner_x += ext_w + 16
                    current_x += group_width + ext_gap

        for side in ('top', 'right', 'bottom', 'left'):
            place_stack(side, by_side[side])

        drawio_edges = []
        seen_edges = set()
        standardize_to_group = layout.get('standardize_edges_to_group', False)
        subgroup_anchor_usage = {}

        def anchor_for_subgroup(subgroup_id: str, target_side: str) -> Optional[Dict[str, str]]:
            meta = subgroup_meta.get(subgroup_id)
            if not meta:
                return None
            idx = meta['index']
            # Left column: top / left / bottom
            # Middle column: top / bottom
            # Right column: top / right / bottom
            if idx == 0:
                allowed = ['top', 'left', 'bottom']
            elif idx == 1:
                allowed = ['top', 'bottom']
            else:
                allowed = ['top', 'right', 'bottom']

            preferred = {
                'top': 'top',
                'bottom': 'bottom',
                'left': 'left',
                'right': 'right'
            }.get(target_side, 'top')

            fallback_vertical = ['top', 'bottom']
            if preferred in allowed:
                chosen = preferred
            else:
                usage_key = (subgroup_id, target_side)
                used = subgroup_anchor_usage.get(usage_key, 0)
                usable = [a for a in fallback_vertical if a in allowed] or allowed
                chosen = usable[min(used, len(usable) - 1)]
                subgroup_anchor_usage[usage_key] = used + 1

            mapping = {
                'top': {'exitX': '0.5', 'exitY': '0', 'exitPerimeter': '1'},
                'bottom': {'exitX': '0.5', 'exitY': '1', 'exitPerimeter': '1'},
                'left': {'exitX': '0', 'exitY': '0.5', 'exitPerimeter': '1'},
                'right': {'exitX': '1', 'exitY': '0.5', 'exitPerimeter': '1'},
            }
            return mapping.get(chosen)

        def entry_for_side(side: str) -> Optional[Dict[str, str]]:
            mapping = {
                'top': {'entryX': '0.5', 'entryY': '1', 'entryPerimeter': '1'},
                'bottom': {'entryX': '0.5', 'entryY': '0', 'entryPerimeter': '1'},
                'left': {'entryX': '1', 'entryY': '0.5', 'entryPerimeter': '1'},
                'right': {'entryX': '0', 'entryY': '0.5', 'entryPerimeter': '1'},
            }
            return mapping.get(side)

        for rel in relations:
            # Composition is used to define containment here; do not render it as a visible edge.
            if rel['type'] == 'Composition' and rel['source'] == hub['id'] and rel['target'] in child_ids:
                continue
            from_id = rel['source']
            to_id = rel['target']
            style_overrides = {}
            if standardize_to_group and rel['type'] != 'Composition':
                from_id = subgroup_container_by_child.get(from_id, from_id)
                to_id = subgroup_container_by_child.get(to_id, to_id)
                if from_id in subgroup_meta and to_id not in subgroup_meta:
                    target_elem = elements_by_id.get(rel['target'])
                    target_side = (target_elem or {}).get('properties', {}).get(spoke_side_prop, '').strip().lower()
                    style_overrides.update(anchor_for_subgroup(from_id, target_side) or {})
                    style_overrides.update(entry_for_side(target_side) or {})
                elif from_id not in subgroup_meta and to_id in subgroup_meta:
                    source_elem = elements_by_id.get(rel['source'])
                    source_side = (source_elem or {}).get('properties', {}).get(spoke_side_prop, '').strip().lower()
                    style_overrides.update(entry_for_side(source_side) or {})
            edge_key = (from_id, to_id, rel['type'], rel.get('label', ''))
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)
            drawio_edges.append(DrawIOEdge(
                from_id=from_id,
                to_id=to_id,
                label=self._edge_label(rel, elements_by_id),
                edge_type=rel['type'],
                style_overrides=style_overrides or None
            ))

        xml_output = exporter.export(
            elements=drawio_elements,
            edges=drawio_edges,
            containers=containers,
            view_name=view_name
        )

        if annotations:
            xml_output = self._embed_annotations_in_drawio(xml_output, annotations, elem_positions)
        text_boxes = layout.get('text_boxes', [])
        if text_boxes:
            xml_output = self._embed_text_boxes_in_drawio(xml_output, text_boxes)

        bottom_y = max(
            [hub_y + hub_height] +
            [pos['y'] + 80 for pos in elem_positions.values()]
        ) + 40
        narrative = self._generate_narrative(view_name, elements, [], relations, intent)
        return self._embed_narrative_in_drawio(xml_output, narrative, bottom_y)

    def _generate_drawio_flow_left_right(self, view_name: str, elements: List[Dict],
                                         relations: List[Dict], layout: Dict,
                                         annotations: Optional[List[Dict]] = None,
                                         intent: Optional[Dict] = None) -> str:
        """Generate deterministic left-to-right flowchart layout with stage columns."""
        exporter = DrawIOExporter()
        elements_by_id = {e['id']: e for e in elements}
        stage_prop = layout.get('stage_property', 'Stage')
        section_prop = layout.get('section_property')
        sections_config = layout.get('sections', [])
        stage_order = layout.get('stage_order', [])
        stage_width = layout.get('stage_width', 260)
        stage_gap = layout.get('stage_gap', 80)
        node_gap = layout.get('node_gap', 40)
        start_x = layout.get('start_x', 80)
        start_y = layout.get('start_y', 80)
        section_gap = layout.get('section_gap', 120)
        order_prop = layout.get('order_property')
        include_narrative = layout.get('include_narrative', False)
        edge_label_mode = layout.get('edge_label_mode', 'on_edge')
        containers = []
        drawio_elements = []
        elem_positions = {}
        max_container_bottom = start_y

        def sort_key(elem: Dict[str, Any]) -> Tuple[int, str]:
            raw = elem.get('properties', {}).get(order_prop, '')
            try:
                order_value = int(str(raw).strip())
            except (TypeError, ValueError):
                order_value = 9999
            return (order_value, elem['display_name'].lower())

        if section_prop:
            configured_sections = [s for s in sections_config if s.get('name')]
            configured_names = [s['name'] for s in configured_sections]
            discovered_names = []
            for elem in elements:
                section_name = elem.get('properties', {}).get(section_prop)
                if section_name and section_name not in discovered_names and section_name not in configured_names:
                    discovered_names.append(section_name)
            section_names = configured_names + discovered_names
        else:
            section_names = [None]

        for section_index, section_name in enumerate(section_names):
            section_cfg = next((s for s in sections_config if s.get('name') == section_name), {})
            section_y = int(section_cfg.get('y', start_y + section_index * (420 + section_gap)))

            section_elements = [
                elem for elem in elements
                if (section_name is None or elem.get('properties', {}).get(section_prop) == section_name)
            ]
            section_element_ids = {elem['id'] for elem in section_elements}
            section_relations = [
                rel for rel in relations
                if rel.get('source') in section_element_ids and rel.get('target') in section_element_ids
            ]

            stages = {}
            for elem in section_elements:
                stage = elem.get('properties', {}).get(stage_prop, '_ungrouped')
                stages.setdefault(stage, []).append(elem)

            ordered_stages = [s for s in stage_order if s in stages] + [s for s in stages.keys() if s not in stage_order]

            for idx, stage in enumerate(ordered_stages):
                stage_elems = stages[stage]
                if order_prop:
                    stage_elems = sorted(stage_elems, key=sort_key)
                container_x = start_x + idx * (stage_width + stage_gap)
                container_y = section_y
                container_height = 70 + len(stage_elems) * 80 + max(0, len(stage_elems) - 1) * node_gap

                container_id = f"stage-{section_index}-{idx}"
                containers.append(DrawIOContainer(
                    id=container_id,
                    label=stage,
                    x=container_x,
                    y=container_y,
                    width=stage_width,
                    height=container_height,
                    style="swimlane;startSize=32;fillColor=#FAFAFA;strokeColor=#9E9E9E;fontStyle=1;"
                ))

                inner_y = 42
                for elem in stage_elems:
                    node_width = min(elem.get('width', 180), stage_width - 30)
                    node_x = int((stage_width - node_width) / 2)
                    drawio_elements.append(DrawIOElement(
                        id=elem['id'],
                        name=elem.get('display_name', elem['name']),
                        x=node_x,
                        y=inner_y,
                        width=node_width,
                        height=60,
                        elem_type=elem['type'],
                        parent_id=container_id,
                        color=elem.get('color', '#B5D4E8'),
                        emphasis=elem.get('emphasis', 'normal')
                    ))
                    elem_positions[elem['id']] = {
                        'x': container_x + node_x,
                        'y': container_y + inner_y,
                        'width': node_width
                    }
                    inner_y += 60 + node_gap

                max_container_bottom = max(max_container_bottom, container_y + container_height)

            for rel in section_relations:
                rel['_section_name'] = section_name

        drawio_edges = []
        edge_label_boxes = []
        seen_edges = set()
        for rel in relations:
            source_id = rel.get('source')
            target_id = rel.get('target')
            if source_id in elements_by_id and target_id in elements_by_id:
                if section_prop:
                    source_section = elements_by_id[source_id].get('properties', {}).get(section_prop)
                    target_section = elements_by_id[target_id].get('properties', {}).get(section_prop)
                    if source_section != target_section:
                        continue
                edge_key = (source_id, target_id, rel.get('type', ''), rel.get('label', ''))
                if edge_key in seen_edges:
                    continue
                seen_edges.add(edge_key)
                label = self._edge_label(rel, elements_by_id)
                if label and edge_label_mode == 'near_source':
                    source_pos = elem_positions.get(source_id)
                    if source_pos:
                        edge_label_boxes.append({
                            'x': source_pos['x'] + source_pos['width'] + 8,
                            'y': source_pos['y'] + 20,
                            'width': max(70, len(label) * 7),
                            'height': 20,
                            'text': label,
                            'style_kind': 'edge_label'
                        })
                    label = ''
                drawio_edges.append(DrawIOEdge(
                    from_id=source_id,
                    to_id=target_id,
                    label=label,
                    edge_type=rel.get('type', 'Flow'),
                    style_overrides={
                        'exitX': '1', 'exitY': '0.5', 'exitPerimeter': '1',
                        'entryX': '0', 'entryY': '0.5', 'entryPerimeter': '1'
                    }
                ))

        xml_output = exporter.export(
            elements=drawio_elements,
            edges=drawio_edges,
            containers=containers,
            view_name=view_name
        )

        if annotations:
            xml_output = self._embed_annotations_in_drawio(xml_output, annotations, elem_positions)

        text_boxes = layout.get('text_boxes', [])
        if text_boxes:
            xml_output = self._embed_text_boxes_in_drawio(xml_output, text_boxes)
        if edge_label_boxes:
            xml_output = self._embed_text_boxes_in_drawio(xml_output, edge_label_boxes)

        if include_narrative:
            narrative = self._generate_narrative(view_name, elements, [], relations, intent)
            return self._embed_narrative_in_drawio(xml_output, narrative, max_container_bottom + 80)
        return xml_output

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

    def _embed_text_boxes_in_drawio(self, xml_output: str, text_boxes: List[Dict[str, Any]]) -> str:
        """Embed explicit text boxes in draw.io XML."""
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(xml_output)
            root_elem = root.find(".//root")
            if root_elem is None:
                return xml_output

            for idx, box in enumerate(text_boxes):
                text = box.get('text', '')
                if not text:
                    continue
                style_kind = box.get('style_kind', 'default')
                is_html = box.get('html', False)
                box_key = f"{idx}|{box.get('x', 50)}|{box.get('y', 50)}|{box.get('width', 320)}|{box.get('height', 180)}|{style_kind}|{text}"
                box_id = hashlib.md5(box_key.encode('utf-8')).hexdigest()[:10]

                cell = ET.Element('mxCell')
                cell.set('id', f'textbox-{box_id}')
                cell.set('value', text if is_html else text.replace('\n', '&#10;'))
                cell.set('vertex', '1')
                cell.set('parent', '1')
                if style_kind == 'edge_label':
                    cell.set('style', 'text;html=1;align=left;verticalAlign=middle;whiteSpace=wrap;overflow=hidden;'
                                      'fontSize=10;fontStyle=1;fillColor=none;strokeColor=none;spacing=2;')
                elif style_kind == 'title':
                    cell.set('style', 'text;html=1;align=left;verticalAlign=middle;whiteSpace=wrap;overflow=hidden;'
                                      'fontSize=24;fontStyle=1;fillColor=none;strokeColor=none;spacing=2;')
                else:
                    cell.set('style', 'text;html=1;align=left;verticalAlign=top;whiteSpace=wrap;overflow=hidden;'
                                      'fontSize=11;fillColor=#FFF8E1;strokeColor=#D6B656;rounded=1;spacing=6;')

                geometry = ET.SubElement(cell, 'mxGeometry')
                geometry.set('x', str(box.get('x', 50)))
                geometry.set('y', str(box.get('y', 50)))
                geometry.set('width', str(box.get('width', 320)))
                geometry.set('height', str(box.get('height', 180)))
                geometry.set('as', 'geometry')
                root_elem.append(cell)

            xml_str = ET.tostring(root, encoding='unicode')
            return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
        except Exception as e:
            print(f"Failed to embed text boxes: {e}")
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
        elements_by_id = {e['id']: e for e in elements}

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
                        label=self._edge_label(rel, elements_by_id),
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
        MVP9: Write diagram-only elements to diagram_elements.csv and their properties to diagram_properties.csv.

        IMPORTANT: Only writes elements that are NOT in the official elements.csv.
        This prevents duplication - official elements stay in elements.csv,
        diagram-only (synthetic) elements go to diagram_elements.csv.

        Args:
            enriched_elements: List of enriched element dicts with properties and overrides applied
        """
        # Load official element IDs from elements.csv to avoid duplicating them
        official_ids = set()
        official_elements_file = self.archi_dir / "elements.csv"
        if official_elements_file.exists():
            with open(official_elements_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    official_ids.add(row['ID'])

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

            # Skip elements that exist in official elements.csv (avoid duplication)
            if elem_id in official_ids:
                continue

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
                        'ID': elem_id,
                        'Key': prop_name,
                        'Value': str(prop_value) if prop_value else ''
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
                writer = csv.DictWriter(f, fieldnames=['ID', 'Key', 'Value'])
                # Only write header if file is new/empty
                if diagram_properties_file.stat().st_size == 0 or not diagram_properties_file.exists():
                    writer.writeheader()
                writer.writerows(new_properties)

    def _write_output(self, spec_path: str, content: str, extension: str) -> Path:
        """Write generated content to file, preserving folder structure from ea_inputs/views/."""
        base_output_dir = Path("ea_diagrams")
        spec_path_obj = Path(spec_path)

        # Check if spec is under ea_inputs/views/ and preserve folder structure
        views_base = Path("ea_inputs/views")
        try:
            relative_path = spec_path_obj.relative_to(views_base)
            # Preserve folder structure: ea_inputs/views/commercial/foo.yaml -> ea_diagrams/commercial/foo.drawio
            output_path = base_output_dir / relative_path.parent / f"{spec_path_obj.stem}.{extension}"
        except ValueError:
            # spec_path is not under ea_inputs/views/, use flat structure
            output_path = base_output_dir / f"{spec_path_obj.stem}.{extension}"

        # Create parent directories if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

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

    def _shrink_containers_to_fit(self, xml_output: str) -> str:
        """
        Post-process AI-generated XML to shrink containers to fit their content.

        The AI often generates containers with excessive height. This function:
        1. Finds all containers (swimlanes)
        2. Groups containers into rows (based on similar Y positions)
        3. Calculates the actual content bounds for each
        4. Shrinks container heights and aligns rows
        5. Repositions orphan elements (not in containers) to follow containers
        """
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(xml_output)
            root_elem = root.find(".//root")
            if root_elem is None:
                return xml_output

            # Index all cells by ID and find parent-child relationships
            cells_by_id = {}
            children_by_parent = {}

            for cell in root_elem.findall('mxCell'):
                cell_id = cell.get('id')
                cells_by_id[cell_id] = cell

                parent_id = cell.get('parent')
                if parent_id:
                    if parent_id not in children_by_parent:
                        children_by_parent[parent_id] = []
                    children_by_parent[parent_id].append(cell)

            # Find containers (swimlanes) and calculate their required heights
            containers = []
            container_ids = set()
            for cell_id, cell in cells_by_id.items():
                style = cell.get('style', '')
                if 'swimlane' in style and cell.get('vertex') == '1':
                    geom = cell.find('mxGeometry')
                    if geom is not None:
                        containers.append({
                            'cell': cell,
                            'id': cell_id,
                            'geom': geom,
                            'x': float(geom.get('x', 0)),
                            'y': float(geom.get('y', 0)),
                            'original_height': float(geom.get('height', 200))
                        })
                        container_ids.add(cell_id)

            # Calculate required height for each container based on children
            padding_bottom = 30  # Bottom padding

            for container in containers:
                container_id = container['id']
                children = children_by_parent.get(container_id, [])

                max_bottom = 0
                for child in children:
                    child_geom = child.find('mxGeometry')
                    if child_geom is not None:
                        child_y = float(child_geom.get('y', 0))
                        child_height = float(child_geom.get('height', 60))
                        max_bottom = max(max_bottom, child_y + child_height)

                # Calculate required height
                if max_bottom > 0:
                    required_height = max_bottom + padding_bottom
                else:
                    required_height = 100  # Minimum for empty containers

                container['required_height'] = max(required_height, 100)

            # Group containers into rows based on similar Y positions (within 200px threshold)
            # This preserves horizontal (2-abreast) arrangements
            rows = []
            y_threshold = 200  # Containers within 200px Y are considered same row

            for container in sorted(containers, key=lambda c: (c['y'], c['x'])):
                placed = False
                for row in rows:
                    # Check if this container belongs to an existing row
                    row_y = row[0]['y']
                    if abs(container['y'] - row_y) < y_threshold:
                        row.append(container)
                        placed = True
                        break
                if not placed:
                    rows.append([container])

            # Sort containers within each row by X position (left to right)
            for row in rows:
                row.sort(key=lambda c: c['x'])

            # Reposition rows vertically, preserving horizontal positions within rows
            current_y = 50  # Start Y position
            gap_between_rows = 40  # Gap between rows

            for row in rows:
                # Find max required height in this row
                max_row_height = max(c['required_height'] for c in row)

                # Update all containers in this row
                for container in row:
                    geom = container['geom']
                    # Keep original X position, update Y and height
                    geom.set('y', str(int(current_y)))
                    geom.set('height', str(int(max_row_height)))

                current_y += max_row_height + gap_between_rows

            # Find orphan elements (parent="1", vertex="1", not containers, not narrative)
            orphan_elements = []
            for cell in children_by_parent.get('1', []):
                cell_id = cell.get('id', '')
                style = cell.get('style', '')
                # Skip containers, narrative textboxes, and non-vertex cells
                if cell_id in container_ids:
                    continue
                if 'narrative' in cell_id or 'text;' in style:
                    continue
                if cell.get('vertex') != '1':
                    continue
                geom = cell.find('mxGeometry')
                if geom is not None:
                    orphan_elements.append({
                        'cell': cell,
                        'geom': geom,
                        'y': float(geom.get('y', 0))
                    })

            # If there are orphan elements, position them after the last row
            if orphan_elements:
                orphan_elements.sort(key=lambda e: e['y'])
                orphan_start_y = current_y
                orphan_x = 50
                orphan_spacing = 80

                for i, orphan in enumerate(orphan_elements):
                    geom = orphan['geom']
                    new_y = orphan_start_y + (i * orphan_spacing)
                    geom.set('y', str(int(new_y)))
                    geom.set('x', str(int(orphan_x)))

            xml_str = ET.tostring(root, encoding='unicode')
            return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str

        except Exception as e:
            print(f"Failed to shrink containers: {e}")
            return xml_output

    def _get_diagram_bottom_y(self, xml_output: str) -> int:
        """
        Calculate the bottom Y coordinate of all diagram elements.
        Used to position the narrative textbox below all content.
        """
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(xml_output)
            max_bottom = 500  # Default minimum

            for cell in root.findall(".//mxCell"):
                geom = cell.find('mxGeometry')
                if geom is not None:
                    y = float(geom.get('y', 0))
                    height = float(geom.get('height', 0))
                    # Only consider absolute positioned elements (parent="1")
                    if cell.get('parent') == '1':
                        max_bottom = max(max_bottom, y + height)

            return int(max_bottom)

        except Exception:
            return 500  # Fallback


def generate_diagram(spec_path: str) -> Dict[str, Any]:
    """
    Generate diagram from YAML spec (convenience function).

    Args:
        spec_path: Path to YAML view spec

    Returns:
        Dict with generated content and metadata
    """
    generator = DrawIOGenerator()
    return generator.generate(spec_path)
