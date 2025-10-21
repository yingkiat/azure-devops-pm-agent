"""
View Builder - Spec-Driven View Generation (MVP6)

Generates ArchiMate views from YAML specifications for deterministic, repeatable views.
Supports hybrid element selection (criteria, name, ID) and relationship filtering.
"""

import csv
import yaml
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
import pandas as pd

from .archi_layouts import (
    LayoutEngine, LayeredLayout, HierarchicalLayout,
    GridLayout, CompactLayout, ElementPosition
)


class ViewBuilder:
    """Generates views.csv from YAML specifications"""

    def __init__(self, archi_inputs_dir: str = "archi_inputs", specs_dir: str = "ea_inputs/views"):
        self.archi_dir = Path(archi_inputs_dir)
        self.specs_dir = Path(specs_dir)

        # Load elements and relationships from CSV
        self.elements = self._load_elements()
        self.relations = self._load_relations()
        self.properties = self._load_properties()

        # Create lookup indexes
        self.element_by_id = {e['id']: e for e in self.elements}
        self.element_by_name = {e['name']: e for e in self.elements}
        self.relation_by_id = {r['id']: r for r in self.relations}

    def _load_elements(self) -> List[Dict[str, Any]]:
        """Load elements from elements.csv"""
        elements_file = self.archi_dir / "elements.csv"
        if not elements_file.exists():
            print(f"  Elements file not found: {elements_file}")
            return []

        df = pd.read_csv(elements_file)
        elements = []

        for _, row in df.iterrows():
            elements.append({
                'id': row['ID'],
                'type': row['Type'],
                'name': row['Name'],
                'documentation': row.get('Documentation', '')
            })

        return elements

    def _load_relations(self) -> List[Dict[str, Any]]:
        """Load relationships from relations.csv"""
        relations_file = self.archi_dir / "relations.csv"
        if not relations_file.exists():
            print(f"  Relations file not found: {relations_file}")
            return []

        df = pd.read_csv(relations_file)
        relations = []

        for _, row in df.iterrows():
            relations.append({
                'id': row['ID'],
                'type': row['Type'],
                'name': row.get('Name', ''),
                'documentation': row.get('Documentation', ''),
                'source_id': row['Source'],
                'target_id': row['Target']
            })

        return relations

    def _load_properties(self) -> List[Dict[str, Any]]:
        """Load properties from properties.csv"""
        properties_file = self.archi_dir / "properties.csv"
        if not properties_file.exists():
            return []

        df = pd.read_csv(properties_file)
        properties = []

        for _, row in df.iterrows():
            properties.append({
                'element_id': row['ID'],
                'key': row['Key'],
                'value': row['Value']
            })

        return properties

    def generate_views_from_specs(self) -> Dict[str, Any]:
        """
        Read all YAML specs from specs_dir and generate views.csv

        Returns:
            Dict with generation results
        """
        # Create specs directory if it doesn't exist
        self.specs_dir.mkdir(parents=True, exist_ok=True)

        # Load all spec files
        specs = self._load_all_specs()

        if not specs:
            print(f"  No view specifications found in {self.specs_dir}")
            return {
                'views_generated': 0,
                'specs_processed': 0,
                'output_file': None
            }

        print(f" Loading {len(specs)} view specifications...")

        # Generate views from specs
        view_definitions = []
        for spec_file, spec in specs:
            try:
                view_def = self._process_spec(spec_file, spec)
                if view_def:
                    view_definitions.append(view_def)
                    print(f"   {view_def['name']} ({len(view_def['elements'])} elements)")
            except Exception as e:
                print(f"   Failed to process {spec_file.name}: {e}")

        # Write views.csv
        output_file = self._write_views_csv(view_definitions)

        return {
            'views_generated': len(view_definitions),
            'specs_processed': len(specs),
            'output_file': str(output_file) if output_file else None,
            'view_definitions': view_definitions  # Return for model.xml generation
        }

    def _load_all_specs(self) -> List[tuple[Path, Dict[str, Any]]]:
        """Load all YAML spec files from specs directory"""
        if not self.specs_dir.exists():
            return []

        specs = []
        for spec_file in self.specs_dir.glob("*.yaml"):
            try:
                with open(spec_file, 'r', encoding='utf-8') as f:
                    spec = yaml.safe_load(f)
                    if spec and 'view' in spec:
                        specs.append((spec_file, spec))
            except Exception as e:
                print(f"  Failed to load {spec_file.name}: {e}")

        return specs

    def _process_spec(self, spec_file: Path, spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single view spec and return view definition"""
        view_config = spec['view']

        # Extract view metadata
        view_name = view_config['name']
        view_documentation = view_config.get('documentation', '')
        view_id = self._generate_id(f'view-{view_name}')

        # Select elements based on spec
        selected_element_ids = self._select_elements(spec.get('elements', {}))

        if not selected_element_ids:
            print(f"    No elements selected for view: {view_name}")
            return None

        # Filter relationships based on spec
        selected_relation_ids = self._filter_relationships(
            selected_element_ids,
            spec.get('relationships', {})
        )

        # Get layout configuration
        layout_config = spec.get('layout', {})

        # Get grouping configuration
        grouping_config = spec.get('grouping', {})

        return {
            'id': view_id,
            'name': view_name,
            'documentation': view_documentation,
            'elements': selected_element_ids,
            'relations': selected_relation_ids,
            'layout': layout_config,
            'grouping': grouping_config,
            'spec_file': spec_file.name
        }

    def _select_elements(self, elements_config: Dict[str, Any]) -> List[str]:
        """
        Select elements based on hybrid selection criteria

        Supports:
        - Criteria-based: where: {type: "Application", criticality: "High"}
        - Name-based: name: "Microsoft Dynamics"
        - ID-based: id: "id-abc123"
        - Transitive: referenced_by, serves, etc.
        """
        selected_ids = set()
        include_rules = elements_config.get('include', [])

        for rule in include_rules:
            if 'where' in rule:
                # Criteria-based selection
                matched = self._filter_by_criteria(rule['where'])
                selected_ids.update(e['id'] for e in matched)

            elif 'name' in rule:
                # Name-based selection
                name = rule['name']
                if name in self.element_by_name:
                    selected_ids.add(self.element_by_name[name]['id'])
                else:
                    # Try fuzzy matching
                    matched = self._fuzzy_match_name(name)
                    if matched:
                        selected_ids.add(matched['id'])
                    else:
                        print(f"      Element not found: {name}")

            elif 'id' in rule:
                # ID-based selection
                elem_id = rule['id']
                if elem_id in self.element_by_id:
                    selected_ids.add(elem_id)
                else:
                    print(f"      Element ID not found: {elem_id}")

        # Handle transitive inclusion
        if self._has_transitive_rules(include_rules):
            transitive_ids = self._resolve_transitive(list(selected_ids), include_rules)
            selected_ids.update(transitive_ids)

        return list(selected_ids)

    def _filter_by_criteria(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter elements by criteria (type, properties, etc.)"""
        matched = []

        for element in self.elements:
            # Check type criteria
            if 'type' in criteria:
                type_criteria = criteria['type']
                if isinstance(type_criteria, list):
                    if element['type'] not in type_criteria:
                        continue
                else:
                    if element['type'] != type_criteria:
                        continue

            # Check name_contains criteria
            if 'name_contains' in criteria:
                name_patterns = criteria['name_contains']
                if isinstance(name_patterns, str):
                    name_patterns = [name_patterns]

                if not any(pattern.lower() in element['name'].lower() for pattern in name_patterns):
                    continue

            # Check property criteria
            if self._check_property_criteria(element['id'], criteria):
                matched.append(element)

        return matched

    def _check_property_criteria(self, element_id: str, criteria: Dict[str, Any]) -> bool:
        """Check if element properties match criteria"""
        # Get element properties
        elem_props = {
            p['key']: p['value']
            for p in self.properties
            if p['element_id'] == element_id
        }

        # Check each property criteria
        for key, value in criteria.items():
            if key in ['type', 'name_contains', 'referenced_by', 'serves']:
                continue  # Skip non-property criteria

            # Check if property matches
            prop_key = key.replace('_', ' ').title()
            if prop_key not in elem_props:
                return False

            # Check value match (case-insensitive)
            if isinstance(value, str):
                if value.lower() not in elem_props[prop_key].lower():
                    return False

        return True

    def _fuzzy_match_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Fuzzy match element by name (case-insensitive, partial match)"""
        name_lower = name.lower()

        # Exact match (case-insensitive)
        for element in self.elements:
            if element['name'].lower() == name_lower:
                return element

        # Partial match
        for element in self.elements:
            if name_lower in element['name'].lower():
                return element

        return None

    def _has_transitive_rules(self, include_rules: List[Dict[str, Any]]) -> bool:
        """Check if any rules require transitive inclusion"""
        transitive_keys = ['referenced_by', 'serves', 'accesses', 'flows_to', 'flows_from']
        return any(
            any(key in rule.get('where', {}) for key in transitive_keys)
            for rule in include_rules
        )

    def _resolve_transitive(self, base_element_ids: List[str], include_rules: List[Dict[str, Any]]) -> Set[str]:
        """Resolve transitive element inclusion based on relationships"""
        transitive_ids = set()

        for rule in include_rules:
            where_clause = rule.get('where', {})

            # Handle "referenced_by" - find elements referenced by base elements
            if 'referenced_by' in where_clause:
                ref_type = where_clause['referenced_by']
                if ref_type == 'included_applications':
                    # Find all elements referenced by applications in base set
                    app_ids = [eid for eid in base_element_ids
                              if self.element_by_id[eid]['type'] == 'ApplicationComponent']

                    for rel in self.relations:
                        if rel['source_id'] in app_ids:
                            transitive_ids.add(rel['target_id'])

            # Handle "serves" - find elements that serve base elements
            if 'serves' in where_clause:
                target_type = where_clause['serves']
                if target_type == 'included_applications':
                    for rel in self.relations:
                        if rel['target_id'] in base_element_ids and rel['type'] == 'Serving':
                            transitive_ids.add(rel['source_id'])

        return transitive_ids

    def _filter_relationships(self, selected_element_ids: List[str],
                              relationships_config: Dict[str, Any]) -> List[str]:
        """Filter relationships based on spec configuration"""
        selected_relation_ids = []
        include_rules = relationships_config.get('include', [])
        exclude_rules = relationships_config.get('exclude', [])

        # Default: include all relationships between selected elements
        if not include_rules:
            include_rules = [{'type': [], 'between': 'included_elements'}]

        element_ids_set = set(selected_element_ids)

        for rule in include_rules:
            # Get relationship types to include
            rel_types = rule.get('type', [])
            if isinstance(rel_types, str):
                rel_types = [rel_types]

            # Filter relationships
            for rel in self.relations:
                # Check if between selected elements
                if rule.get('between') == 'included_elements':
                    if rel['source_id'] not in element_ids_set or rel['target_id'] not in element_ids_set:
                        continue

                # Check relationship type
                if rel_types and rel['type'] not in rel_types:
                    continue

                # Check if excluded
                if self._is_relationship_excluded(rel, exclude_rules):
                    continue

                if rel['id'] not in selected_relation_ids:
                    selected_relation_ids.append(rel['id'])

        return selected_relation_ids

    def _is_relationship_excluded(self, rel: Dict[str, Any], exclude_rules: List[Dict[str, Any]]) -> bool:
        """Check if relationship should be excluded"""
        for rule in exclude_rules:
            if 'type' in rule:
                exclude_types = rule['type']
                if isinstance(exclude_types, str):
                    exclude_types = [exclude_types]

                if rel['type'] in exclude_types:
                    return True

        return False

    def _organize_by_groups(self, element_ids: List[str], grouping_config: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Organize elements into groups based on property values.
        Supports both single-level and nested two-level grouping.

        Returns:
            Dict mapping group names to lists of element IDs (single-level)
            OR Dict mapping primary group → Dict of secondary groups (two-level)
        """
        if not grouping_config or 'by_property' not in grouping_config:
            # No grouping - return all elements in a single group
            return {'_no_group': element_ids}

        property_key = grouping_config['by_property']

        # Check for nested grouping (MVP6 enhancement)
        secondary_property = grouping_config.get('secondary_by_property')

        if secondary_property:
            # Two-level nested grouping: primary_group -> secondary_group -> elements
            return self._organize_nested_groups(element_ids, property_key, secondary_property)
        else:
            # Single-level grouping (existing behavior)
            groups = {}
            ungrouped = []

            for elem_id in element_ids:
                # Find property value for this element
                prop_value = None
                for prop in self.properties:
                    if prop['element_id'] == elem_id and prop['key'] == property_key:
                        prop_value = prop['value']
                        break

                if prop_value:
                    if prop_value not in groups:
                        groups[prop_value] = []
                    groups[prop_value].append(elem_id)
                else:
                    ungrouped.append(elem_id)

            # Add ungrouped elements to a special group
            if ungrouped:
                groups['_ungrouped'] = ungrouped

            return groups

    def _organize_nested_groups(self, element_ids: List[str], primary_key: str, secondary_key: str) -> Dict[str, Dict[str, List[str]]]:
        """
        Organize elements into nested groups: primary -> secondary -> element IDs

        Returns:
            Dict mapping primary_group_name -> Dict[secondary_group_name -> [element_ids]]
        """
        nested_groups = {}

        for elem_id in element_ids:
            # Find primary and secondary property values
            primary_value = None
            secondary_value = None

            for prop in self.properties:
                if prop['element_id'] == elem_id:
                    if prop['key'] == primary_key:
                        primary_value = prop['value']
                    elif prop['key'] == secondary_key:
                        secondary_value = prop['value']

            # Use defaults for missing properties
            primary_value = primary_value or '_ungrouped'
            secondary_value = secondary_value or '_ungrouped'

            # Create nested structure
            if primary_value not in nested_groups:
                nested_groups[primary_value] = {}

            if secondary_value not in nested_groups[primary_value]:
                nested_groups[primary_value][secondary_value] = []

            nested_groups[primary_value][secondary_value].append(elem_id)

        return nested_groups

    def _get_layout_engine(self, layout_config: Dict[str, Any]) -> LayoutEngine:
        """Get layout engine based on configuration"""
        algorithm = layout_config.get('algorithm', 'layered')
        spacing_x = layout_config.get('spacing_x', 50)
        spacing_y = layout_config.get('spacing_y', 80)

        if algorithm == 'hierarchical':
            return HierarchicalLayout(spacing_x=spacing_x, spacing_y=spacing_y)
        elif algorithm == 'grid':
            columns = layout_config.get('columns', 3)
            return GridLayout(columns=columns, spacing_x=spacing_x, spacing_y=spacing_y)
        elif algorithm == 'column':
            # NEW: Column layout for vertical stacking
            from .archi_layouts import ColumnLayout
            return ColumnLayout(spacing_x=spacing_x, spacing_y=spacing_y)
        elif algorithm == 'compact':
            max_width = layout_config.get('max_width', 800)
            return CompactLayout(max_width=max_width)
        else:  # Default to layered
            return LayeredLayout(spacing_x=spacing_x, spacing_y=spacing_y)

    def _write_views_csv(self, view_definitions: List[Dict[str, Any]]) -> Optional[Path]:
        """Write views.csv in Archi format"""
        if not view_definitions:
            print("  No views to write")
            return None

        output_file = self.archi_dir / "views.csv"

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Type', 'Name', 'Documentation', 'Element', 'x', 'y', 'w', 'h'])

            for view_def in view_definitions:
                # Write view header
                writer.writerow([
                    view_def['id'],
                    'archimate-diagram-model',
                    view_def['name'],
                    view_def['documentation'],
                    '',  # Element
                    '',  # x
                    '',  # y
                    '',  # w
                    ''   # h
                ])

                # Check if grouping is enabled
                grouping_config = view_def.get('grouping', {})

                if grouping_config and 'by_property' in grouping_config:
                    # Organize elements into groups (may be nested)
                    groups = self._organize_by_groups(view_def['elements'], grouping_config)

                    # Check if nested grouping
                    is_nested = grouping_config.get('secondary_by_property') is not None

                    if is_nested:
                        # Handle nested grouping (primary -> secondary)
                        self._write_nested_groups_csv(writer, view_def, groups, grouping_config)
                    else:
                        # Handle flat grouping (existing code)
                        self._write_flat_groups_csv(writer, view_def, groups, grouping_config)

                else:
                    # No grouping - use standard layout
                    layout = self._get_layout_engine(view_def['layout'])
                    view_elements = [self.element_by_id[eid] for eid in view_def['elements']]
                    view_relations = [self.relation_by_id[rid] for rid in view_def['relations']]

                    # Calculate positions
                    positions = layout.calculate_layout(view_elements, view_relations)

                    # Write element positions
                    for pos in positions:
                        writer.writerow([
                            '',  # ID (empty for element rows)
                            '',  # Type
                            '',  # Name
                            '',  # Documentation
                            pos.element_id,
                            pos.x,
                            pos.y,
                            pos.w,
                            pos.h
                        ])

                # Write relationship placeholders (Archi will auto-route)
                for rel_id in view_def['relations']:
                    writer.writerow([
                        '',  # ID
                        '',  # Type
                        '',  # Name
                        '',  # Documentation
                        rel_id,
                        '',  # x (relationships don't have positions)
                        '',  # y
                        '',  # w
                        ''   # h
                    ])

        print(f"\n Generated views.csv: {output_file}")
        print(f" Total views: {len(view_definitions)}")

        return output_file

    def _generate_id(self, text: str) -> str:
        """Generate unique ID from text"""
        return f"id-{hashlib.md5(text.encode()).hexdigest()[:12]}"

    def _write_flat_groups_csv(self, writer, view_def: Dict[str, Any], groups: Dict[str, List[str]],
                               grouping_config: Dict[str, Any]) -> None:
        """Write flat (single-level) grouping to CSV"""
        # Calculate group layout
        group_width = grouping_config.get('group_width', 400)
        group_height = grouping_config.get('group_height', 300)
        group_spacing_x = grouping_config.get('group_spacing_x', 50)
        group_spacing_y = grouping_config.get('group_spacing_y', 50)

        # Determine group order (by property if specified)
        group_order = grouping_config.get('order', sorted(groups.keys()))

        x_offset = 20
        y_offset = 20
        groups_per_row = grouping_config.get('groups_per_row', 3)

        for idx, group_name in enumerate(group_order):
            if group_name not in groups:
                continue

            # Calculate group position
            row = idx // groups_per_row
            col = idx % groups_per_row
            group_x = x_offset + col * (group_width + group_spacing_x)
            group_y = y_offset + row * (group_height + group_spacing_y)

            # Write group container
            group_id = self._generate_id(f'group-{view_def["id"]}-{group_name}')
            writer.writerow([
                '',  # ID
                '',  # Type
                group_name if not group_name.startswith('_') else 'Other',  # Group label
                '',  # Documentation
                group_id,
                group_x,
                group_y,
                group_width,
                group_height
            ])

            # Layout elements within the group
            group_elements = [self.element_by_id[eid] for eid in groups[group_name]]
            layout = self._get_layout_engine(view_def['layout'])

            # Calculate positions relative to group
            group_positions = layout.calculate_layout(group_elements, [])

            # Write element positions (RELATIVE to group container)
            padding = 20
            for pos in group_positions:
                writer.writerow([
                    '',  # ID (empty for element rows)
                    '',  # Type
                    '',  # Name
                    '',  # Documentation
                    pos.element_id,
                    padding + pos.x,  # Relative to group
                    padding + pos.y,  # Relative to group
                    pos.w,
                    pos.h
                ])

    def _write_nested_groups_csv(self, writer, view_def: Dict[str, Any], nested_groups: Dict[str, Dict[str, List[str]]],
                                 grouping_config: Dict[str, Any]) -> None:
        """Write nested two-level grouping to CSV (primary groups contain secondary groups with elements)"""
        # For CSV, flatten to show primary groups only with all contained elements
        # XML generation will handle proper nesting
        group_width = grouping_config.get('group_width', 400)
        group_height = grouping_config.get('group_height', 300)
        group_spacing_x = grouping_config.get('group_spacing_x', 50)
        group_spacing_y = grouping_config.get('group_spacing_y', 50)

        # Get primary group order
        primary_order = grouping_config.get('order', sorted(nested_groups.keys()))

        x_offset = 20
        y_offset = 20
        groups_per_row = grouping_config.get('groups_per_row', 3)

        for idx, primary_name in enumerate(primary_order):
            if primary_name not in nested_groups:
                continue

            # Calculate primary group position
            row = idx // groups_per_row
            col = idx % groups_per_row
            group_x = x_offset + col * (group_width + group_spacing_x)
            group_y = y_offset + row * (group_height + group_spacing_y)

            # Write primary group container
            primary_group_id = self._generate_id(f'primary-group-{view_def["id"]}-{primary_name}')
            writer.writerow([
                '',  # ID
                '',  # Type
                primary_name if not primary_name.startswith('_') else 'Other',  # Group label
                '',  # Documentation
                primary_group_id,
                group_x,
                group_y,
                group_width,
                group_height
            ])

            # Collect all elements from all secondary groups within this primary group
            all_elements_in_primary = []
            for secondary_name, element_ids in nested_groups[primary_name].items():
                all_elements_in_primary.extend(element_ids)

            # Layout elements within the primary group
            group_elements = [self.element_by_id[eid] for eid in all_elements_in_primary if eid in self.element_by_id]
            layout = self._get_layout_engine(view_def['layout'])

            # Calculate positions relative to group
            group_positions = layout.calculate_layout(group_elements, [])

            # Write element positions
            padding = 20
            for pos in group_positions:
                writer.writerow([
                    '',  # ID
                    '',  # Type
                    '',  # Name
                    '',  # Documentation
                    pos.element_id,
                    padding + pos.x,
                    padding + pos.y,
                    pos.w,
                    pos.h
                ])


def main():
    """Test view builder"""
    builder = ViewBuilder()
    result = builder.generate_views_from_specs()

    print(f"\n{'='*60}")
    print(f"View Generation Complete:")
    print(f"  Views generated: {result['views_generated']}")
    print(f"  Specs processed: {result['specs_processed']}")
    print(f"  Output file: {result['output_file']}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
