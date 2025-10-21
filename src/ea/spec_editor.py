"""
Spec Editor - YAML View Specification Editor (MVP6)

Provides tools for creating, editing, and managing view specifications.
Supports natural language operations: create, add, remove, replace.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
import re


class SpecEditor:
    """Editor for YAML view specifications"""

    def __init__(self, specs_dir: str = "ea_inputs/views", archi_dir: str = "archi_inputs"):
        self.specs_dir = Path(specs_dir)
        self.archi_dir = Path(archi_dir)
        self.specs_dir.mkdir(parents=True, exist_ok=True)

        # Load available elements for reference
        self._available_elements = self._load_available_elements()

    def _load_available_elements(self) -> List[Dict[str, str]]:
        """Load available elements from archi_inputs for reference"""
        import pandas as pd
        elements_file = self.archi_dir / "elements.csv"

        if not elements_file.exists():
            return []

        df = pd.read_csv(elements_file)
        return [
            {'id': row['ID'], 'name': row['Name'], 'type': row['Type']}
            for _, row in df.iterrows()
        ]

    def create_spec(self, view_name: str, description: str,
                    viewpoint: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new view specification

        Args:
            view_name: Name of the view
            description: Natural language description of what to include
            viewpoint: Optional ArchiMate viewpoint (e.g., "application_cooperation")

        Returns:
            Created spec dictionary
        """
        # Generate spec filename
        spec_filename = self._generate_filename(view_name)
        spec_path = self.specs_dir / spec_filename

        # Check if spec already exists
        if spec_path.exists():
            raise FileExistsError(f"View spec already exists: {spec_filename}")

        # Parse description to extract elements and relationships
        parsed = self._parse_description(description)

        # Create spec structure
        spec = {
            'view': {
                'name': view_name,
                'documentation': description
            },
            'elements': {
                'include': parsed['elements']
            },
            'relationships': {
                'include': parsed['relationships']
            },
            'layout': parsed.get('layout', {
                'algorithm': 'layered',
                'spacing_x': 50,
                'spacing_y': 80
            })
        }

        # Add viewpoint if specified
        if viewpoint:
            spec['view']['viewpoint'] = viewpoint

        # Write spec file
        self._write_spec(spec_path, spec)

        return {
            'spec_file': spec_filename,
            'spec_path': str(spec_path),
            'view_name': view_name,
            'spec': spec
        }

    def edit_spec(self, view_name: str, operation: str, element_name: str,
                  element_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Edit an existing view specification

        Args:
            view_name: Name of the view to edit
            operation: Operation to perform (add, remove, replace)
            element_name: Name of element to operate on
            element_type: Optional type filter for element

        Returns:
            Edit result dictionary
        """
        # Find spec file
        spec_path = self._find_spec_by_view_name(view_name)

        if not spec_path:
            raise FileNotFoundError(f"View spec not found: {view_name}")

        # Load existing spec
        spec = self._read_spec(spec_path)

        # Perform operation
        if operation.lower() == 'add':
            result = self._add_element(spec, element_name, element_type)
        elif operation.lower() == 'remove':
            result = self._remove_element(spec, element_name)
        elif operation.lower() == 'replace':
            # Replace expects element_name to be "old_name|new_name"
            if '|' in element_name:
                old_name, new_name = element_name.split('|', 1)
                result = self._replace_element(spec, old_name.strip(), new_name.strip())
            else:
                raise ValueError("Replace operation requires 'old_name|new_name' format")
        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Write updated spec
        self._write_spec(spec_path, spec)

        return {
            'spec_file': spec_path.name,
            'operation': operation,
            'element': element_name,
            'result': result,
            'spec': spec
        }

    def list_specs(self) -> List[Dict[str, Any]]:
        """List all view specifications"""
        specs = []

        for spec_file in self.specs_dir.glob("*.yaml"):
            try:
                spec = self._read_spec(spec_file)
                view_config = spec.get('view', {})

                # Count elements and relationships
                elements_count = len(spec.get('elements', {}).get('include', []))
                relationships_count = len(spec.get('relationships', {}).get('include', []))

                specs.append({
                    'name': view_config.get('name', spec_file.stem),
                    'file': spec_file.name,
                    'documentation': view_config.get('documentation', ''),
                    'viewpoint': view_config.get('viewpoint', 'N/A'),
                    'elements_count': elements_count,
                    'relationships_count': relationships_count
                })
            except Exception as e:
                print(f"  Failed to read {spec_file.name}: {e}")

        return specs

    def get_spec(self, view_name: str) -> Dict[str, Any]:
        """Get a specific view specification"""
        spec_path = self._find_spec_by_view_name(view_name)

        if not spec_path:
            raise FileNotFoundError(f"View spec not found: {view_name}")

        return self._read_spec(spec_path)

    def list_available_elements(self, element_type: Optional[str] = None) -> List[Dict[str, str]]:
        """List available elements that can be added to views"""
        if element_type:
            return [e for e in self._available_elements if e['type'] == element_type]
        return self._available_elements

    def _generate_filename(self, view_name: str) -> str:
        """Generate spec filename from view name"""
        # Convert to lowercase, replace spaces with underscores
        filename = view_name.lower().replace(' ', '_').replace('-', '_')
        # Remove non-alphanumeric characters except underscore
        filename = re.sub(r'[^a-z0-9_]', '', filename)
        return f"{filename}.yaml"

    def _find_spec_by_view_name(self, view_name: str) -> Optional[Path]:
        """Find spec file by view name"""
        # Try exact filename match
        spec_filename = self._generate_filename(view_name)
        spec_path = self.specs_dir / spec_filename

        if spec_path.exists():
            return spec_path

        # Try searching all specs
        for spec_file in self.specs_dir.glob("*.yaml"):
            spec = self._read_spec(spec_file)
            if spec.get('view', {}).get('name') == view_name:
                return spec_file

        return None

    def _read_spec(self, spec_path: Path) -> Dict[str, Any]:
        """Read YAML spec file"""
        with open(spec_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _write_spec(self, spec_path: Path, spec: Dict[str, Any]):
        """Write YAML spec file"""
        with open(spec_path, 'w', encoding='utf-8') as f:
            yaml.dump(spec, f, default_flow_style=False, sort_keys=False, indent=2)

    def _parse_description(self, description: str) -> Dict[str, Any]:
        """
        Parse natural language description to extract elements and relationships

        Example: "Show CRM, QAD, and purchase order flows"
        Returns: elements to include, relationship types
        """
        parsed = {
            'elements': [],
            'relationships': []
        }

        # Extract element names (look for capitalized words and known patterns)
        # This is a simple heuristic - can be enhanced with NLP
        words = description.split()

        # Look for known element names in available elements
        for element in self._available_elements:
            # Check if element name appears in description (case-insensitive)
            if element['name'].lower() in description.lower():
                parsed['elements'].append({
                    'name': element['name']
                })

        # Infer relationship types from keywords
        relationship_keywords = {
            'flow': ['Flow'],
            'integration': ['Flow', 'Serving'],
            'serve': ['Serving'],
            'access': ['Access'],
            'composition': ['Composition']
        }

        for keyword, rel_types in relationship_keywords.items():
            if keyword in description.lower():
                if not any(r.get('type') == rel_types for r in parsed['relationships']):
                    parsed['relationships'].append({
                        'type': rel_types,
                        'between': 'included_elements'
                    })

        # Default relationships if none specified
        if not parsed['relationships']:
            parsed['relationships'].append({
                'type': ['Serving', 'Flow'],
                'between': 'included_elements'
            })

        return parsed

    def _add_element(self, spec: Dict[str, Any], element_name: str,
                    element_type: Optional[str] = None) -> str:
        """Add element to spec"""
        include_list = spec.setdefault('elements', {}).setdefault('include', [])

        # Check if element already exists
        for item in include_list:
            if item.get('name') == element_name or item.get('id') == element_name:
                return f"Element already exists: {element_name}"

        # Find element in available elements
        element = self._find_element(element_name, element_type)

        if element:
            # Add by name (more readable)
            include_list.append({'name': element['name']})
            return f"Added element: {element['name']} ({element['type']})"
        else:
            # Element not found, add as criteria
            new_rule = {'name': element_name}
            if element_type:
                new_rule['type'] = element_type
            include_list.append(new_rule)
            return f"Added element reference: {element_name}"

    def _remove_element(self, spec: Dict[str, Any], element_name: str) -> str:
        """Remove element from spec"""
        include_list = spec.get('elements', {}).get('include', [])

        # Find and remove matching element
        for i, item in enumerate(include_list):
            if item.get('name') == element_name or item.get('id') == element_name:
                include_list.pop(i)
                return f"Removed element: {element_name}"

        return f"Element not found: {element_name}"

    def _replace_element(self, spec: Dict[str, Any], old_name: str, new_name: str) -> str:
        """Replace element in spec"""
        include_list = spec.get('elements', {}).get('include', [])

        # Find element
        element = self._find_element(new_name)

        # Find and replace matching element
        for i, item in enumerate(include_list):
            if item.get('name') == old_name or item.get('id') == old_name:
                if element:
                    include_list[i] = {'name': element['name']}
                    return f"Replaced {old_name} with {element['name']} ({element['type']})"
                else:
                    include_list[i] = {'name': new_name}
                    return f"Replaced {old_name} with {new_name}"

        return f"Element not found: {old_name}"

    def _find_element(self, name_or_id: str, element_type: Optional[str] = None) -> Optional[Dict[str, str]]:
        """Find element by name or ID"""
        # Try exact match by ID
        for element in self._available_elements:
            if element['id'] == name_or_id:
                if element_type and element['type'] != element_type:
                    continue
                return element

        # Try exact match by name (case-insensitive)
        for element in self._available_elements:
            if element['name'].lower() == name_or_id.lower():
                if element_type and element['type'] != element_type:
                    continue
                return element

        # Try partial match by name
        for element in self._available_elements:
            if name_or_id.lower() in element['name'].lower():
                if element_type and element['type'] != element_type:
                    continue
                return element

        return None


def main():
    """Test spec editor"""
    editor = SpecEditor()

    # List available elements
    print("Available elements:")
    for elem in editor.list_available_elements()[:5]:
        print(f"  - {elem['name']} ({elem['type']})")

    # Create a test spec
    print("\nCreating test spec...")
    result = editor.create_spec(
        view_name="CRM Integration Flow",
        description="Show Microsoft Dynamics, QAD EE, and Document Intelligence with flows"
    )
    print(f"  Created: {result['spec_file']}")

    # List all specs
    print("\nAll specs:")
    for spec in editor.list_specs():
        print(f"  - {spec['name']} ({spec['elements_count']} elements)")


if __name__ == '__main__':
    main()
