"""
Archi Export Module

Converts EA discovery JSON to Archi-compatible CSV files:
- elements.csv: ArchiMate elements
- relations.csv: ArchiMate relationships
- properties.csv: Element properties
- views.csv: Visual diagram layouts
"""

import csv
import json
import hashlib
import yaml
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime
import xml.etree.ElementTree as ET

from .archi_layouts import choose_layout, ElementPosition
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ViewDefinition:
    """Represents an ArchiMate view definition"""
    id: str
    type: str
    name: str
    documentation: str
    elements: List[str]
    relations: List[str]
    grouping: Optional[Dict[str, Any]] = None
    layout: Optional[Dict[str, Any]] = None


class ViewGenerator:
    """Auto-generates views from EA analysis (backward compatibility stub)"""

    def generate_all_views(self, ea_analysis: Dict[str, Any],
                          elements: List[Dict[str, Any]],
                          relations: List[Dict[str, Any]]) -> List[ViewDefinition]:
        """Generate default views from elements and relations"""
        import hashlib

        views = []

        # Create single overview view with all elements
        all_element_ids = [e['id'] for e in elements]
        all_relation_ids = [r['id'] for r in relations]

        if all_element_ids:
            view_id = f"id-{hashlib.md5('overview-view'.encode()).hexdigest()[:12]}"
            views.append(ViewDefinition(
                id=view_id,
                type='archimate-diagram-model',
                name='EA Overview',
                documentation='Auto-generated overview of all discovered elements',
                elements=all_element_ids,
                relations=all_relation_ids
            ))

        return views


# ArchiMate XML namespace (Open Group standard)
ARCHIMATE_NS = "http://www.opengroup.org/xsd/archimate/3.0/"
ET.register_namespace("", ARCHIMATE_NS)


