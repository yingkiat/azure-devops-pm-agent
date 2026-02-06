"""
Shared Element Selection Logic (MVP9 Enhancement)

Common logic for selecting elements and applying property overrides.
Used by both archi_generator.py (ArchiMate XML/CSV) and drawio_generator.py (draw.io).

Key features:
- Hybrid selection: name, where (criteria), id
- Property overrides from view specs
- Fuzzy name matching
- Consistent behavior across output formats
- MVP9 Data Stocktake: Creates synthetic diagram elements for missing names
"""

import csv
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Set


class ElementSelector:
    """
    Handles element selection and property overrides for view specifications.

    Supports:
    - Name-based selection: name: "Microsoft Dynamics CRM"
    - Criteria-based selection: where: {type: "ApplicationComponent", Horizon: "H3"}
    - ID-based selection: id: "id-abc123"
    - Property overrides: override: {Horizon: "H1", Process: "Customer Management"}
    """

    def __init__(self, elements: List[Dict[str, Any]], properties: List[Dict[str, Any]],
                 archi_dir: str = "archi_inputs"):
        """
        Initialize selector with EA data.

        Args:
            elements: List of element dicts with keys: id, type, name, documentation
            properties: List of property dicts with keys: element_id, key, value
            archi_dir: Directory for archi inputs (for persisting synthetic elements)
        """
        self.elements = elements
        self.properties = properties
        self.archi_dir = Path(archi_dir)

        # Load official element IDs (from elements.csv only, not diagram_elements.csv)
        self.official_ids = self._load_official_element_ids()

        # Create lookup indexes
        self.element_by_id = {e['id']: e for e in elements}
        self.element_by_name = {e['name']: e for e in elements}

        # Index properties by element ID
        self.properties_by_elem = {}
        for prop in properties:
            elem_id = prop['element_id']
            if elem_id not in self.properties_by_elem:
                self.properties_by_elem[elem_id] = {}
            self.properties_by_elem[elem_id][prop['key']] = prop['value']

        # Property overrides from view spec (element_id -> {property_key: value})
        # Reset for each new view/spec processing
        self.property_overrides: Dict[str, Dict[str, str]] = {}

        # Track synthetic elements created during selection (for persistence)
        self.synthetic_elements: List[Dict[str, Any]] = []
        self.synthetic_properties: List[Dict[str, Any]] = []

    def _load_official_element_ids(self) -> Set[str]:
        """Load IDs from elements.csv only (official EA model)."""
        official_ids = set()
        elements_file = self.archi_dir / "elements.csv"
        if elements_file.exists():
            with open(elements_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    official_ids.add(row['ID'])
        return official_ids

    def select_elements(self, elements_config: Dict[str, Any]) -> List[str]:
        """
        Select elements based on hybrid selection criteria.

        MVP9 Data Stocktake:
        - Elements found in elements.csv or diagram_elements.csv are used directly
        - Elements NOT found are created as synthetic diagram elements
        - Synthetic elements are persisted to diagram_elements.csv and diagram_properties.csv

        Args:
            elements_config: Dict with 'include' list of rules

        Returns:
            List of element IDs

        Example:
            elements_config = {
                'include': [
                    {'name': 'Microsoft Dynamics CRM', 'override': {'Horizon': 'H3'}},
                    {'where': {'type': 'ApplicationComponent', 'Domain': 'Sales'}},
                    {'id': 'id-abc123'}
                ]
            }
        """
        # Reset for new selection
        self.property_overrides = {}
        self.synthetic_elements = []
        self.synthetic_properties = []

        selected_ids = set()
        include_rules = elements_config.get('include', [])
        official_count = 0
        synthetic_count = 0

        # Handle legacy format: direct 'where' at top level
        if not include_rules and 'where' in elements_config:
            include_rules = [{'where': elements_config['where']}]

        for rule in include_rules:
            if 'where' in rule:
                # Criteria-based selection
                matched = self._filter_by_criteria(rule['where'])
                selected_ids.update(e['id'] for e in matched)
                official_count += len(matched)

            elif 'name' in rule:
                # Name-based selection
                name = rule['name']
                elem_id = None
                if name in self.element_by_name:
                    elem_id = self.element_by_name[name]['id']
                    official_count += 1
                else:
                    # Try fuzzy matching
                    matched = self._fuzzy_match_name(name)
                    if matched:
                        elem_id = matched['id']
                        official_count += 1
                    else:
                        # MVP9: Create synthetic diagram element
                        elem_id = self._create_synthetic_element(name, rule)
                        synthetic_count += 1

                if elem_id:
                    selected_ids.add(elem_id)
                    # Capture property overrides if specified
                    if 'override' in rule:
                        if elem_id not in self.property_overrides:
                            self.property_overrides[elem_id] = {}
                        self.property_overrides[elem_id].update(rule['override'])

            elif 'id' in rule:
                # ID-based selection
                elem_id = rule['id']
                if elem_id in self.element_by_id:
                    selected_ids.add(elem_id)
                    official_count += 1
                    # Capture property overrides if specified
                    if 'override' in rule:
                        if elem_id not in self.property_overrides:
                            self.property_overrides[elem_id] = {}
                        self.property_overrides[elem_id].update(rule['override'])
                else:
                    print(f"      Element ID not found: {elem_id}")

        # Print data stocktake report
        self._print_stocktake(len(include_rules), official_count, synthetic_count)

        # Persist synthetic elements to diagram_elements.csv and diagram_properties.csv
        if self.synthetic_elements:
            self._persist_synthetic_elements()

        return list(selected_ids)

    def _create_synthetic_element(self, name: str, rule: Dict[str, Any]) -> str:
        """
        Create a synthetic diagram element for a name not found in the model.

        Args:
            name: Element name from YAML spec
            rule: YAML rule with optional 'override' and 'type'

        Returns:
            Generated element ID
        """
        # Generate deterministic ID from name
        elem_id = f"diagram-{hashlib.md5(name.encode()).hexdigest()[:12]}"

        # Infer type from rule or default to ApplicationComponent
        elem_type = rule.get('type', 'ApplicationComponent')

        # Create synthetic element
        synthetic_elem = {
            'id': elem_id,
            'type': elem_type,
            'name': name,
            'documentation': f'Diagram element (not in official EA model)'
        }

        # Add to internal lookups so it can be used immediately
        self.element_by_id[elem_id] = synthetic_elem
        self.element_by_name[name] = synthetic_elem
        self.elements.append(synthetic_elem)

        # Track for persistence
        self.synthetic_elements.append(synthetic_elem)

        # Extract properties from override (for persistence)
        if 'override' in rule:
            for key, value in rule['override'].items():
                self.synthetic_properties.append({
                    'element_id': elem_id,
                    'key': key,
                    'value': str(value)
                })
                # Also add to properties index
                if elem_id not in self.properties_by_elem:
                    self.properties_by_elem[elem_id] = {}
                self.properties_by_elem[elem_id][key] = str(value)

        print(f"      Created synthetic element: {name} ({elem_type})")
        return elem_id

    def _print_stocktake(self, total: int, official: int, synthetic: int) -> None:
        """Print MVP9 data stocktake report."""
        print("\n" + "="*60)
        print("MVP9 DATA STOCKTAKE")
        print("="*60)
        print(f"YAML Spec Elements: {total}")
        print(f"  - In elements.csv (official): {official}")
        print(f"  - Created as diagram elements: {synthetic}")
        if synthetic > 0:
            print(f"\n  Synthetic elements will be saved to diagram_elements.csv")
        print("="*60 + "\n")

    def _persist_synthetic_elements(self) -> None:
        """Persist synthetic elements to diagram_elements.csv and diagram_properties.csv."""
        diagram_elements_file = self.archi_dir / "diagram_elements.csv"
        diagram_properties_file = self.archi_dir / "diagram_properties.csv"

        # Load existing IDs to avoid duplicates
        existing_ids = set()
        if diagram_elements_file.exists():
            with open(diagram_elements_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    existing_ids.add(row['ID'])

        # Filter out already-existing elements
        new_elements = [e for e in self.synthetic_elements if e['id'] not in existing_ids]

        # Append new elements
        if new_elements:
            file_exists = diagram_elements_file.exists() and diagram_elements_file.stat().st_size > 0
            with open(diagram_elements_file, 'a', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['ID', 'Type', 'Name', 'Documentation'])
                if not file_exists:
                    writer.writeheader()
                for elem in new_elements:
                    writer.writerow({
                        'ID': elem['id'],
                        'Type': elem['type'],
                        'Name': elem['name'],
                        'Documentation': elem.get('documentation', '')
                    })
            print(f"  Saved {len(new_elements)} new elements to diagram_elements.csv")

        # Load existing properties to avoid duplicates
        existing_props = set()
        if diagram_properties_file.exists():
            with open(diagram_properties_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    existing_props.add((row['ID'], row['Key']))

        # Filter out already-existing properties
        new_properties = [p for p in self.synthetic_properties
                         if (p['element_id'], p['key']) not in existing_props]

        # Append new properties
        if new_properties:
            file_exists = diagram_properties_file.exists() and diagram_properties_file.stat().st_size > 0
            with open(diagram_properties_file, 'a', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['ID', 'Key', 'Value'])
                if not file_exists:
                    writer.writeheader()
                for prop in new_properties:
                    writer.writerow({
                        'ID': prop['element_id'],
                        'Key': prop['key'],
                        'Value': prop['value']
                    })
            print(f"  Saved {len(new_properties)} new properties to diagram_properties.csv")

    def get_element_property(self, elem_id: str, property_key: str) -> Optional[str]:
        """
        Get property value for an element, with override support.
        Overrides from view spec take precedence over base data.

        Args:
            elem_id: Element ID
            property_key: Property name (e.g., "Horizon", "Process", "Domain")

        Returns:
            Property value or None if not found
        """
        # Check overrides first
        if elem_id in self.property_overrides:
            if property_key in self.property_overrides[elem_id]:
                return self.property_overrides[elem_id][property_key]

        # Fall back to base properties
        elem_props = self.properties_by_elem.get(elem_id, {})
        return elem_props.get(property_key)

    def enrich_elements_with_properties(self, element_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Enrich element dicts with their properties (including overrides).

        Args:
            element_ids: List of element IDs

        Returns:
            List of element dicts with added 'properties' field
        """
        enriched = []
        for elem_id in element_ids:
            elem = self.element_by_id.get(elem_id)
            if not elem:
                continue

            # Start with base properties
            props = dict(self.properties_by_elem.get(elem_id, {}))

            # Apply overrides
            if elem_id in self.property_overrides:
                props.update(self.property_overrides[elem_id])

            # Create enriched element
            enriched_elem = {**elem, 'properties': props}
            enriched.append(enriched_elem)

        return enriched

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
        elem_props = self.properties_by_elem.get(element_id, {})

        # Check each property criteria
        for key, value in criteria.items():
            if key in ['type', 'name_contains']:
                continue  # Skip non-property criteria

            # Property key might need formatting
            # Criteria uses "Lifecycle Status" but we store as "Lifecycle Status"
            if key not in elem_props:
                return False

            # Check value match
            if isinstance(value, list):
                # Multiple allowed values
                if elem_props[key] not in value:
                    return False
            elif isinstance(value, str):
                # Single value (case-insensitive contains)
                if value.lower() not in elem_props[key].lower():
                    return False

        return True

    def _fuzzy_match_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Try to fuzzy match element name using similarity threshold"""
        from difflib import SequenceMatcher

        name_lower = name.lower()

        # Try exact match first (case-insensitive)
        for elem in self.elements:
            if elem['name'].lower() == name_lower:
                return elem

        # Try fuzzy match with 0.85 similarity threshold
        # This avoids matching "W3 Sirius" to "W3 Sirius Extension (DHR)"
        best_match = None
        best_ratio = 0.85

        for elem in self.elements:
            elem_name_lower = elem['name'].lower()
            ratio = SequenceMatcher(None, name_lower, elem_name_lower).ratio()

            if ratio > best_ratio:
                best_ratio = ratio
                best_match = elem

        return best_match
