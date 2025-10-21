"""
Layout Algorithms for Archi Diagram Views

Provides intelligent positioning algorithms for ArchiMate elements:
- Grid Layout: Simple grid arrangement
- Hierarchical Layout: Top-down layered arrangement
- Layered Layout: EA layer-based positioning
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import math


@dataclass
class ElementPosition:
    """Position data for an element in a view"""
    element_id: str
    x: int
    y: int
    w: int
    h: int


class LayoutEngine:
    """Base class for layout algorithms"""

    # Standard element dimensions
    ELEMENT_WIDTH = 120
    ELEMENT_HEIGHT = 60

    def __init__(self, spacing_x: int = 40, spacing_y: int = 40):
        self.spacing_x = spacing_x
        self.spacing_y = spacing_y

    def calculate_layout(self, elements: List[Dict[str, Any]],
                        relations: List[Dict[str, Any]] = None) -> List[ElementPosition]:
        """Calculate positions for elements - override in subclasses"""
        raise NotImplementedError


class GridLayout(LayoutEngine):
    """Simple grid arrangement"""

    def __init__(self, columns: int = 3, spacing_x: int = 40, spacing_y: int = 40):
        super().__init__(spacing_x, spacing_y)
        self.columns = columns

    def calculate_layout(self, elements: List[Dict[str, Any]],
                        relations: List[Dict[str, Any]] = None) -> List[ElementPosition]:
        """Arrange elements in a grid"""
        positions = []

        for i, elem in enumerate(elements):
            row = i // self.columns
            col = i % self.columns

            positions.append(ElementPosition(
                element_id=elem['id'],
                x=col * (self.ELEMENT_WIDTH + self.spacing_x) + 20,
                y=row * (self.ELEMENT_HEIGHT + self.spacing_y) + 20,
                w=self.ELEMENT_WIDTH,
                h=self.ELEMENT_HEIGHT
            ))

        return positions


class HierarchicalLayout(LayoutEngine):
    """Top-down hierarchical arrangement based on relationships"""

    def __init__(self, spacing_x: int = 50, spacing_y: int = 80):
        super().__init__(spacing_x, spacing_y)

    def calculate_layout(self, elements: List[Dict[str, Any]],
                        relations: List[Dict[str, Any]] = None) -> List[ElementPosition]:
        """Arrange elements in hierarchical layers"""

        if not relations:
            # Fallback to grid if no relationships
            return GridLayout().calculate_layout(elements)

        # Build dependency graph
        element_ids = {elem['id'] for elem in elements}
        children = {elem['id']: set() for elem in elements}
        parents = {elem['id']: set() for elem in elements}

        for rel in relations:
            source = rel.get('source_id')
            target = rel.get('target_id')

            if source in element_ids and target in element_ids:
                # For hierarchical relationships (composition, realization, serving)
                rel_type = rel.get('relationship_type', '')
                if rel_type in ['Composition', 'Realization', 'Serving', 'Triggering']:
                    children[source].add(target)
                    parents[target].add(source)

        # Topological sort into levels
        levels = self._topological_levels(elements, parents, children)

        # Position elements by level
        positions = []
        for level_num, level_elements in enumerate(levels):
            level_width = len(level_elements) * (self.ELEMENT_WIDTH + self.spacing_x)
            start_x = 20  # Left margin

            for i, elem in enumerate(level_elements):
                positions.append(ElementPosition(
                    element_id=elem['id'],
                    x=start_x + i * (self.ELEMENT_WIDTH + self.spacing_x),
                    y=20 + level_num * (self.ELEMENT_HEIGHT + self.spacing_y),
                    w=self.ELEMENT_WIDTH,
                    h=self.ELEMENT_HEIGHT
                ))

        return positions

    def _topological_levels(self, elements: List[Dict[str, Any]],
                           parents: Dict[str, set],
                           children: Dict[str, set]) -> List[List[Dict[str, Any]]]:
        """Group elements into hierarchical levels"""

        # Find root nodes (no parents)
        roots = [elem for elem in elements if not parents[elem['id']]]

        if not roots:
            # No clear hierarchy - fallback to single level
            return [elements]

        levels = []
        visited = set()
        current_level = roots

        while current_level:
            levels.append(current_level)
            visited.update(elem['id'] for elem in current_level)

            # Find next level (children of current level)
            next_level = []
            for elem in current_level:
                for child_id in children[elem['id']]:
                    child_elem = next((e for e in elements if e['id'] == child_id), None)
                    if child_elem and child_id not in visited:
                        # Only add if all parents have been visited
                        if all(p in visited for p in parents[child_id]):
                            next_level.append(child_elem)

            current_level = next_level

        # Add any remaining elements not in hierarchy
        remaining = [elem for elem in elements if elem['id'] not in visited]
        if remaining:
            levels.append(remaining)

        return levels


class LayeredLayout(LayoutEngine):
    """EA layer-based positioning (Business, Application, Data, Infrastructure)"""

    LAYER_ORDER = ['business', 'application', 'data', 'infrastructure', 'security']

    def __init__(self, spacing_x: int = 40, spacing_y: int = 80):
        super().__init__(spacing_x, spacing_y)

    def calculate_layout(self, elements: List[Dict[str, Any]],
                        relations: List[Dict[str, Any]] = None) -> List[ElementPosition]:
        """Arrange elements by EA layer"""

        # Group elements by layer
        layers = {layer: [] for layer in self.LAYER_ORDER}
        unclassified = []

        for elem in elements:
            elem_type = elem.get('type', '').lower()
            layer = self._determine_layer(elem_type)

            if layer:
                layers[layer].append(elem)
            else:
                unclassified.append(elem)

        # Position elements
        positions = []
        current_y = 20

        for layer in self.LAYER_ORDER:
            layer_elements = layers[layer]
            if not layer_elements:
                continue

            # Arrange layer elements horizontally
            for i, elem in enumerate(layer_elements):
                positions.append(ElementPosition(
                    element_id=elem['id'],
                    x=20 + i * (self.ELEMENT_WIDTH + self.spacing_x),
                    y=current_y,
                    w=self.ELEMENT_WIDTH,
                    h=self.ELEMENT_HEIGHT
                ))

            current_y += self.ELEMENT_HEIGHT + self.spacing_y

        # Add unclassified elements at the end
        if unclassified:
            for i, elem in enumerate(unclassified):
                positions.append(ElementPosition(
                    element_id=elem['id'],
                    x=20 + i * (self.ELEMENT_WIDTH + self.spacing_x),
                    y=current_y,
                    w=self.ELEMENT_WIDTH,
                    h=self.ELEMENT_HEIGHT
                ))

        return positions

    def _determine_layer(self, element_type: str) -> str:
        """Determine EA layer from element type"""

        if any(t in element_type for t in ['business', 'actor', 'process', 'capability']):
            return 'business'
        elif any(t in element_type for t in ['application', 'component', 'service', 'interface']):
            return 'application'
        elif any(t in element_type for t in ['data', 'object']):
            return 'data'
        elif any(t in element_type for t in ['technology', 'node', 'device', 'network']):
            return 'infrastructure'
        elif 'security' in element_type:
            return 'security'

        return None


class CompactLayout(LayoutEngine):
    """Compact arrangement for small diagrams"""

    def __init__(self, max_width: int = 800):
        super().__init__(spacing_x=30, spacing_y=30)
        self.max_width = max_width

    def calculate_layout(self, elements: List[Dict[str, Any]],
                        relations: List[Dict[str, Any]] = None) -> List[ElementPosition]:
        """Arrange elements compactly within max width"""

        positions = []
        current_x = 20
        current_y = 20
        row_height = 0

        for elem in elements:
            # Check if we need to wrap to next row
            if current_x + self.ELEMENT_WIDTH > self.max_width:
                current_x = 20
                current_y += row_height + self.spacing_y
                row_height = 0

            positions.append(ElementPosition(
                element_id=elem['id'],
                x=current_x,
                y=current_y,
                w=self.ELEMENT_WIDTH,
                h=self.ELEMENT_HEIGHT
            ))

            current_x += self.ELEMENT_WIDTH + self.spacing_x
            row_height = max(row_height, self.ELEMENT_HEIGHT)

        return positions


class ColumnLayout(LayoutEngine):
    """Vertical column arrangement - stacks elements in a single column"""

    def __init__(self, spacing_x: int = 40, spacing_y: int = 40):
        super().__init__(spacing_x, spacing_y)

    def calculate_layout(self, elements: List[Dict[str, Any]],
                        relations: List[Dict[str, Any]] = None) -> List[ElementPosition]:
        """Arrange elements in a vertical column"""
        positions = []
        x = 20  # Left margin
        y = 20  # Top margin

        for elem in elements:
            positions.append(ElementPosition(
                element_id=elem['id'],
                x=x,
                y=y,
                w=self.ELEMENT_WIDTH,
                h=self.ELEMENT_HEIGHT
            ))
            # Move to next row (vertical stacking)
            y += self.ELEMENT_HEIGHT + self.spacing_y

        return positions


def choose_layout(view_type: str, element_count: int, has_relationships: bool = False) -> LayoutEngine:
    """Choose appropriate layout algorithm based on view characteristics"""

    # Business process views - hierarchical
    if 'process' in view_type.lower() and has_relationships:
        return HierarchicalLayout()

    # EA layer views - layered
    if any(layer in view_type.lower() for layer in ['overview', 'landscape', 'architecture']):
        return LayeredLayout()

    # Small diagrams - compact
    if element_count <= 6:
        return CompactLayout(max_width=500)

    # Medium diagrams - grid
    if element_count <= 12:
        return GridLayout(columns=3)

    # Large diagrams - grid with more columns
    return GridLayout(columns=4)
