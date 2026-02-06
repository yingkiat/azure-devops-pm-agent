"""
View Finalizer - Preview + Validate views before generation (MVP6+)

Hybrid approach:
1. Python validation: Quick data quality checks
2. LLM interview: Conversational approval flow

Provides deterministic validation while keeping generation approval interactive.
"""

from typing import Dict, List, Any, Set, Tuple
from dataclasses import dataclass, field
import pandas as pd
from pathlib import Path


@dataclass
class ViewValidation:
    """Results of validating a single view"""
    view_name: str
    is_valid: bool
    element_count: int
    relationship_count: int
    issues: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    preview: Dict[str, Any] = field(default_factory=dict)


class ViewFinalizer:
    """Previews and validates views before generation"""

    def __init__(self, archi_inputs_dir: str = "archi_inputs"):
        self.archi_dir = Path(archi_inputs_dir)
        self.elements = self._load_elements()
        self.relations = self._load_relations()
        self.properties = self._load_properties()

        # Create lookup indexes
        self.element_by_id = {e['id']: e for e in self.elements}
        self.properties_by_element = self._index_properties()

    def _load_elements(self) -> List[Dict[str, Any]]:
        """Load elements from elements.csv"""
        elements_file = self.archi_dir / "elements.csv"
        if not elements_file.exists():
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
            return []

        df = pd.read_csv(relations_file)
        relations = []
        for _, row in df.iterrows():
            relations.append({
                'id': row['ID'],
                'type': row['Type'],
                'name': row.get('Name', ''),
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

    def _index_properties(self) -> Dict[str, Dict[str, str]]:
        """Index properties by element ID for fast lookup"""
        indexed = {}
        for prop in self.properties:
            elem_id = prop['element_id']
            if elem_id not in indexed:
                indexed[elem_id] = {}
            indexed[elem_id][prop['key']] = prop['value']
        return indexed

    def finalize_view(
        self,
        view_name: str,
        selected_element_ids: List[str],
        selected_relation_ids: List[str],
        grouping_config: Dict[str, Any],
        spec_file_name: str = None
    ) -> ViewValidation:
        """
        Validate and preview a single view

        Args:
            view_name: Name of the view
            selected_element_ids: Elements selected by WHERE clause
            selected_relation_ids: Relationships selected for view
            grouping_config: Grouping configuration from YAML spec
            spec_file_name: Name of YAML spec file (for reference)

        Returns:
            ViewValidation with issues, warnings, and preview
        """
        validation = ViewValidation(
            view_name=view_name,
            element_count=len(selected_element_ids),
            relationship_count=len(selected_relation_ids),
            is_valid=True
        )

        # Check 1: Empty view
        if not selected_element_ids:
            validation.is_valid = False
            validation.issues.append({
                'severity': 'error',
                'code': 'EMPTY_VIEW',
                'message': f"View '{view_name}' has no elements (WHERE clause matched nothing)",
                'spec_file': spec_file_name
            })
            return validation

        # Check 2: Check for duplicate elements
        if len(selected_element_ids) != len(set(selected_element_ids)):
            unique_ids = set(selected_element_ids)
            duplicates = [id for id in selected_element_ids if selected_element_ids.count(id) > 1]
            validation.is_valid = False
            validation.issues.append({
                'severity': 'error',
                'code': 'DUPLICATE_ELEMENTS',
                'message': f"View '{view_name}' contains {len(duplicates)} duplicate element IDs",
                'element_ids': duplicates,
                'spec_file': spec_file_name
            })

        # Check 3: Validate grouping properties
        if grouping_config and 'by_property' in grouping_config:
            primary_prop = grouping_config['by_property']
            secondary_prop = grouping_config.get('secondary_by_property')

            # Check primary grouping property
            missing_primary = self._find_elements_missing_property(
                selected_element_ids, primary_prop
            )

            if missing_primary:
                validation.warnings.append({
                    'severity': 'warning',
                    'code': 'MISSING_GROUPING_PROPERTY',
                    'message': f"View '{view_name}': {len(missing_primary)} elements missing primary grouping property '{primary_prop}'",
                    'property': primary_prop,
                    'element_count': len(missing_primary),
                    'element_ids': missing_primary[:5],
                    'note': 'These elements will be placed in "_ungrouped"'
                })

            # Check secondary grouping property if applicable
            if secondary_prop:
                missing_secondary = self._find_elements_missing_property(
                    selected_element_ids, secondary_prop
                )

                if missing_secondary:
                    validation.warnings.append({
                        'severity': 'warning',
                        'code': 'MISSING_SECONDARY_PROPERTY',
                        'message': f"View '{view_name}': {len(missing_secondary)} elements missing secondary grouping property '{secondary_prop}'",
                        'property': secondary_prop,
                        'element_count': len(missing_secondary),
                        'element_ids': missing_secondary[:5],
                        'note': 'These elements will be placed in "_ungrouped" sub-groups'
                    })

        # Check 4: Check for orphaned elements (no relationships)
        element_ids_set = set(selected_element_ids)
        relation_ids_set = set(selected_relation_ids)

        elements_with_rels = set()
        for rel_id in selected_relation_ids:
            rel = next((r for r in self.relations if r['id'] == rel_id), None)
            if rel:
                if rel['source_id'] in element_ids_set:
                    elements_with_rels.add(rel['source_id'])
                if rel['target_id'] in element_ids_set:
                    elements_with_rels.add(rel['target_id'])

        orphaned_elements = element_ids_set - elements_with_rels
        if orphaned_elements and len(selected_relation_ids) > 0:
            # Only warn if there ARE relationships but some elements aren't connected
            validation.warnings.append({
                'severity': 'warning',
                'code': 'ORPHANED_ELEMENTS',
                'message': f"View '{view_name}': {len(orphaned_elements)} elements have no relationships",
                'element_count': len(orphaned_elements),
                'element_ids': list(orphaned_elements)[:5],
                'note': 'Unconnected elements may indicate missing relationships'
            })

        # Build preview
        validation.preview = {
            'view_name': view_name,
            'element_count': len(selected_element_ids),
            'element_types': self._get_element_types(selected_element_ids),
            'relationship_count': len(selected_relation_ids),
            'sample_elements': self._get_sample_elements(selected_element_ids, 15),
            'has_grouping': bool(grouping_config and 'by_property' in grouping_config),
            'grouping_properties': {
                'primary': grouping_config.get('by_property') if grouping_config else None,
                'secondary': grouping_config.get('secondary_by_property') if grouping_config else None
            },
            'property_distribution': self._get_property_distribution(selected_element_ids)
        }

        return validation

    def _find_elements_missing_property(
        self,
        element_ids: List[str],
        property_key: str
    ) -> List[str]:
        """Find elements that don't have a specific property"""
        missing = []
        for elem_id in element_ids:
            if elem_id not in self.properties_by_element:
                missing.append(elem_id)
            elif property_key not in self.properties_by_element[elem_id]:
                missing.append(elem_id)
        return missing

    def _get_element_types(self, element_ids: List[str]) -> Dict[str, int]:
        """Count elements by type"""
        types = {}
        for elem_id in element_ids:
            elem = self.element_by_id.get(elem_id)
            if elem:
                elem_type = elem['type']
                types[elem_type] = types.get(elem_type, 0) + 1
        return types

    def _get_sample_elements(self, element_ids: List[str], limit: int = 15) -> List[Dict[str, Any]]:
        """Get sample of elements with their properties"""
        samples = []
        for elem_id in element_ids[:limit]:
            elem = self.element_by_id.get(elem_id)
            if elem:
                props = self.properties_by_element.get(elem_id, {})
                samples.append({
                    'id': elem_id,
                    'name': elem['name'],
                    'type': elem['type'],
                    'properties': props
                })
        return samples

    def _get_property_distribution(self, element_ids: List[str]) -> Dict[str, Dict[str, int]]:
        """Show distribution of key properties (Region, Sub-Domain, etc)"""
        distribution = {}
        key_properties = ['Region', 'Domain', 'Sub-Domain', 'Lifecycle Status']

        for key in key_properties:
            values = {}
            for elem_id in element_ids:
                props = self.properties_by_element.get(elem_id, {})
                if key in props:
                    value = props[key]
                    values[value] = values.get(value, 0) + 1

            if values:
                distribution[key] = values

        return distribution

    def format_validation_report(self, validations: List[ViewValidation]) -> str:
        """
        Format validation results for console display

        Returns:
            Human-readable report
        """
        lines = []
        lines.append("\n" + "=" * 90)
        lines.append("VIEW FINALIZATION - VALIDATION & PREVIEW")
        lines.append("=" * 90)

        # Summary
        total_views = len(validations)
        valid_views = sum(1 for v in validations if v.is_valid)
        total_issues = sum(len(v.issues) for v in validations)
        total_warnings = sum(len(v.warnings) for v in validations)

        lines.append(f"\nSUMMARY:")
        lines.append(f"  Views Processed:    {total_views}")
        lines.append(f"  Valid:              {valid_views}")
        lines.append(f"  Issues:             {total_issues}")
        lines.append(f"  Warnings:           {total_warnings}")

        # Details for each view
        lines.append("\n" + "-" * 90)

        for i, val in enumerate(validations, 1):
            status = "✓ VALID" if val.is_valid else "✗ INVALID"
            lines.append(f"\nVIEW {i}: {status} - {val.view_name}")

            # Summary line
            lines.append(f"  Elements: {val.element_count} | Relationships: {val.relationship_count}")

            # Preview
            if val.preview:
                # Element types
                type_str = ", ".join(f"{count}x {type}" for type, count in val.preview['element_types'].items())
                lines.append(f"  Element Types: {type_str}")

                # Grouping info
                if val.preview['has_grouping']:
                    primary = val.preview['grouping_properties']['primary']
                    secondary = val.preview['grouping_properties']['secondary']
                    if secondary:
                        lines.append(f"  Grouping: Primary by '{primary}' → Secondary by '{secondary}'")
                    else:
                        lines.append(f"  Grouping: By '{primary}'")

                # Property distribution
                if val.preview['property_distribution']:
                    lines.append(f"  Property Distribution:")
                    for prop, values in val.preview['property_distribution'].items():
                        dist_str = ", ".join(f"{v}:{c}" for v, c in sorted(values.items()))
                        lines.append(f"    {prop}: {dist_str}")

                # Sample elements
                if val.preview['sample_elements']:
                    lines.append(f"  Sample Elements (showing {min(5, len(val.preview['sample_elements']))} of {val.element_count}):")
                    for sample in val.preview['sample_elements'][:5]:
                        lines.append(f"    • {sample['name']} ({sample['type']})")

            # Issues
            if val.issues:
                lines.append(f"  ✗ ISSUES ({len(val.issues)}):")
                for issue in val.issues:
                    lines.append(f"    [{issue['code']}] {issue['message']}")

            # Warnings
            if val.warnings:
                lines.append(f"  ⚠ WARNINGS ({len(val.warnings)}):")
                for warn in val.warnings:
                    lines.append(f"    [{warn['code']}] {warn['message']}")
                    if 'note' in warn:
                        lines.append(f"      → {warn['note']}")

        lines.append("\n" + "=" * 90 + "\n")

        return "\n".join(lines)

    def should_proceed_with_generation(self, validations: List[ViewValidation]) -> bool:
        """Determine if view generation should proceed based on critical issues"""
        has_critical_issues = any(
            issue['severity'] == 'error'
            for val in validations
            for issue in val.issues
        )
        return not has_critical_issues