class ArchiExporter:
    """Exports EA analysis to Archi-compatible CSV format"""

    def __init__(self, output_dir: str = "archi_inputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.view_generator = ViewGenerator()
        self.property_schema = self._load_property_schema()

    def export(self, ea_analysis_file: str, generate_views: bool = True,
               generate_archimate_xml: bool = False, use_ai_layout: bool = True,
               incremental: bool = False) -> Dict[str, str]:
        """
        Export EA analysis to Archi CSV files and optionally .archimate XML

        Args:
            ea_analysis_file: Path to EA analysis JSON
            generate_views: Whether to generate view layouts
            generate_archimate_xml: Whether to generate .archimate XML package file
            use_ai_layout: Whether to use AI-driven layout for grouped views (MVP7)
            incremental: Whether to merge with existing data (True) or replace (False)

        Returns:
            Dict of output file paths
        """
        # Ensure output directory exists (in case it was deleted after __init__)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load EA analysis
        with open(ea_analysis_file, 'r', encoding='utf-8') as f:
            ea_analysis = json.load(f)

        mode_str = "INCREMENTAL" if incremental else "REPLACE"
        print(f"Exporting EA analysis to Archi format ({mode_str} mode)...")
        print(f"Output directory: {self.output_dir}")

        # Generate elements from this discovery
        new_elements = self._generate_elements(ea_analysis)
        print(f"  New elements from discovery: {len(new_elements)}")

        # Generate relationships from this discovery
        new_relations = self._generate_relations(ea_analysis, new_elements)
        print(f"  New relationships from discovery: {len(new_relations)}")

        # Generate properties from this discovery
        new_properties = self._generate_properties(ea_analysis, new_elements)
        print(f"  New properties from discovery: {len(new_properties)}")

        # Merge with existing data if incremental mode
        if incremental:
            existing_elements = self._load_existing_elements()
            existing_relations = self._load_existing_relations()
            existing_properties = self._load_existing_properties()

            print(f"  Existing elements: {len(existing_elements)}")
            print(f"  Existing relationships: {len(existing_relations)}")
            print(f"  Existing properties: {len(existing_properties)}")

            elements = self._merge_elements(existing_elements, new_elements)
            relations = self._merge_relations(existing_relations, new_relations)
            properties = self._merge_properties(existing_properties, new_properties)

            print(f"  Merged elements: {len(elements)}")
            print(f"  Merged relationships: {len(relations)}")
            print(f"  Merged properties: {len(properties)}")
        else:
            elements = new_elements
            relations = new_relations
            properties = new_properties

        # Write CSV files
        output_files = {}
        output_files['elements'] = self._write_elements_csv(elements)
        output_files['relations'] = self._write_relations_csv(relations)
        output_files['properties'] = self._write_properties_csv(properties)

        # Generate views if requested (MVP6: Dual-mode support)
        views = []
        if generate_views:
            # Check if spec files exist for spec-driven mode
            from pathlib import Path
            specs_dir = Path("ea_inputs/views")

            if specs_dir.exists() and list(specs_dir.glob("**/*.yaml")):
                # MVP6 Mode: Generate views from specs (deterministic)
                print(f" MVP6 Mode: Using view specifications from {specs_dir}")
                from .view_builder import ViewBuilder
                view_builder = ViewBuilder()
                result = view_builder.generate_views_from_specs()

                if result.get('views_generated', 0) > 0:
                    output_files['views'] = result.get('output_file')
                    # Convert dict view_definitions to ViewDefinition objects for model.xml
                    view_defs = result.get('view_definitions', [])
                    views = [ViewDefinition(
                        id=v['id'],
                        type='archimate-diagram-model',
                        name=v['name'],
                        documentation=v['documentation'],
                        elements=v['elements'],
                        relations=v['relations'],
                        grouping=v.get('grouping'),
                        layout=v.get('layout')
                    ) for v in view_defs]
                    print(f" Generated {result['views_generated']} views from specs (deterministic)")
                else:
                    print(f"  No views generated from specs, falling back to auto-gen")
                    views = self.view_generator.generate_all_views(ea_analysis, elements, relations)
                    output_files['views'] = self._write_views_csv(views, elements, relations)
                    print(f" Generated {len(views)} views (auto-gen)")
            else:
                # MVP4 Mode: Auto-generate views (backward compatible)
                print(f" MVP4 Mode: Auto-generating views")
                views = self.view_generator.generate_all_views(ea_analysis, elements, relations)
                output_files['views'] = self._write_views_csv(views, elements, relations)
                print(f" Generated {len(views)} views (auto-gen)")

        # Generate .archimate XML package if requested
        if generate_archimate_xml:
            xml_path = self._write_archimate_xml(elements, relations, properties, views, use_ai_layout=use_ai_layout)
            output_files['archimate_xml'] = xml_path
            if views:
                print(f" Generated ArchiMate XML with {len(views)} views (model.xml)")
            else:
                print(f" Generated ArchiMate XML (model.xml)")

        return output_files

    def _generate_elements(self, ea_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate ArchiMate elements from EA analysis (ArchiMate-native format)"""

        elements = []

        # Expect ArchiMate-native discovery format
        if 'discovery' not in ea_analysis:
            print("  No 'discovery' section found in EA analysis")
            return elements

        discovery = ea_analysis['discovery']

        # Process each ArchiMate type directly - no mapping needed!
        for archimate_type, items in discovery.items():
            if not items or not isinstance(items, list):
                continue

            # Create elements using the ArchiMate type directly from the key
            for item in items:
                element = self._create_element(
                    item,
                    archimate_type,  # Use ArchiMate type directly from discovery
                    self._get_layer_from_type(archimate_type),  # Infer layer from type
                    archimate_type  # Category is same as type
                )
                if element:
                    elements.append(element)

        return elements

    def _get_layer_from_type(self, archimate_type: str) -> str:
        """Infer EA layer from ArchiMate type"""
        type_lower = archimate_type.lower()

        if any(x in type_lower for x in ['business', 'capability', 'actor']):
            return 'business'
        elif any(x in type_lower for x in ['application', 'interface', 'service']):
            return 'application'
        elif 'data' in type_lower:
            return 'data'
        elif any(x in type_lower for x in ['node', 'device', 'network', 'technology']):
            return 'infrastructure'
        else:
            return 'application'  # Default to application layer

    def _create_element(self, item: Any, archimate_type: str, layer: str, category: str) -> Dict[str, Any]:
        """Create an ArchiMate element from EA item"""

        if isinstance(item, dict):
            name = item.get('name', f'{category}-item')
            description = item.get('description', '')
        else:
            name = str(item)
            description = ''

        element_id = self._generate_id(f'elem-{archimate_type}-{name}')

        return {
            'id': element_id,
            'type': archimate_type,
            'name': name,
            'documentation': description,
            'layer': layer,
            'category': category,
            'raw_data': item if isinstance(item, dict) else {}
        }

    def _validate_relationship_type(self, rel_type: str) -> str:
        """
        Validate and map relationship type to valid ArchiMate 3.0 types.

        Valid ArchiMate 3.0 relationship types:
        - Composition, Aggregation, Assignment, Realization
        - Serving, Access, Influence, Triggering, Flow
        - Specialization, Association
        """
        # Valid ArchiMate types
        valid_types = {
            'Composition', 'Aggregation', 'Assignment', 'Realization',
            'Serving', 'Access', 'Influence', 'Triggering', 'Flow',
            'Specialization', 'Association'
        }

        # If already valid, return as-is
        if rel_type in valid_types:
            return rel_type

        # Map common invalid types to valid ArchiMate types
        type_mappings = {
            'Replacing': 'Association',  # Replacement relationships
            'Uses': 'Serving',           # Usage relationships
            'Calls': 'Flow',             # API/service calls
            'Depends': 'Association',    # Dependencies
            'Contains': 'Composition',   # Containment
            'Implements': 'Realization', # Implementation
            'Supports': 'Serving',       # Support relationships
        }

        # Try mapping
        mapped_type = type_mappings.get(rel_type, 'Association')

        if mapped_type != rel_type:
            print(f"  Mapped invalid relationship type '{rel_type}' -> '{mapped_type}'")

        return mapped_type

    def _generate_relations(self, ea_analysis: Dict[str, Any],
                           elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate ArchiMate relationships from EA analysis"""

        relations = []
        element_by_name = {e['name']: e for e in elements}

        # NEW FORMAT: Read relationships from prompt output
        if 'relationships' in ea_analysis:
            for rel in ea_analysis['relationships']:
                if not isinstance(rel, dict):
                    continue

                source_name = rel.get('source', '')
                target_name = rel.get('target', '')

                # Find matching elements by name
                if source_name in element_by_name and target_name in element_by_name:
                    # Validate and map relationship type
                    rel_type = self._validate_relationship_type(rel.get('type', 'Association'))

                    relations.append({
                        'id': self._generate_id(f'rel-{source_name}-{target_name}'),
                        'type': rel_type,
                        'source_id': element_by_name[source_name]['id'],
                        'target_id': element_by_name[target_name]['id'],
                        'relationship_type': rel_type,
                        'name': rel.get('name', ''),
                        'documentation': rel.get('description', '')
                    })

        # LEGACY FORMAT: Application layer interfaces (fallback)
        app_layer = ea_analysis.get('application', {})
        if 'interfaces' in app_layer:
            for interface in app_layer['interfaces']:
                if isinstance(interface, dict):
                    source_name = interface.get('from_system', '')
                    target_name = interface.get('to_system', '')

                    if source_name in element_by_name and target_name in element_by_name:
                        relations.append({
                            'id': self._generate_id(f'rel-{source_name}-{target_name}'),
                            'type': 'Flow',
                            'source_id': element_by_name[source_name]['id'],
                            'target_id': element_by_name[target_name]['id'],
                            'relationship_type': 'Flow',
                            'name': interface.get('name', ''),
                            'documentation': f"Data: {', '.join(interface.get('data_exchanged', []))}"
                        })

        # LEGACY FORMAT: Data layer flows (fallback)
        data_layer = ea_analysis.get('data', {})
        if 'flows' in data_layer:
            for flow in data_layer['flows']:
                if isinstance(flow, dict):
                    source_name = flow.get('from_system', '')
                    target_name = flow.get('to_system', '')

                    if source_name in element_by_name and target_name in element_by_name:
                        relations.append({
                            'id': self._generate_id(f'rel-{source_name}-{target_name}'),
                            'type': 'Flow',
                            'source_id': element_by_name[source_name]['id'],
                            'target_id': element_by_name[target_name]['id'],
                            'relationship_type': 'Flow',
                            'name': flow.get('name', ''),
                            'documentation': f"Format: {flow.get('format', 'unknown')}"
                        })

        # INFERRED: Serving relationships from capabilities_supported field
        applications = [e for e in elements if e['type'] == 'ApplicationComponent']
        capabilities = [e for e in elements if e['type'] == 'Capability']

        # Build capability-only lookup to prevent circular relationships
        capability_by_name = {c['name']: c for c in capabilities}

        for app in applications:
            # Check capabilities_supported field from discovery
            caps_supported = app.get('raw_data', {}).get('capabilities_supported', [])
            for cap_name in caps_supported:
                # Find matching capability element (ONLY in capabilities, not all elements)
                if cap_name in capability_by_name:
                    cap_element = capability_by_name[cap_name]
                    # Prevent circular relationships (app cannot serve itself)
                    if app['id'] == cap_element['id']:
                        continue
                    # Create Serving relationship: App serves Capability
                    rel_id = self._generate_id(f'rel-serving-{app["name"]}-{cap_name}')
                    # Avoid duplicates
                    if not any(r['id'] == rel_id for r in relations):
                        relations.append({
                            'id': rel_id,
                            'type': 'Serving',
                            'source_id': app['id'],
                            'target_id': cap_element['id'],
                            'relationship_type': 'Serving',
                            'name': 'supports',
                            'documentation': f'{app["name"]} supports {cap_name} capability'
                        })

        return relations

    def _generate_properties(self, ea_analysis: Dict[str, Any],
                            elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate element properties from both raw_data and changes section"""

        properties = []

        # Build element lookup by name for matching with changes
        element_by_name = {e['name']: e for e in elements}

        # PART 1: Extract properties from raw_data (element-level attributes)
        # Skip keys that shouldn't become properties
        skip_keys = {'name', 'description', 'status', 'capabilities_supported', 'lifecycle_signals'}

        for element in elements:
            raw_data = element.get('raw_data', {})

            # Dynamically extract all properties from raw_data
            for key, value in raw_data.items():
                # Skip keys that are already used elsewhere or shouldn't be properties
                if key in skip_keys or not value:
                    continue

                # Format the property key (convert snake_case to Title Case)
                prop_key = key.replace('_', ' ').title()

                # Handle different value types
                if isinstance(value, list):
                    # Join list values with comma
                    prop_value = ', '.join(str(v) for v in value if v)
                elif isinstance(value, dict):
                    # Skip complex nested objects
                    continue
                else:
                    prop_value = str(value)

                if prop_value:  # Only add if there's a value
                    properties.append({
                        'element_id': element['id'],
                        'key': prop_key,
                        'value': prop_value
                    })

        # PART 2: Extract properties from changes section (business attributes)
        changes = ea_analysis.get('changes', {})

        # Keys that identify the element, not properties
        change_skip_keys = {'app_name', 'capability'}

        # Process inserts - these have full business attribute assessments
        for insert in changes.get('inserts', []):
            if not isinstance(insert, dict):
                continue

            app_name = insert.get('app_name')
            if not app_name or app_name not in element_by_name:
                continue

            element = element_by_name[app_name]
            element_id = element['id']
            element_type = element['type']

            # Extract business attributes from the insert
            for attr_key, attr_value in insert.items():
                # Skip identifying keys and empty values
                if attr_key in change_skip_keys or not attr_value:
                    continue

                # Format the property key (convert snake_case to Title Case)
                prop_key = attr_key.replace('_', ' ').title()

                # Check if property is allowed for this element type
                if not self._is_property_allowed(element_type, prop_key):
                    continue

                # Avoid duplicates - check if property already exists
                existing = any(p['element_id'] == element_id and p['key'] == prop_key
                             for p in properties)
                if not existing:
                    properties.append({
                        'element_id': element_id,
                        'key': prop_key,
                        'value': str(attr_value)
                    })

        # Process updates - may have attribute changes
        for update in changes.get('updates', []):
            if not isinstance(update, dict):
                continue

            app_name = update.get('app_name')
            if not app_name or app_name not in element_by_name:
                continue

            element = element_by_name[app_name]
            element_id = element['id']
            element_type = element['type']

            # Extract business attributes from the update
            for attr_key, attr_value in update.items():
                # Skip identifying keys and empty values
                if attr_key in change_skip_keys or not attr_value:
                    continue

                # Format the property key (convert snake_case to Title Case)
                prop_key = attr_key.replace('_', ' ').title()

                # Check if property is allowed for this element type
                if not self._is_property_allowed(element_type, prop_key):
                    continue

                # Remove old value if exists, then add new one
                properties = [p for p in properties
                            if not (p['element_id'] == element_id and p['key'] == prop_key)]
                properties.append({
                    'element_id': element_id,
                    'key': prop_key,
                    'value': str(attr_value)
                })

        return properties

    def _write_elements_csv(self, elements: List[Dict[str, Any]]) -> str:
        """Write elements.csv"""

        output_file = self.output_dir / "elements.csv"

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Type', 'Name', 'Documentation'])

            for elem in elements:
                writer.writerow([
                    elem['id'],
                    elem['type'],
                    elem['name'],
                    elem.get('documentation', '')
                ])

        print(f"   {output_file}")
        return str(output_file)

    def _write_relations_csv(self, relations: List[Dict[str, Any]]) -> str:
        """Write relations.csv"""

        output_file = self.output_dir / "relations.csv"

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Type', 'Name', 'Documentation', 'Source', 'Target'])

            for rel in relations:
                writer.writerow([
                    rel['id'],
                    rel.get('relationship_type', rel.get('type', 'Association')),
                    rel.get('name', ''),
                    rel.get('documentation', ''),
                    rel['source_id'],
                    rel['target_id']
                ])

        print(f"   {output_file}")
        return str(output_file)

    def _write_properties_csv(self, properties: List[Dict[str, Any]]) -> str:
        """Write properties.csv"""

        output_file = self.output_dir / "properties.csv"

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Key', 'Value'])

            for prop in properties:
                writer.writerow([
                    prop['element_id'],
                    prop['key'],
                    prop['value']
                ])

        print(f"   {output_file}")
        return str(output_file)

    # ===== Incremental Mode Helper Methods =====

    def _load_existing_elements(self) -> List[Dict[str, Any]]:
        """Load existing elements from elements.csv"""
        elements_file = self.output_dir / "elements.csv"
        if not elements_file.exists():
            return []

        elements = []
        with open(elements_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                elements.append({
                    'id': row['ID'],
                    'type': row['Type'],
                    'name': row['Name'],
                    'documentation': row.get('Documentation', ''),
                    'layer': 'application',  # Default, will be overridden if needed
                    'category': row['Type'],
                    'raw_data': {}
                })
        return elements

    def _load_existing_relations(self) -> List[Dict[str, Any]]:
        """Load existing relations from relations.csv"""
        relations_file = self.output_dir / "relations.csv"
        if not relations_file.exists():
            return []

        relations = []
        with open(relations_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                relations.append({
                    'id': row['ID'],
                    'type': row['Type'],
                    'name': row.get('Name', ''),
                    'documentation': row.get('Documentation', ''),
                    'source_id': row['Source'],
                    'target_id': row['Target'],
                    'relationship_type': row['Type']
                })
        return relations

    def _load_existing_properties(self) -> List[Dict[str, Any]]:
        """Load existing properties from properties.csv"""
        properties_file = self.output_dir / "properties.csv"
        if not properties_file.exists():
            return []

        properties = []
        with open(properties_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                properties.append({
                    'element_id': row['ID'],
                    'key': row['Key'],
                    'value': row['Value']
                })
        return properties

    def _merge_elements(self, existing: List[Dict[str, Any]], new: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge existing and new elements, deduplicating by name.
        New elements with same name will update existing ones.
        """
        # Build lookup by name (case-insensitive)
        merged = {}
        for elem in existing:
            key = elem['name'].lower()
            merged[key] = elem

        for elem in new:
            key = elem['name'].lower()
            if key in merged:
                # Update existing element with new data (keep ID for consistency)
                existing_elem = merged[key]
                # Merge descriptions
                if elem.get('documentation') and elem['documentation'] != existing_elem.get('documentation', ''):
                    if existing_elem.get('documentation'):
                        existing_elem['documentation'] = f"{existing_elem['documentation']}; {elem['documentation']}"
                    else:
                        existing_elem['documentation'] = elem['documentation']
                # Update other fields from new element
                existing_elem['type'] = elem['type']
                existing_elem['layer'] = elem.get('layer', existing_elem.get('layer', 'application'))
                existing_elem['category'] = elem.get('category', existing_elem.get('category', elem['type']))
                existing_elem['raw_data'] = elem.get('raw_data', {})
            else:
                # Add new element
                merged[key] = elem

        return list(merged.values())

    def _merge_relations(self, existing: List[Dict[str, Any]], new: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge existing and new relations, deduplicating by (type, source, target).
        """
        # Build lookup by (type, source_id, target_id)
        merged = {}
        for rel in existing:
            key = (rel['type'], rel['source_id'], rel['target_id'])
            merged[key] = rel

        for rel in new:
            key = (rel['type'], rel['source_id'], rel['target_id'])
            if key not in merged:
                merged[key] = rel
            # If exists, keep existing (don't overwrite)

        return list(merged.values())

    def _merge_properties(self, existing: List[Dict[str, Any]], new: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge existing and new properties, deduplicating by (element_id, key).
        New properties override existing ones for the same key.
        """
        # Build lookup by (element_id, key)
        merged = {}
        for prop in existing:
            key = (prop['element_id'], prop['key'])
            merged[key] = prop

        for prop in new:
            key = (prop['element_id'], prop['key'])
            # New properties override existing
            merged[key] = prop

        return list(merged.values())

    def import_catalogue_properties(self, catalogue_path: str) -> Dict[str, Any]:
        """
        Directly import properties from Application Catalogue.xlsx.

        Reads the catalogue deterministically (no LLM). Handles multi-row headers
        by combining rows 1+2 (sub-header takes precedence where non-empty).
        Matches rows to model elements by "Application Name" column.
        Merges all column values as properties - catalogue is authoritative.
        """
        try:
            from openpyxl import load_workbook
        except ImportError:
            return {"success": False, "error": "openpyxl required: pip install openpyxl"}

        cat_path = Path(catalogue_path)
        if not cat_path.exists():
            return {"success": False, "error": f"File not found: {catalogue_path}"}

        wb = load_workbook(cat_path, data_only=True)
        ws = wb.active

        # Build combined header: if merged cells exist in row 1, combine rows 1+2
        # Sub-header (row 2) takes precedence over parent header (row 1) when non-empty
        has_merged = any(m.min_row == 1 for m in ws.merged_cells.ranges)

        if has_merged and ws.max_row >= 2:
            row1_vals = list(next(ws.iter_rows(min_row=1, max_row=1, values_only=True)))
            row2_vals = list(next(ws.iter_rows(min_row=2, max_row=2, values_only=True)))
            headers = []
            for c1, c2 in zip(row1_vals, row2_vals):
                c1_s = str(c1).strip() if c1 is not None else ''
                c2_s = str(c2).strip() if c2 is not None else ''
                headers.append(c2_s if c2_s else (c1_s if c1_s else None))
            data_start_row = 3
        else:
            row1_vals = list(next(ws.iter_rows(min_row=1, max_row=1, values_only=True)))
            headers = [str(c).strip() if c is not None else None for c in row1_vals]
            data_start_row = 2

        wb.close()

        # Map catalogue column names → canonical property names used in the model
        # Catalogue uses snake_case sub-headers; model uses title case property keys
        COLUMN_MAP = {
            'name': 'Application Name',
            'domain': 'Domain',
            'region': 'Region',
            'sub_domain': 'Sub-Domain',
            'it_owner': 'It Owner',
            'description': 'Description',
            'tech_standard': 'Tech Standard',
            'hosting_type': 'Hosting Type',
            'vendor_support': 'Vendor Support',
            'risk_level': 'Risk Level',
            'business_criticality': 'Business Criticality',
            'administrator_team': 'Administrator Team',
            'disaster_recovery_tier': 'Disaster Recovery Tier',
            'application_short_code': 'Application Short Code',
            'roadmap_disposition': 'Roadmap Disposition',
            'planning_horizon': 'Planning Horizon',
        }

        def canonical(col_name: str) -> str:
            return COLUMN_MAP.get(col_name, col_name)

        # Find the application name column (raw header "name" or "application name")
        app_name_col = None
        for i, h in enumerate(headers):
            if h and h.lower() in ('name', 'application name'):
                app_name_col = i
                break

        if app_name_col is None:
            return {
                "success": False,
                "error": f"Application name column not found. Headers detected: {[h for h in headers if h]}"
            }

        # Build name → element_id lookup from elements.csv
        name_to_id = {
            elem['name'].lower().strip(): elem['id']
            for elem in self._load_existing_elements()
        }

        # Process catalogue rows
        wb = load_workbook(cat_path, data_only=True)
        ws = wb.active

        catalogue_props = []
        new_elements = []
        rows_matched = 0
        rows_created = 0

        for row in ws.iter_rows(min_row=data_start_row, values_only=True):
            raw_name = row[app_name_col]
            if raw_name is None or not str(raw_name).strip():
                continue

            app_name = str(raw_name).strip()
            element_id = name_to_id.get(app_name.lower())

            if element_id is None:
                # Create new element from catalogue row
                description_col = next(
                    (i for i, h in enumerate(headers) if h and h.lower() == 'description'), None
                )
                description = ''
                if description_col is not None and row[description_col] is not None:
                    description = str(row[description_col]).strip()

                element_id = self._generate_id(app_name)
                new_elements.append({
                    'id': element_id,
                    'type': 'ApplicationComponent',
                    'name': app_name,
                    'documentation': description,
                    'layer': 'application',
                    'category': 'ApplicationComponent',
                    'raw_data': {}
                })
                name_to_id[app_name.lower()] = element_id
                rows_created += 1
            else:
                rows_matched += 1

            for col_idx, header in enumerate(headers):
                if not header:
                    continue
                value = row[col_idx]
                if value is None or str(value).strip() in ('', 'nan', 'None'):
                    continue
                catalogue_props.append({
                    'element_id': element_id,
                    'key': canonical(header),
                    'value': str(value).strip()
                })

        wb.close()

        # Merge elements (new catalogue elements added to existing)
        existing_elements = self._load_existing_elements()
        merged_elements = self._merge_elements(existing_elements, new_elements)
        self._write_elements_csv(merged_elements)

        # Merge: existing first, then catalogue overwrites (catalogue is authoritative)
        existing_props = self._load_existing_properties()
        merged_props = self._merge_properties(existing_props, catalogue_props)

        # Write updated properties.csv
        self._write_properties_csv(merged_props)

        # Regenerate model.xml with updated properties
        elements = self._load_existing_elements()
        relations = self._load_existing_relations()

        views = []
        specs_dir = Path("ea_inputs/views")
        if specs_dir.exists() and list(specs_dir.glob("**/*.yaml")):
            from .view_builder import ViewBuilder
            result = ViewBuilder().generate_views_from_specs()
            view_defs = result.get('view_definitions', [])
            views = [ViewDefinition(
                id=v['id'],
                type='archimate-diagram-model',
                name=v['name'],
                documentation=v['documentation'],
                elements=v['elements'],
                relations=v['relations'],
                grouping=v.get('grouping'),
                layout=v.get('layout')
            ) for v in view_defs]

        self._write_archimate_xml(elements, relations, merged_props, views)

        return {
            "success": True,
            "catalogue": str(cat_path),
            "headers_detected": [h for h in headers if h],
            "rows_matched": rows_matched,
            "rows_created": rows_created,
            "properties_imported": len(catalogue_props),
            "total_properties": len(merged_props),
            "model_xml_updated": True
        }

    def _write_views_csv(self, views: List[ViewDefinition],
                        elements: List[Dict[str, Any]],
                        relations: List[Dict[str, Any]]) -> str:
        """Write views.csv with element positions"""

        output_file = self.output_dir / "views.csv"

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Type', 'Name', 'Documentation', 'Element', 'x', 'y', 'w', 'h'])

            for view in views:
                # Write view header
                writer.writerow([
                    view.id,
                    view.type,
                    view.name,
                    view.documentation,
                    '',  # Element
                    '',  # x
                    '',  # y
                    '',  # w
                    ''   # h
                ])

                # Get elements for this view
                view_elements = [e for e in elements if e['id'] in view.elements]
                view_relations = [r for r in relations if r['id'] in view.relations]

                # Choose layout algorithm
                layout = choose_layout(
                    view_type=view.name,
                    element_count=len(view_elements),
                    has_relationships=len(view_relations) > 0
                )

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
                for rel_id in view.relations:
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

        print(f"   {output_file}")
        print(f"\n Views Created:")
        for view in views:
            print(f"   - {view.name} ({len(view.elements)} elements)")

        return str(output_file)

    def _load_property_schema(self) -> Dict[str, List[str]]:
        """Load property schema from YAML file. Returns element type -> allowed properties map."""
        schema_file = self.output_dir / "property_schema.yaml"

        if not schema_file.exists():
            # Default schema if file doesn't exist (backward compatibility)
            return {}

        try:
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema = yaml.safe_load(f)
                if schema is None:
                    return {}
                # Normalize keys to lowercase for case-insensitive matching
                return {k.lower(): [attr.lower() for attr in v] if v else []
                        for k, v in schema.items()}
        except Exception as e:
            print(f"Warning: Could not load property schema: {e}")
            return {}

    def _is_property_allowed(self, element_type: str, property_key: str) -> bool:
        """Check if a property is allowed for an element type based on schema."""
        if not self.property_schema:
            # No schema loaded - allow all (backward compatibility)
            return True

        type_lower = element_type.lower()
        prop_lower = property_key.lower()

        # If element type not in schema, allow all properties
        if type_lower not in self.property_schema:
            return True

        # Check if property is in the allowlist for this type
        # Normalize underscores to spaces so snake_case CSV headers match schema names
        # e.g. "risk_level" matches "risk level" (from "Risk Level" in schema)
        prop_normalized = prop_lower.replace('_', ' ')
        allowed = self.property_schema[type_lower]
        return any(prop_normalized == attr.replace('_', ' ') for attr in allowed)

    def _generate_id(self, text: str) -> str:
        """Generate unique ID from text"""
        return f"id-{hashlib.md5(text.encode()).hexdigest()[:12]}"

    def _write_archimate_xml(self, elements: List[Dict[str, Any]], relations: List[Dict[str, Any]],
                             properties: List[Dict[str, Any]], views: List, use_ai_layout: bool = True) -> str:
        """
        Generate .archimate XML file for direct import into Archi tool

        Args:
            use_ai_layout: Whether to use AI-driven layout for grouped views (MVP7)

        Returns:
            Path to generated .archimate file
        """
        output_file = self.output_dir / "model.xml"

        # Create root model element with Open Group ArchiMate namespace
        root = ET.Element("model", {
            "xmlns": ARCHIMATE_NS,
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:schemaLocation": f"{ARCHIMATE_NS} http://www.opengroup.org/xsd/archimate/3.1/archimate3_Model.xsd",
            "identifier": self._generate_id("model")
        })

        # Add model name as first child element (required by schema)
        name_el = ET.SubElement(root, "name")
        name_el.text = "AI-Generated EA Model"

        # Build property map
        prop_map = {}
        prop_definitions = {}  # Map property keys to their definition IDs

        for p in properties:
            prop_map.setdefault(p['element_id'], []).append((p['key'], p['value']))
            # Track unique property keys for definitions
            if p['key'] not in prop_definitions:
                prop_definitions[p['key']] = self._generate_id(f"propdef-{p['key']}")

        # Create elements container (Model schema order: name -> elements -> relationships -> propertyDefinitions)
        elements_el = ET.SubElement(root, "elements")

        # Add all elements with properties
        for elem in elements:
            el = ET.SubElement(elements_el, "element", {
                "identifier": elem['id'],
                "xsi:type": elem['type']  # Use xsi:type for element type
            })

            # Add name as child element
            name_el = ET.SubElement(el, "name")
            name_el.text = elem['name']

            if elem.get('documentation'):
                doc_el = ET.SubElement(el, "documentation")
                doc_el.text = elem['documentation']

            # Add properties container if element has properties
            if elem['id'] in prop_map:
                props_container = ET.SubElement(el, "properties")
                for key, value in prop_map[elem['id']]:
                    # Reference the property definition
                    prop_el = ET.SubElement(props_container, "property", {
                        "propertyDefinitionRef": prop_definitions[key]
                    })
                    value_el = ET.SubElement(prop_el, "value")
                    value_el.text = value

        # Create relationships container only if we have relationships
        if relations:
            rels_el = ET.SubElement(root, "relationships")
            for rel in relations:
                rel_el = ET.SubElement(rels_el, "relationship", {
                    "identifier": rel['id'],
                    "xsi:type": rel['type'],
                    "source": rel['source_id'],
                    "target": rel['target_id']
                })

                if rel.get('name'):
                    name_el = ET.SubElement(rel_el, "name")
                    name_el.text = rel['name']

                if rel.get('documentation'):
                    doc_el = ET.SubElement(rel_el, "documentation")
                    doc_el.text = rel['documentation']

        # Create property definitions container (after relationships)
        if prop_definitions:
            propdefs_el = ET.SubElement(root, "propertyDefinitions")
            for key, def_id in prop_definitions.items():
                propdef = ET.SubElement(propdefs_el, "propertyDefinition", {
                    "identifier": def_id,
                    "type": "string"
                })
                ET.SubElement(propdef, "name").text = key

        # Add views container (after propertyDefinitions)
        if views:
            views_el = ET.SubElement(root, "views")

            # Add diagrams container inside views
            diagrams_el = ET.SubElement(views_el, "diagrams")

            # Element lookup for positions
            element_by_id = {e['id']: e for e in elements}

            for view in views:
                # Create view element inside diagrams container
                view_el = ET.SubElement(diagrams_el, "view", {
                    "identifier": view.id,
                    "xsi:type": "Diagram"
                })

                ET.SubElement(view_el, "name").text = view.name

                if view.documentation:
                    ET.SubElement(view_el, "documentation").text = view.documentation

                # Track node IDs for this view (for connection references)
                node_id_map = {}

                # Get view relations (needed for both branches)
                view_relations = [r for r in relations if r['id'] in view.relations]

                # Check if view has grouping configuration
                grouping_config = getattr(view, 'grouping', {}) if hasattr(view, 'grouping') else {}

                if grouping_config and 'by_property' in grouping_config:
                    # MVP7: Try AI-driven layout for grouped views if enabled
                    if use_ai_layout:
                        try:
                            # Use AI layout engine for nested grouping
                            print(f"  MVP7 Mode: Using AI layout for grouped view '{view.name}'")
                            self._write_ai_layout_xml(view_el, view, grouping_config, element_by_id, node_id_map, view_relations)
                        except Exception as e:
                            print(f"  MVP7 Layout failed, falling back to MVP6: {e}")
                            # Fall back to MVP6 rules-based
                            from .view_builder import ViewBuilder
                            vb = ViewBuilder()
                            groups = vb._organize_by_groups(view.elements, grouping_config)
                            is_nested = grouping_config.get('secondary_by_property') is not None
                            if is_nested:
                                self._write_nested_groups_xml(view_el, view, groups, grouping_config, element_by_id, node_id_map, vb)
                            else:
                                self._write_flat_groups_xml(view_el, view, groups, grouping_config, element_by_id, node_id_map, vb)
                    else:
                        # MVP6 Grouped Layout (rules-based)
                        from .view_builder import ViewBuilder
                        vb = ViewBuilder()
                        groups = vb._organize_by_groups(view.elements, grouping_config)
                        is_nested = grouping_config.get('secondary_by_property') is not None
                        if is_nested:
                            self._write_nested_groups_xml(view_el, view, groups, grouping_config, element_by_id, node_id_map, vb)
                        else:
                            self._write_flat_groups_xml(view_el, view, groups, grouping_config, element_by_id, node_id_map, vb)
                else:
                    # Standard flat layout (no grouping)
                    view_elements = [element_by_id[eid] for eid in view.elements if eid in element_by_id]

                    # Choose layout algorithm
                    from .archi_layouts import choose_layout
                    layout = choose_layout(
                        view_type=view.name,
                        element_count=len(view_elements),
                        has_relationships=len(view_relations) > 0
                    )

                    # Calculate positions
                    positions = layout.calculate_layout(view_elements, view_relations)
                    position_map = {p.element_id: p for p in positions}

                    # Add element nodes with positions
                    for elem_id in view.elements:
                        if elem_id not in element_by_id:
                            continue

                        pos = position_map.get(elem_id)
                        if not pos:
                            continue

                        # Generate unique node ID per view
                        node_id = self._generate_id(f"node-{view.id}-{elem_id}")
                        node_id_map[elem_id] = node_id

                        # Add position/size as attributes directly on node element
                        node_el = ET.SubElement(view_el, "node", {
                            "identifier": node_id,
                            "elementRef": elem_id,
                            "xsi:type": "Element",
                            "x": str(pos.x),
                            "y": str(pos.y),
                            "w": str(pos.w),
                            "h": str(pos.h)
                        })

                # Add connection elements (relationships)
                for rel in view_relations:
                    # Use the node IDs we created in this view
                    source_node_id = node_id_map.get(rel['source_id'])
                    target_node_id = node_id_map.get(rel['target_id'])

                    if not source_node_id or not target_node_id:
                        continue

                    conn_el = ET.SubElement(view_el, "connection", {
                        "identifier": self._generate_id(f"conn-{view.id}-{rel['id']}"),
                        "relationshipRef": rel['id'],
                        "xsi:type": "Relationship",
                        "source": source_node_id,
                        "target": target_node_id
                    })

        # Write XML file
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")  # Pretty print
        tree.write(output_file, encoding='utf-8', xml_declaration=True)

        print(f"   {output_file.resolve()}")
        return str(output_file)

    def _write_ai_layout_xml(self, view_el, view, grouping_config: Dict[str, Any],
                             element_by_id: Dict[str, Dict[str, Any]], node_id_map: Dict[str, str],
                             view_relations: List[Dict[str, Any]]) -> None:
        """
        MVP7: Write diagram layout using AI-driven spatial reasoning.

        Uses DiagramLayoutEngine to generate positions from YAML constraints.
        """
        from .archi_layout_ai import DiagramLayoutEngine, create_layout_data_for_view

        # Prepare layout data from view definition
        elements_list, groups_list, relationships_list, constraints = create_layout_data_for_view(
            {
                "elements": view.elements,
                "relations": view.relations,
                "grouping": grouping_config,
                "layout": getattr(view, 'layout', {}),
            },
            element_by_id,
            {r['id']: r for r in view_relations},
        )

        # Generate layout with AI
        layout_engine = DiagramLayoutEngine()
        diagram_xml_str = layout_engine.generate_layout(
            view_name=view.name,
            elements=elements_list,
            groups=groups_list,
            relationships=relationships_list,
            constraints=constraints,
        )

        # Parse AI-generated diagram XML and extract nodes/connections
        import xml.etree.ElementTree as ET
        diagram_root = ET.fromstring(diagram_xml_str)

        # Copy all nodes and connections from AI diagram into view_el
        for node in diagram_root.findall(".//node"):
            # Create deep copy of node
            node_copy = ET.Element(node.tag, node.attrib)
            for child in node:
                node_copy.append(ET.fromstring(ET.tostring(child)))
            view_el.append(node_copy)

            # Track node IDs for element references
            elem_ref = node.get("elementRef")
            if elem_ref:
                node_id_map[elem_ref] = node.get("identifier")

        # Copy all connections from AI diagram
        for conn in diagram_root.findall(".//connection"):
            conn_copy = ET.Element(conn.tag, conn.attrib)
            view_el.append(conn_copy)

    def _write_flat_groups_xml(self, view_el, view, groups: Dict[str, List[str]], grouping_config: Dict[str, Any],
                               element_by_id: Dict[str, Dict[str, Any]], node_id_map: Dict[str, str],
                               vb) -> None:
        """Write flat (single-level) grouping to XML"""
        group_width = grouping_config.get('group_width', 400)
        group_height = grouping_config.get('group_height', 300)
        group_spacing_x = grouping_config.get('group_spacing_x', 50)
        group_spacing_y = grouping_config.get('group_spacing_y', 50)
        group_order = grouping_config.get('order', sorted(groups.keys()))
        groups_per_row = grouping_config.get('groups_per_row', 3)

        x_offset = 20
        y_offset = 20

        for idx, group_name in enumerate(group_order):
            if group_name not in groups:
                continue

            # Calculate group position
            row = idx // groups_per_row
            col = idx % groups_per_row
            group_x = x_offset + col * (group_width + group_spacing_x)
            group_y = y_offset + row * (group_height + group_spacing_y)

            # Create group container node
            group_node_id = self._generate_id(f"group-{view.id}-{group_name}")
            group_node_el = ET.SubElement(view_el, "node", {
                "identifier": group_node_id,
                "xsi:type": "Container",
                "x": str(group_x),
                "y": str(group_y),
                "w": str(group_width),
                "h": str(group_height)
            })

            # Add label to group
            label_text = group_name if not group_name.startswith('_') else 'Other'
            ET.SubElement(group_node_el, "label").text = label_text

            # Get layout engine for elements within group
            layout_config = getattr(view, 'layout', {}) if hasattr(view, 'layout') else {}
            layout = vb._get_layout_engine(layout_config)

            # Layout elements within group
            group_elements = [element_by_id[eid] for eid in groups[group_name] if eid in element_by_id]
            group_positions = layout.calculate_layout(group_elements, [])

            # Add child nodes inside group container with ABSOLUTE coordinates
            padding = 20
            for pos in group_positions:
                node_id = self._generate_id(f"node-{view.id}-{pos.element_id}")
                node_id_map[pos.element_id] = node_id

                absolute_x = group_x + padding + pos.x
                absolute_y = group_y + padding + pos.y

                child_node_el = ET.SubElement(group_node_el, "node", {
                    "identifier": node_id,
                    "elementRef": pos.element_id,
                    "xsi:type": "Element",
                    "x": str(absolute_x),
                    "y": str(absolute_y),
                    "w": str(pos.w),
                    "h": str(pos.h)
                })

    def _write_nested_groups_xml(self, view_el, view, nested_groups: Dict[str, Dict[str, List[str]]],
                                 grouping_config: Dict[str, Any], element_by_id: Dict[str, Dict[str, Any]],
                                 node_id_map: Dict[str, str], vb) -> None:
        """Write nested two-level grouping to XML (primary -> secondary containers with elements)"""
        group_width = grouping_config.get('group_width', 400)
        group_height = grouping_config.get('group_height', 300)
        group_spacing_x = grouping_config.get('group_spacing_x', 50)
        group_spacing_y = grouping_config.get('group_spacing_y', 50)
        primary_order = grouping_config.get('order', sorted(nested_groups.keys()))
        groups_per_row = grouping_config.get('groups_per_row', 3)

        x_offset = 20
        y_offset = 20

        for idx, primary_name in enumerate(primary_order):
            if primary_name not in nested_groups:
                continue

            # Calculate primary group position
            row = idx // groups_per_row
            col = idx % groups_per_row
            primary_x = x_offset + col * (group_width + group_spacing_x)
            primary_y = y_offset + row * (group_height + group_spacing_y)

            # Create primary group container
            primary_node_id = self._generate_id(f"primary-{view.id}-{primary_name}")
            primary_node_el = ET.SubElement(view_el, "node", {
                "identifier": primary_node_id,
                "xsi:type": "Container",
                "x": str(primary_x),
                "y": str(primary_y),
                "w": str(group_width),
                "h": str(group_height)
            })

            # Add label for primary group
            label_text = primary_name if not primary_name.startswith('_') else 'Other'
            ET.SubElement(primary_node_el, "label").text = label_text

            # Collect all elements with secondary grouping
            all_elements_with_notes = []
            secondary_note_positions = {}

            padding = 20
            current_y = padding

            # Get layout engine
            layout_config = getattr(view, 'layout', {}) if hasattr(view, 'layout') else {}
            layout = vb._get_layout_engine(layout_config)

            # Process each secondary group within this primary group
            for secondary_name, element_ids in sorted(nested_groups[primary_name].items()):
                # Add Note element for sub-domain (visual separator)
                note_id = self._generate_id(f"note-{view.id}-{primary_name}-{secondary_name}")
                note_element_id = self._generate_id(f"note-element-{primary_name}-{secondary_name}")

                # Position note at the top of secondary group
                note_x = primary_x + padding
                note_y = primary_y + current_y
                secondary_note_positions[secondary_name] = (note_x, note_y)
                current_y += 70  # Space for note

                # Create label node (MVP7 fix: use Label not Note)
                label_node_el = ET.SubElement(primary_node_el, "node", {
                    "identifier": note_id,
                    "xsi:type": "Label",
                    "x": str(note_x),
                    "y": str(note_y),
                    "w": str(300),
                    "h": str(50)
                })
                ET.SubElement(label_node_el, "label").text = secondary_name if not secondary_name.startswith('_') else 'Other'

                # Add styling for label
                style_el = ET.SubElement(label_node_el, "style")
                ET.SubElement(style_el, "fillColor", {
                    "r": "240", "g": "240", "b": "240", "a": "100"
                })
                ET.SubElement(style_el, "lineColor", {
                    "r": "100", "g": "100", "b": "100", "a": "100"
                })
                font_el = ET.SubElement(style_el, "font", {"name": "Arial", "size": "11"})
                ET.SubElement(font_el, "color", {"r": "0", "g": "0", "b": "0"})

                # Layout elements within this secondary group
                group_elements = [element_by_id[eid] for eid in element_ids if eid in element_by_id]
                if group_elements:
                    group_positions = layout.calculate_layout(group_elements, [])

                    # Add element nodes under secondary group
                    for pos in group_positions:
                        node_id = self._generate_id(f"node-{view.id}-{pos.element_id}")
                        node_id_map[pos.element_id] = node_id

                        # Position relative to primary group and below note
                        absolute_x = primary_x + padding + pos.x
                        absolute_y = primary_y + current_y + pos.y

                        child_node_el = ET.SubElement(primary_node_el, "node", {
                            "identifier": node_id,
                            "elementRef": pos.element_id,
                            "xsi:type": "Element",
                            "x": str(absolute_x),
                            "y": str(absolute_y),
                            "w": str(pos.w),
                            "h": str(pos.h)
                        })

                    # Add space after secondary group
                    current_y += max(p.y + p.h for p in group_positions) + 30

    def _write_diagrams_xml(self, views: List[ViewDefinition],
                            elements: List[Dict[str, Any]],
                            relations: List[Dict[str, Any]]) -> str:
        """
        Generate ArchiMate Diagram Exchange XML for views

        Returns:
            Path to generated diagrams.xml file
        """
        output_file = self.output_dir / "diagrams.xml"

        # Create root element with ArchiMate namespace
        root = ET.Element("model", {
            "xmlns": ARCHIMATE_NS,
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:schemaLocation": f"{ARCHIMATE_NS} http://www.opengroup.org/xsd/archimate/3.1/archimate3_Diagram.xsd",
            "identifier": self._generate_id("diagram-model")
        })

        # Add model name
        name_el = ET.SubElement(root, "name")
        name_el.text = "AI-Generated Diagrams"

        # Element lookup for positions
        element_by_id = {e['id']: e for e in elements}

        # Create views container
        for view in views:
            # Create view element
            view_el = ET.SubElement(root, "view", {
                "identifier": view.id,
                "xsi:type": "Diagram"
            })

            ET.SubElement(view_el, "name").text = view.name

            if view.documentation:
                ET.SubElement(view_el, "documentation").text = view.documentation

            # Get layout for this view
            view_elements = [element_by_id[eid] for eid in view.elements if eid in element_by_id]
            view_relations = [r for r in relations if r['id'] in view.relations]

            # Choose layout algorithm
            from .archi_layouts import choose_layout
            layout = choose_layout(
                view_type=view.name,
                element_count=len(view_elements),
                has_relationships=len(view_relations) > 0
            )

            # Calculate positions
            positions = layout.calculate_layout(view_elements, view_relations)
            position_map = {p.element_id: p for p in positions}

            # Add element nodes with positions
            for elem_id in view.elements:
                if elem_id not in element_by_id:
                    continue

                pos = position_map.get(elem_id)
                if not pos:
                    continue

                node_el = ET.SubElement(view_el, "node", {
                    "identifier": self._generate_id(f"node-{elem_id}"),
                    "elementRef": elem_id,
                    "xsi:type": "Element"
                })

                # Add bounds (position and size)
                bounds_el = ET.SubElement(node_el, "bounds", {
                    "x": str(pos.x),
                    "y": str(pos.y),
                    "width": str(pos.w),
                    "height": str(pos.h)
                })

            # Add connection elements (relationships)
            for rel in view_relations:
                conn_el = ET.SubElement(view_el, "connection", {
                    "identifier": self._generate_id(f"conn-{rel['id']}"),
                    "relationshipRef": rel['id'],
                    "xsi:type": "Relationship",
                    "source": self._generate_id(f"node-{rel['source_id']}"),
                    "target": self._generate_id(f"node-{rel['target_id']}")
                })

        # Write XML file
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(output_file, encoding='utf-8', xml_declaration=True)

        print(f"   {output_file.resolve()}")
        return str(output_file)
