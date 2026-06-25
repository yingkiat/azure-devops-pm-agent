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
import html
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import hashlib

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

    APP_INVENTORY_KIND_TYPE = {
        "external": "BusinessActor",
        "frontend": "ApplicationInterface",
        "api": "ApplicationService",
        "secret_store": "TechnologyService",
        "data_store": "DataObject",
        "storage": "Artifact",
        "other": "ApplicationComponent",
    }
    APP_INVENTORY_KIND_COLOR = {
        "external": "#F5F5F5",
        "frontend": "#B5D4E8",
        "api": "#C9E7CB",
        "secret_store": "#FFE0B2",
        "data_store": "#F2D1C9",
        "storage": "#D7CCC8",
        "other": "#B3B3B3",
    }

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

        if spec.get('type') == 'azure_diagram':
            from .drawio_azure_generator import DrawIOAzureGenerator
            return DrawIOAzureGenerator(
                archi_dir=str(self.archi_dir),
                views_dir=str(self.views_dir),
            ).generate(spec_path)

        if spec.get('type') == 'app_inventory':
            return self._generate_app_inventory_from_spec(spec_path, spec)

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

    def _generate_app_inventory_from_spec(self, spec_path: str, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Generate draw.io output for a YAML spec with type: app_inventory."""
        inventory_ref = spec.get('inventory')
        if not inventory_ref:
            return {'error': "app_inventory spec requires an 'inventory' path"}

        inventory_path = self._resolve_app_inventory_path(inventory_ref)
        if not inventory_path.exists():
            return {'error': f'Inventory file not found: {inventory_path}'}

        inventory = json.loads(inventory_path.read_text(encoding='utf-8'))
        view_name = spec.get('view', {}).get('name') or self._app_inventory_view_name(inventory)
        drawio_xml = self.generate_app_inventory_drawio(inventory, view_name=view_name)
        output_path = self._write_output(spec_path, drawio_xml, 'drawio')

        app_map = inventory.get('application_map', {}) or {}
        return {
            'view_name': view_name,
            'element_count': len(app_map.get('nodes', [])),
            'relationship_count': len(app_map.get('edges', [])),
            'output_files': [str(output_path)],
        }

    def generate_app_inventory_drawio(self, inventory: Dict[str, Any], view_name: Optional[str] = None) -> str:
        """Generate roadmap-style draw.io XML from an app-inventory JSON document."""
        app_map = inventory.get('application_map', {}) or {}
        nodes = app_map.get('nodes', []) or []
        edges = app_map.get('edges', []) or []
        view_name = view_name or self._app_inventory_view_name(inventory)

        groups = self._app_inventory_groups(app_map, nodes)
        elements, id_map = self._build_app_inventory_elements(
            nodes,
            groups,
            components=inventory.get('components', []) or [],
            build_outputs=inventory.get('build_outputs', []) or [],
        )
        relations = self._build_app_inventory_relations(edges, id_map)

        layout = {
            'stage_property': 'Stage',
            'stage_order': [group['label'] for group in groups],
            'stage_columns': self._app_inventory_stage_columns(groups),
            'order_property': 'Sequence',
            'stage_width': int(app_map.get('stage_width', 330)),
            'stage_gap': 45,
            'node_gap': 28,
            'node_note_gap': 6,
            'stacked_stage_gap': 26,
            'start_x': 60,
            'start_y': 90,
            'edge_label_mode': 'near_target',
            'include_narrative': False,
            'text_boxes': [{
                'x': 60,
                'y': 24,
                'width': 900,
                'height': 38,
                'style_kind': 'title',
                'text': view_name,
            }],
        }

        return self._generate_drawio_flow_left_right(view_name, elements, relations, layout)

    def _app_inventory_groups(self, app_map: Dict[str, Any], nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Return explicit app architecture groups in display order."""
        configured_groups = app_map.get('groups') or []
        groups = []
        seen_ids = set()
        for index, group in enumerate(configured_groups):
            group_id = str(group.get('id') or group.get('name') or group.get('label') or f'group-{index + 1}')
            if group_id in seen_ids:
                continue
            seen_ids.add(group_id)
            groups.append({
                'id': group_id,
                'label': str(group.get('label') or group.get('name') or group_id),
                'order': group.get('order', index + 1),
            })

        explicit_node_groups = []
        for node in nodes:
            group_id = self._app_inventory_node_group_id(node)
            if group_id and group_id not in seen_ids and group_id not in explicit_node_groups:
                explicit_node_groups.append(group_id)

        for group_id in explicit_node_groups:
            groups.append({
                'id': group_id,
                'label': group_id,
                'order': len(groups) + 1,
            })

        if not groups:
            groups.append({'id': 'ungrouped', 'label': 'Ungrouped', 'order': 1})

        return sorted(groups, key=lambda g: (self._safe_int(g.get('order'), 9999), g['label'].lower()))

    @staticmethod
    def _app_inventory_stage_columns(groups: List[Dict[str, Any]]) -> List[List[str]]:
        """Map explicit app groups to the app-architecture column layout."""
        explicit_slots = ['integration', 'frontend', 'backend']
        normalized_by_group = {}
        for group in groups:
            for value in (group.get('id'), group.get('label'), group.get('name')):
                normalized = re.sub(r'[^a-z0-9]+', '', str(value or '').lower())
                if normalized and normalized not in normalized_by_group:
                    normalized_by_group[normalized] = group

        columns: List[List[str]] = []
        assigned_labels = set()
        for slot in explicit_slots:
            group = normalized_by_group.get(slot)
            if group:
                label = str(group['label'])
                columns.append([label])
                assigned_labels.add(label)

        remaining_labels = [
            str(group['label'])
            for group in groups
            if str(group['label']) not in assigned_labels
        ]
        if remaining_labels:
            columns.append(remaining_labels)

        return columns

    def _build_app_inventory_elements(
        self,
        nodes: List[Dict[str, Any]],
        groups: List[Dict[str, Any]],
        components: List[Dict[str, Any]],
        build_outputs: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
        id_map: Dict[str, str] = {}
        used_ids = set()
        elements: List[Dict[str, Any]] = []
        group_label_by_id = {group['id']: group['label'] for group in groups}
        component_by_id = {str(component.get('id')): component for component in components if component.get('id')}
        build_outputs_by_component: Dict[str, List[Dict[str, Any]]] = {}
        for output in build_outputs:
            component_id = str(output.get('component') or '')
            if component_id:
                build_outputs_by_component.setdefault(component_id, []).append(output)

        for index, node in enumerate(nodes):
            source_id = str(node.get('id') or f'node-{index + 1}')
            elem_id = self._safe_app_inventory_id(source_id, used_ids)
            id_map[source_id] = elem_id

            kind = str(node.get('kind') or 'other')
            group_id = self._app_inventory_node_group_id(node) or 'ungrouped'
            stage = group_label_by_id.get(group_id, group_id)
            label = self._app_inventory_node_label(node)
            note_text = self._app_inventory_node_detail_line(node)
            component_id = str(node.get('component') or '')
            component = component_by_id.get(component_id, {})
            metadata = self._app_inventory_node_metadata(
                node=node,
                component=component,
                build_outputs=build_outputs_by_component.get(component_id, []),
                element_id=elem_id,
                group_label=stage,
                source_id=source_id,
            )

            elements.append({
                'id': elem_id,
                'type': self.APP_INVENTORY_KIND_TYPE.get(kind, self.APP_INVENTORY_KIND_TYPE['other']),
                'name': label,
                'display_name': label,
                'documentation': node.get('summary', ''),
                'layer': 'Application',
                'color': self.APP_INVENTORY_KIND_COLOR.get(kind, self.APP_INVENTORY_KIND_COLOR['other']),
                'width': 240,
                'height': 60,
                'note_text': note_text,
                'note_height': 24,
                'properties': {
                    'Stage': stage,
                    'Sequence': str(index + 1),
                    'Kind': kind,
                    'Source ID': source_id,
                    'Summary': str(node.get('summary') or ''),
                    'Metrics': self._app_inventory_metrics_line(node.get('metrics')),
                },
                'emphasis': 'normal',
                'emphasis_role': '',
                'metadata': metadata,
            })

        return elements, id_map

    @staticmethod
    def _app_inventory_node_group_id(node: Dict[str, Any]) -> str:
        return str(
            node.get('group')
            or node.get('group_id')
            or node.get('architecture_group')
            or node.get('architectureGroup')
            or ''
        )

    def _app_inventory_node_metadata(
        self,
        node: Dict[str, Any],
        component: Dict[str, Any],
        build_outputs: List[Dict[str, Any]],
        element_id: str,
        group_label: str,
        source_id: str,
    ) -> Dict[str, Any]:
        properties = {
            'Source ID': source_id,
            'Architecture Group': group_label,
        }
        self._copy_metadata_value(properties, 'Kind', node.get('kind'))
        self._copy_metadata_value(properties, 'Summary', node.get('summary'))
        self._copy_metadata_value(properties, 'Component', node.get('component'))
        self._copy_metadata_value(properties, 'Infra Refs', node.get('infra_refs') or node.get('infra_ref'))

        for key, value in (node.get('metrics') or {}).items():
            self._copy_metadata_value(properties, f'Metric: {str(key).replace("_", " ").title()}', value)

        if component:
            self._copy_metadata_value(properties, 'Component Name', component.get('name'))
            self._copy_metadata_value(properties, 'Component Type', component.get('type'))
            self._copy_metadata_value(properties, 'Component Path', component.get('path'))
            self._copy_metadata_value(properties, 'Depends On', component.get('dependsOn'))
            self._copy_metadata_value(properties, 'Uses Infra', component.get('uses_infra'))
            self._copy_metadata_value(properties, 'Component Summary', component.get('summary'))

        for idx, output in enumerate(build_outputs, start=1):
            prefix = f'Build Output {idx}'
            self._copy_metadata_value(properties, f'{prefix} Kind', output.get('kind'))
            self._copy_metadata_value(properties, f'{prefix} Image', output.get('image'))
            self._copy_metadata_value(properties, f'{prefix} Package', output.get('package'))
            self._copy_metadata_value(properties, f'{prefix} Runtime', output.get('runtime'))
            self._copy_metadata_value(properties, f'{prefix} Base Image', output.get('base_image'))

        for key, value in (node.get('metadata') or {}).items():
            self._copy_metadata_value(properties, key, value)

        return {
            'id': element_id,
            'name': str(node.get('label') or node.get('id') or 'Component'),
            'type': self.APP_INVENTORY_KIND_TYPE.get(str(node.get('kind') or 'other'), self.APP_INVENTORY_KIND_TYPE['other']),
            'documentation': str(node.get('summary') or component.get('summary') or ''),
            'properties': properties,
        }

    @staticmethod
    def _copy_metadata_value(properties: Dict[str, str], key: str, value: Any) -> None:
        if value in (None, ''):
            return
        if isinstance(value, (list, dict)):
            properties[key] = json.dumps(value, ensure_ascii=True, sort_keys=True)
        else:
            properties[key] = str(value)

    @staticmethod
    def _safe_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _build_app_inventory_relations(self, edges: List[Dict[str, Any]], id_map: Dict[str, str]) -> List[Dict[str, Any]]:
        relations: List[Dict[str, Any]] = []
        for index, edge in enumerate(edges):
            source = id_map.get(str(edge.get('from') or ''))
            target = id_map.get(str(edge.get('to') or ''))
            if not source or not target:
                continue

            relations.append({
                'id': f'app-rel-{index + 1}',
                'type': 'Flow',
                'source': source,
                'target': target,
                'label': str(edge.get('label') or ''),
                'documentation': self._app_inventory_metrics_line(edge.get('metrics')),
            })
        return relations

    @staticmethod
    def _resolve_app_inventory_path(inventory_ref: str) -> Path:
        path = Path(inventory_ref)
        if path.exists():
            return path
        return Path('ea_inputs') / inventory_ref

    @staticmethod
    def _app_inventory_view_name(inventory: Dict[str, Any]) -> str:
        app_name = inventory.get('application') or inventory.get('project') or 'Application'
        env = inventory.get('environment')
        suffix = f' ({env})' if env else ''
        return f'{app_name} - Application Architecture{suffix}'

    @staticmethod
    def _safe_app_inventory_id(source_id: str, used_ids: set) -> str:
        candidate = re.sub(r'[^A-Za-z0-9_.-]+', '-', source_id).strip('-._')
        if not candidate or not re.match(r'^[A-Za-z]', candidate):
            candidate = f'app-{candidate or "node"}'
        candidate = f'diagram-{candidate}'

        base = candidate
        if candidate in used_ids:
            digest = hashlib.md5(source_id.encode('utf-8')).hexdigest()[:8]
            candidate = f'{base}-{digest}'
            counter = 2
            while candidate in used_ids:
                candidate = f'{base}-{digest}-{counter}'
                counter += 1

        used_ids.add(candidate)
        return candidate

    @classmethod
    def _app_inventory_node_label(cls, node: Dict[str, Any]) -> str:
        return html.escape(str(node.get('label') or node.get('id') or 'Component'))

    @classmethod
    def _app_inventory_node_detail_line(cls, node: Dict[str, Any]) -> str:
        explicit = node.get('display_line') or node.get('displayLine')
        if explicit not in (None, ''):
            return str(explicit).strip()

        detail_parts = []
        summary = str(node.get('summary') or '').strip()
        metrics = cls._app_inventory_metrics_line(node.get('metrics'))
        if summary:
            detail_parts.append(summary)
        if metrics:
            detail_parts.append(metrics)

        return ' | '.join(detail_parts)

    @staticmethod
    def _app_inventory_metrics_line(metrics: Optional[Dict[str, Any]]) -> str:
        if not metrics:
            return ''
        parts = []
        for key, value in list(metrics.items())[:3]:
            label = str(key).replace('_', ' ')
            parts.append(f'{label}: {value}')
        return ' | '.join(parts)

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

    @staticmethod
    def _should_render_edge_labels(layout: Dict[str, Any], default: bool = True) -> bool:
        """Return whether visible edge labels should be rendered for a layout."""
        suppress = layout.get('suppress_edge_labels')
        if suppress is not None:
            return not suppress
        return default

    @staticmethod
    def _expand_text_boxes(text_boxes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Expand higher-level text box configs into plain draw.io text boxes."""
        expanded_boxes: List[Dict[str, Any]] = []

        for box in text_boxes:
            if box.get('kind') != 'stacked_lines':
                expanded_boxes.append(box)
                continue

            default_x = box.get('x', 50)
            default_y = box.get('y', 50)
            header_height = box.get('header_height', 28)
            line_height = box.get('line_height', 24)
            line_gap = box.get('line_gap', 6)

            header_text = box.get('header_text', '')
            if header_text:
                expanded_boxes.append({
                    'x': box.get('header_x', default_x),
                    'y': box.get('header_y', default_y),
                    'width': box.get('header_width', box.get('width', 150)),
                    'height': header_height,
                    'style_kind': box.get('header_style_kind', 'note_header'),
                    'text': header_text,
                    'html': box.get('header_html', False),
                })

            line_x = box.get('line_x', default_x)
            line_y = box.get('line_y', default_y + header_height + line_gap)
            line_width = box.get('line_width', box.get('width', 320))
            line_style_kind = box.get('line_style_kind', 'note_line')

            for idx, line in enumerate(box.get('lines', [])):
                default_line_box = {
                    'x': line_x,
                    'y': line_y + (idx * (line_height + line_gap)),
                    'width': line_width,
                    'height': line_height,
                    'style_kind': line_style_kind,
                    'html': False,
                }

                if isinstance(line, dict):
                    line_box = {
                        **default_line_box,
                        **line,
                    }
                else:
                    line_box = {
                        **default_line_box,
                        'text': str(line),
                    }

                if line_box.get('text'):
                    expanded_boxes.append(line_box)

        return expanded_boxes

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

            # Find children based on relationship direction while preserving relationship order.
            children_ids = []
            seen_child_ids = set()
            if direction == 'inbound':
                # Children point TO parent (e.g., App -Serving-> Capability)
                # So parent is target, children are sources
                for rel in relation_pool:
                    if rel['target'] == parent_id:
                        if not relationship_type or rel['type'] == relationship_type:
                            child_elem = self.element_by_id.get(rel['source'])
                            if child_elem and child_elem['type'] == child_type:
                                if rel['source'] not in seen_child_ids:
                                    children_ids.append(rel['source'])
                                    seen_child_ids.add(rel['source'])
            else:
                # Parent points TO children (e.g., BusinessFunction -Composition-> Capability)
                # So parent is source, children are targets
                for rel in relation_pool:
                    if rel['source'] == parent_id:
                        if not relationship_type or rel['type'] == relationship_type:
                            child_elem = self.element_by_id.get(rel['target'])
                            if child_elem and child_elem['type'] == child_type:
                                if rel['target'] not in seen_child_ids:
                                    children_ids.append(rel['target'])
                                    seen_child_ids.add(rel['target'])

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
                status_value = props.get(color_by, '')
                color = get_element_color(elem, status_value)
            else:
                # Default to roadmap disposition, then lifecycle status, else layer color
                status_value = props.get('Roadmap Disposition', '') or props.get('Lifecycle Status', '')
                color = get_element_color(elem, status_value)

            explicit_width = None
            width_override = props.get('Width')
            if width_override not in (None, ''):
                try:
                    explicit_width = int(width_override)
                except (TypeError, ValueError):
                    explicit_width = None

            # MVP9: Apply emphasis treatment
            emphasis = emphasis_map.get(elem['name'].lower(), {'treatment': 'normal', 'role': ''})

            enriched.append({
                **elem,
                'display_name': props.get('Display Name', elem['name']),
                'layer': layer,
                'color': color,
                'width': explicit_width or calculate_element_width(props.get('Display Name', elem['name'])),
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
        from utils.openai_client import chat

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
                    name=elem.get('display_name', elem['name']),
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
        ordered_child_ids = [child['id'] for child in hub_entry.get('children', [])]
        child_ids = set(ordered_child_ids)
        child_by_id = {child_id: elements_by_id.get(child_id, child) for child_id, child in ((c['id'], c) for c in hub_entry.get('children', []))}
        hub_prop = layout.get('core_group_by', 'Internal Group')
        spoke_side_prop = layout.get('spoke_side_property', 'Spoke Side')

        containers = []
        drawio_elements = []
        elem_positions = {}

        center_x = layout.get('center_x', 700)
        center_y = layout.get('center_y', 260)
        hub_width = layout.get('hub_width', 560)
        requested_hub_height = layout.get('hub_height', 300)
        hub_x = center_x - (hub_width // 2)

        children = [child_by_id[cid] for cid in ordered_child_ids if cid in child_by_id]
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
        subgroup_child_top = layout.get('core_child_top', 38)
        subgroup_child_height = layout.get('core_child_height', 60)
        subgroup_child_spacing = layout.get('core_child_spacing', 24)
        subgroup_bottom_padding = layout.get('core_group_bottom_padding', 24)
        row_pitch = subgroup_child_height + subgroup_child_spacing
        group_index_by_name = {name: idx for idx, name in enumerate(ordered_group_names)}
        reserved_leading_rows = {name: 0 for name in ordered_group_names}

        for group_name in ordered_group_names:
            source_idx = group_index_by_name[group_name]
            for row_idx, child in enumerate(grouped_children[group_name]):
                span_to_group = str(child.get('properties', {}).get('Span To Group', '')).strip()
                target_idx = group_index_by_name.get(span_to_group)
                if target_idx is None or target_idx <= source_idx:
                    continue
                for covered_group in ordered_group_names[source_idx + 1:target_idx + 1]:
                    reserved_leading_rows[covered_group] = max(
                        reserved_leading_rows[covered_group],
                        row_idx + 1
                    )

        max_group_rows = max(
            (len(grouped_children[group_name]) + reserved_leading_rows.get(group_name, 0)
             for group_name in ordered_group_names),
            default=0
        )
        if max_group_rows > 0:
            subgroup_content_height = (
                subgroup_child_top +
                (max_group_rows * subgroup_child_height) +
                ((max_group_rows - 1) * subgroup_child_spacing) +
                subgroup_bottom_padding
            )
        else:
            subgroup_content_height = subgroup_child_top + subgroup_child_height + subgroup_bottom_padding
        subgroup_height = max(
            requested_hub_height - subgroup_top - subgroup_inner_margin,
            subgroup_content_height
        )
        hub_height = subgroup_top + subgroup_height + subgroup_inner_margin
        hub_y = center_y - (hub_height // 2)

        # Use the hub element id as the outer container id so future edges can target it if needed.
        containers.append(DrawIOContainer(
            id=hub['id'],
            label=hub['name'],
            x=hub_x,
            y=hub_y,
            width=hub_width,
            height=hub_height,
            style="swimlane;startSize=42;fillColor=#E3F2FD;strokeColor=#1565C0;fontStyle=1;strokeWidth=2;align=center;"
        ))
        elem_positions[hub['name'].lower()] = {'x': hub_x + 20, 'y': hub_y + 20, 'width': hub_width - 40}
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
                style="swimlane;startSize=28;fillColor=#F8FBFF;strokeColor=#90CAF9;fontStyle=1;align=center;"
            ))
            subgroup_meta[subgroup_id] = {
                'index': idx,
                'group_name': group_name
            }

            child_y = subgroup_child_top + reserved_leading_rows.get(group_name, 0) * row_pitch
            for child in grouped_children[group_name]:
                subgroup_container_by_child[child['id']] = subgroup_id
                child_props = child.get('properties', {})
                child_width = min(child.get('width', 180), subgroup_width - 24)
                child_x = int((subgroup_width - child_width) / 2)
                span_to_group = str(child_props.get('Span To Group', '')).strip()
                span_target_idx = group_index_by_name.get(span_to_group)
                if span_target_idx is not None and span_target_idx > idx:
                    span_groups = span_target_idx - idx + 1
                    span_width = (span_groups * subgroup_width) + ((span_groups - 1) * subgroup_gap)
                    child_width = min(max(child.get('width', 180), span_width - 24), span_width - 24)
                    child_x = int((span_width - child_width) / 2)
                drawio_elements.append(DrawIOElement(
                    id=child['id'],
                    name=child.get('display_name', child['name']),
                    x=child_x,
                    y=child_y,
                    width=child_width,
                    height=subgroup_child_height,
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
                child_y += subgroup_child_height + subgroup_child_spacing

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
        external_group_container_by_elem = {}
        external_side_by_id = {}
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
                    external_side_by_id[group_id] = side
                    containers.append(DrawIOContainer(
                        id=group_id,
                        label=group_name,
                        x=x,
                        y=current_y,
                        width=group_width,
                        height=group_height,
                        style="swimlane;startSize=28;fillColor=#F5F5F5;strokeColor=#9E9E9E;fontStyle=1;align=center;"
                    ))
                    inner_y = 38
                    for elem in group_elems:
                        external_group_container_by_elem[elem['id']] = group_id
                        external_side_by_id[elem['id']] = side
                        drawio_elements.append(DrawIOElement(
                            id=elem['id'],
                            name=elem.get('display_name', elem['name']),
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
                    external_side_by_id[group_id] = side
                    containers.append(DrawIOContainer(
                        id=group_id,
                        label=group_name,
                        x=current_x,
                        y=y,
                        width=group_width,
                        height=group_height,
                        style="swimlane;startSize=28;fillColor=#F5F5F5;strokeColor=#9E9E9E;fontStyle=1;align=center;"
                    ))
                    inner_x = 15
                    for elem in group_elems:
                        external_group_container_by_elem[elem['id']] = group_id
                        external_side_by_id[elem['id']] = side
                        drawio_elements.append(DrawIOElement(
                            id=elem['id'],
                            name=elem.get('display_name', elem['name']),
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
        render_edge_labels = self._should_render_edge_labels(layout, default=False)

        def anchor_for_side(side: str, prefix: str) -> Optional[Dict[str, str]]:
            mapping = {
                'top': {'X': '0.5', 'Y': '0'},
                'bottom': {'X': '0.5', 'Y': '1'},
                'left': {'X': '0', 'Y': '0.5'},
                'right': {'X': '1', 'Y': '0.5'},
            }
            coords = mapping.get(side)
            if not coords:
                return None
            return {
                f'{prefix}X': coords['X'],
                f'{prefix}Y': coords['Y'],
                f'{prefix}Perimeter': '1',
            }

        def anchor_for_subgroup(subgroup_id: str, target_side: str) -> Optional[Dict[str, str]]:
            if subgroup_id not in subgroup_meta:
                return None
            return anchor_for_side(target_side, 'exit')

        def entry_for_side(side: str) -> Optional[Dict[str, str]]:
            return anchor_for_side(side, 'entry')

        def opposite_side(side: str) -> str:
            mapping = {
                'top': 'bottom',
                'bottom': 'top',
                'left': 'right',
                'right': 'left',
            }
            return mapping.get(side, side)

        def normalize_diagram_origin(padding: int = 40) -> None:
            min_x = None
            min_y = None

            for container in containers:
                min_x = container.x if min_x is None else min(min_x, container.x)
                min_y = container.y if min_y is None else min(min_y, container.y)

            for element in drawio_elements:
                absolute_x = element.x
                absolute_y = element.y
                if element.parent_id:
                    parent_container = next((c for c in containers if c.id == element.parent_id), None)
                    while parent_container is not None:
                        absolute_x += parent_container.x
                        absolute_y += parent_container.y
                        if parent_container.parent_id:
                            parent_container = next((c for c in containers if c.id == parent_container.parent_id), None)
                        else:
                            parent_container = None
                min_x = absolute_x if min_x is None else min(min_x, absolute_x)
                min_y = absolute_y if min_y is None else min(min_y, absolute_y)

            if min_x is None or min_y is None:
                return

            shift_x = max(0, padding - min_x)
            shift_y = max(0, padding - min_y)
            if shift_x == 0 and shift_y == 0:
                return

            for container in containers:
                if not container.parent_id or container.parent_id == '1':
                    container.x += shift_x
                    container.y += shift_y

            for key, pos in elem_positions.items():
                pos['x'] += shift_x
                pos['y'] += shift_y

        normalize_diagram_origin()

        container_by_id = {container.id: container for container in containers}

        def absolute_container_bounds(container_id: str) -> Optional[Dict[str, float]]:
            container = container_by_id.get(container_id)
            if not container:
                return None
            x = float(container.x)
            y = float(container.y)
            parent_id = container.parent_id
            while parent_id and parent_id != '1':
                parent = container_by_id.get(parent_id)
                if not parent:
                    break
                x += float(parent.x)
                y += float(parent.y)
                parent_id = parent.parent_id
            return {
                'left': x,
                'right': x + float(container.width),
                'top': y,
                'bottom': y + float(container.height),
                'center_x': x + float(container.width) / 2,
                'center_y': y + float(container.height) / 2,
            }

        def edge_waypoints(from_container_id: str, to_container_id: str,
                           source_side: str, target_side: str) -> Optional[List[Tuple[int, int]]]:
            source_bounds = absolute_container_bounds(from_container_id)
            target_bounds = absolute_container_bounds(to_container_id)
            if not source_bounds or not target_bounds:
                return None

            clearance = int(layout.get('edge_clearance', 24))

            if source_side == 'top' and target_side == 'bottom':
                source_guide_y = int(source_bounds['top'] - clearance)
                target_guide_y = int(target_bounds['bottom'] + clearance)
                guide_y = int(min(source_guide_y, target_guide_y))
                return [
                    (int(source_bounds['center_x']), source_guide_y),
                    (int(source_bounds['center_x']), guide_y),
                    (int(target_bounds['center_x']), guide_y),
                    (int(target_bounds['center_x']), target_guide_y),
                ]
            if source_side == 'bottom' and target_side == 'top':
                source_guide_y = int(source_bounds['bottom'] + clearance)
                target_guide_y = int(target_bounds['top'] - clearance)
                guide_y = int(max(source_guide_y, target_guide_y))
                return [
                    (int(source_bounds['center_x']), source_guide_y),
                    (int(source_bounds['center_x']), guide_y),
                    (int(target_bounds['center_x']), guide_y),
                    (int(target_bounds['center_x']), target_guide_y),
                ]
            if source_side == 'left' and target_side == 'right':
                source_guide_x = int(source_bounds['left'] - clearance)
                target_guide_x = int(target_bounds['right'] + clearance)
                guide_x = int(min(source_guide_x, target_guide_x))
                return [
                    (source_guide_x, int(source_bounds['center_y'])),
                    (guide_x, int(source_bounds['center_y'])),
                    (guide_x, int(target_bounds['center_y'])),
                    (target_guide_x, int(target_bounds['center_y'])),
                ]
            if source_side == 'right' and target_side == 'left':
                source_guide_x = int(source_bounds['right'] + clearance)
                target_guide_x = int(target_bounds['left'] - clearance)
                guide_x = int(max(source_guide_x, target_guide_x))
                return [
                    (source_guide_x, int(source_bounds['center_y'])),
                    (guide_x, int(source_bounds['center_y'])),
                    (guide_x, int(target_bounds['center_y'])),
                    (target_guide_x, int(target_bounds['center_y'])),
                ]
            return None

        for rel in relations:
            # Composition is used to define containment here; do not render it as a visible edge.
            if rel['type'] == 'Composition' and rel['source'] == hub['id'] and rel['target'] in child_ids:
                continue
            from_id = rel['source']
            to_id = rel['target']
            style_overrides = {}
            route_waypoints = None
            if standardize_to_group and rel['type'] != 'Composition':
                from_id = subgroup_container_by_child.get(from_id, from_id)
                to_id = subgroup_container_by_child.get(to_id, to_id)
                from_id = external_group_container_by_elem.get(from_id, from_id)
                to_id = external_group_container_by_elem.get(to_id, to_id)
                if from_id in subgroup_meta and to_id not in subgroup_meta:
                    target_elem = elements_by_id.get(rel['target'])
                    target_side = external_side_by_id.get(to_id)
                    if not target_side:
                        target_side = (target_elem or {}).get('properties', {}).get(spoke_side_prop, '').strip().lower() or 'right'
                    style_overrides.update(anchor_for_subgroup(from_id, target_side) or {})
                    style_overrides.update(entry_for_side(opposite_side(target_side)) or {})
                    route_waypoints = edge_waypoints(from_id, to_id, target_side, opposite_side(target_side))
                elif from_id not in subgroup_meta and to_id in subgroup_meta:
                    source_elem = elements_by_id.get(rel['source'])
                    source_placement_side = external_side_by_id.get(from_id)
                    if not source_placement_side:
                        source_placement_side = (source_elem or {}).get('properties', {}).get(spoke_side_prop, '').strip().lower() or 'left'
                    source_side = opposite_side(source_placement_side)
                    target_side = source_placement_side
                    style_overrides.update(anchor_for_side(source_side, 'exit') or {})
                    style_overrides.update(entry_for_side(target_side) or {})
                    route_waypoints = edge_waypoints(from_id, to_id, source_side, target_side)
                elif from_id in subgroup_meta and to_id in subgroup_meta:
                    target_side = 'right' if subgroup_meta[from_id]['index'] <= subgroup_meta[to_id]['index'] else 'left'
                    source_side = opposite_side(target_side)
                    style_overrides.update(anchor_for_subgroup(from_id, target_side) or {})
                    style_overrides.update(entry_for_side(source_side) or {})
                    route_waypoints = edge_waypoints(from_id, to_id, target_side, source_side)
            if from_id == to_id:
                continue
            rendered_label = self._edge_label(rel, elements_by_id) if render_edge_labels else ''
            edge_key = (
                from_id,
                to_id,
                rel['type'],
                rendered_label,
                tuple(sorted(style_overrides.items()))
            )
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)
            drawio_edges.append(DrawIOEdge(
                from_id=from_id,
                to_id=to_id,
                label=rendered_label,
                edge_type=rel['type'],
                style_overrides=style_overrides or None,
                waypoints=route_waypoints
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
        stage_columns = layout.get('stage_columns') or []
        node_note_gap = int(layout.get('node_note_gap', 6))
        stacked_stage_gap = int(layout.get('stacked_stage_gap', 26))
        containers = []
        drawio_elements = []
        elem_positions = {}
        node_note_boxes = []
        max_container_bottom = start_y

        stage_column_index: Dict[str, int] = {}
        if stage_columns:
            for column_index, column_stages in enumerate(stage_columns):
                for stage_name in column_stages:
                    stage_column_index[str(stage_name)] = column_index

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
            if stage_columns:
                fallback_column_index = len(stage_columns)
                ordered_stages = sorted(
                    ordered_stages,
                    key=lambda stage: (
                        stage_column_index.get(stage, fallback_column_index),
                        stage_order.index(stage) if stage in stage_order else 9999,
                        stage.lower(),
                    )
                )
            column_y_offsets: Dict[int, int] = {}

            for idx, stage in enumerate(ordered_stages):
                stage_elems = stages[stage]
                if order_prop:
                    stage_elems = sorted(stage_elems, key=sort_key)
                node_heights = []
                for elem in stage_elems:
                    try:
                        node_height = int(elem.get('height', 60))
                    except (TypeError, ValueError):
                        node_height = 60
                    note_text = str(elem.get('note_text') or '').strip()
                    note_height = int(elem.get('note_height', 24)) if note_text else 0
                    node_heights.append(node_height + (node_note_gap + note_height if note_text else 0))
                column_index = stage_column_index.get(stage, idx) if stage_columns else idx
                container_x = start_x + column_index * (stage_width + stage_gap)
                container_y = column_y_offsets.get(column_index, section_y) if stage_columns else section_y
                container_height = (
                    70
                    + sum(height + 20 for height in node_heights)
                    + max(0, len(stage_elems) - 1) * node_gap
                )

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
                    try:
                        node_height = int(elem.get('height', 60))
                    except (TypeError, ValueError):
                        node_height = 60
                    node_x = int((stage_width - node_width) / 2)
                    note_text = str(elem.get('note_text') or '').strip()
                    note_height = int(elem.get('note_height', 24)) if note_text else 0
                    drawio_elements.append(DrawIOElement(
                        id=elem['id'],
                        name=elem.get('display_name', elem['name']),
                        x=node_x,
                        y=inner_y,
                        width=node_width,
                        height=node_height,
                        elem_type=elem['type'],
                        parent_id=container_id,
                        color=elem.get('color', '#B5D4E8'),
                        emphasis=elem.get('emphasis', 'normal'),
                        metadata=elem.get('metadata'),
                    ))
                    elem_positions[elem['id']] = {
                        'x': container_x + node_x,
                        'y': container_y + inner_y,
                        'width': node_width,
                        'height': node_height,
                    }
                    if note_text:
                        note_width = int(elem.get('note_width', stage_width - 20))
                        node_note_boxes.append({
                            'x': container_x + int((stage_width - note_width) / 2),
                            'y': container_y + inner_y + node_height + node_note_gap,
                            'width': note_width,
                            'height': note_height,
                            'text': note_text,
                            'style_kind': 'app_node_note',
                        })
                    inner_y += node_height + (node_note_gap + note_height if note_text else 0) + node_gap

                max_container_bottom = max(max_container_bottom, container_y + container_height)
                if stage_columns:
                    column_y_offsets[column_index] = container_y + container_height + stacked_stage_gap

            for rel in section_relations:
                rel['_section_name'] = section_name

        drawio_edges = []
        edge_label_boxes = []
        seen_edges = set()
        drawable_relations = [
            rel for rel in relations
            if rel.get('source') in elements_by_id and rel.get('target') in elements_by_id
        ]
        outgoing_relations: Dict[str, List[Dict[str, Any]]] = {}
        incoming_relations: Dict[str, List[Dict[str, Any]]] = {}
        for rel in drawable_relations:
            outgoing_relations.setdefault(rel.get('source'), []).append(rel)
            incoming_relations.setdefault(rel.get('target'), []).append(rel)
        source_label_counts: Dict[str, int] = {}
        target_label_counts: Dict[str, int] = {}

        def edge_anchor_fraction(rel_list: List[Dict[str, Any]], rel: Dict[str, Any]) -> float:
            try:
                idx = rel_list.index(rel)
            except ValueError:
                idx = 0
            if len(rel_list) <= 1:
                return 0.5
            return round((idx + 1) / (len(rel_list) + 1), 2)

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
                if edge_label_mode == 'none':
                    label = ''
                elif label and edge_label_mode in ('near_source', 'near_target'):
                    label_width = max(70, len(label) * 7)
                    source_pos = elem_positions.get(source_id)
                    target_pos = elem_positions.get(target_id)
                    if edge_label_mode == 'near_source' and source_pos:
                        label_index = source_label_counts.get(source_id, 0)
                        source_label_counts[source_id] = label_index + 1
                        edge_label_boxes.append({
                            'x': source_pos['x'] + source_pos['width'] + 8,
                            'y': source_pos['y'] + 10 + (label_index * 22),
                            'width': label_width,
                            'height': 20,
                            'text': label,
                            'style_kind': 'edge_label'
                        })
                    elif edge_label_mode == 'near_target' and target_pos:
                        label_index = target_label_counts.get(target_id, 0)
                        target_label_counts[target_id] = label_index + 1
                        edge_label_boxes.append({
                            'x': max(20, target_pos['x'] - label_width - 8),
                            'y': target_pos['y'] + 10 + (label_index * 22),
                            'width': label_width,
                            'height': 20,
                            'text': label,
                            'style_kind': 'edge_label'
                        })
                    label = ''
                exit_y = edge_anchor_fraction(outgoing_relations.get(source_id, []), rel)
                entry_y = edge_anchor_fraction(incoming_relations.get(target_id, []), rel)
                drawio_edges.append(DrawIOEdge(
                    from_id=source_id,
                    to_id=target_id,
                    label=label,
                    edge_type=rel.get('type', 'Flow'),
                    style_overrides={
                        'exitX': '1', 'exitY': str(exit_y), 'exitPerimeter': '1',
                        'entryX': '0', 'entryY': str(entry_y), 'entryPerimeter': '1'
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
        if node_note_boxes:
            xml_output = self._embed_text_boxes_in_drawio(xml_output, node_note_boxes)
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
                placement = ann.get('placement', 'above')
                offset_x = int(ann.get('offset_x', 10))
                default_offset_y = 36 if placement == 'below' else 8
                offset_y = int(ann.get('offset_y', default_offset_y))

                # Find element position
                pos = elem_positions.get(near)
                if not pos:
                    # Try partial match
                    for name, p in elem_positions.items():
                        if near in name or name in near:
                            pos = p
                            break

                if pos:
                    target_x = int(pos['x'])
                    target_y = int(pos['y'])
                    target_w = int(pos.get('width', 120))
                    target_h = int(pos.get('height', 60))
                    target_id = pos.get('id')

                    ann_width = int(ann.get('width', max(135, min(240, len(text) * 7 + 22))))
                    ann_height = int(ann.get('height', 26))

                    if placement == 'right':
                        ann_x = target_x + target_w + offset_x
                        ann_y = target_y + (target_h // 2) - (ann_height // 2)
                    elif placement == 'left':
                        ann_x = target_x - ann_width - offset_x
                        ann_y = target_y + (target_h // 2) - (ann_height // 2)
                    elif placement == 'below':
                        ann_x = target_x + (target_w // 2) - (ann_width // 2)
                        ann_y = target_y + target_h + offset_y
                    else:
                        ann_x = target_x + (target_w // 2) - (ann_width // 2)
                        ann_y = target_y - ann_height - offset_y

                    textbox = ET.Element('mxCell')
                    textbox.set('id', f'ann-{idx}')
                    textbox.set('value', text)
                    textbox.set('vertex', '1')
                    textbox.set('parent', '1')
                    textbox.set('style', 'rounded=1;whiteSpace=wrap;html=1;align=left;verticalAlign=middle;'
                                        'fontSize=9;fillColor=#FFF8E1;strokeColor=#D4B106;'
                                        'spacing=6;arcSize=10;')

                    geometry = ET.SubElement(textbox, 'mxGeometry')
                    geometry.set('x', str(int(ann_x)))
                    geometry.set('y', str(int(ann_y)))
                    geometry.set('width', str(int(ann_width)))
                    geometry.set('height', str(int(ann_height)))
                    geometry.set('as', 'geometry')

                    root_elem.append(textbox)

                    if target_id and ann.get('connector', False):
                        connector = ET.Element('mxCell')
                        connector.set('id', f'ann-edge-{idx}')
                        connector.set('edge', '1')
                        connector.set('parent', '1')
                        connector.set('source', f'ann-{idx}')
                        connector.set('target', target_id)
                        connector.set('style', 'edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;'
                                               'jettySize=auto;html=1;strokeColor=#D4B106;dashed=1;'
                                               'endArrow=open;startArrow=none;fontSize=8;')

                        edge_geometry = ET.SubElement(connector, 'mxGeometry')
                        edge_geometry.set('relative', '1')
                        edge_geometry.set('as', 'geometry')
                        root_elem.append(connector)

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

            default_box_dimensions = {
                'default': {'width': 150, 'height': 28},
                'edge_label': {'width': 70, 'height': 20},
                'app_node_note': {'width': 300, 'height': 24},
                'note_header': {'width': 150, 'height': 28},
                'note_line': {'width': 320, 'height': 24},
                'title': {'width': 320, 'height': 48},
            }

            for idx, box in enumerate(self._expand_text_boxes(text_boxes)):
                text = box.get('text', '')
                if not text:
                    continue
                style_kind = box.get('style_kind', 'default')
                is_html = box.get('html', False)
                render_text = text
                render_as_html = is_html
                if not is_html and '\n' in text:
                    escaped_lines = [
                        line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        for line in text.splitlines()
                    ]
                    render_text = '<div>' + '<br/>'.join(escaped_lines) + '</div>'
                    render_as_html = True
                dims = default_box_dimensions.get(style_kind, default_box_dimensions['default'])
                width = box.get('width', dims['width'])
                height = box.get('height', dims['height'])
                auto_sized_default = (
                    style_kind == 'default' and
                    'width' not in box and
                    'height' not in box
                )
                offset_y = box.get('offset_y', 24 if auto_sized_default else 0)
                x = box.get('x', 50)
                y = box.get('y', 50) + offset_y
                box_key = f"{idx}|{x}|{y}|{width}|{height}|{style_kind}|{text}"
                box_id = hashlib.md5(box_key.encode('utf-8')).hexdigest()[:10]

                cell = ET.Element('mxCell')
                cell.set('id', f'textbox-{box_id}')
                cell.set('value', render_text)
                cell.set('vertex', '1')
                cell.set('parent', '1')
                if style_kind == 'edge_label':
                    cell.set('style', 'text;html=0;align=left;verticalAlign=middle;whiteSpace=wrap;overflow=hidden;'
                                      'fontSize=10;fontStyle=1;fillColor=none;strokeColor=none;spacing=2;')
                elif style_kind == 'app_node_note':
                    cell.set('style', 'text;html=0;align=center;verticalAlign=top;whiteSpace=wrap;overflow=hidden;'
                                      'fontSize=10;fontColor=#444444;fillColor=none;strokeColor=none;spacing=2;')
                elif style_kind == 'title':
                    cell.set('style', f'text;html={"1" if render_as_html else "0"};align=left;verticalAlign=middle;whiteSpace=wrap;overflow=hidden;'
                                      'fontSize=24;fontStyle=1;fillColor=none;strokeColor=none;spacing=2;')
                elif style_kind == 'note_header':
                    cell.set('style', f'text;html={"1" if render_as_html else "0"};align=center;verticalAlign=middle;whiteSpace=wrap;overflow=hidden;'
                                      'fontSize=12;fontStyle=1;fillColor=#FFF8E1;strokeColor=#D6B656;rounded=1;spacing=6;')
                elif style_kind == 'note_line':
                    cell.set('style', f'text;html={"1" if render_as_html else "0"};align=left;verticalAlign=middle;whiteSpace=wrap;overflow=hidden;'
                                      'fontSize=11;fillColor=#FFF8E1;strokeColor=#D6B656;rounded=1;spacing=6;')
                else:
                    cell.set('style', f'text;html={"1" if render_as_html else "0"};align=left;verticalAlign=middle;whiteSpace=wrap;overflow=hidden;'
                                      'fontSize=11;fillColor=#FFF8E1;strokeColor=#D6B656;rounded=1;spacing=6;')

                geometry = ET.SubElement(cell, 'mxGeometry')
                geometry.set('x', str(x))
                geometry.set('y', str(y))
                geometry.set('width', str(width))
                geometry.set('height', str(height))
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
                    name=elem.get('display_name', elem['name']),
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
