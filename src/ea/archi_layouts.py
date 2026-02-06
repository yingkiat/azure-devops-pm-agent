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


@dataclass
class ContainerPosition:
    """Position data for a container (swimlane/group) in a view"""
    container_id: str
    label: str
    x: int
    y: int
    w: int
    h: int
    parent_id: str = None  # For nested containers


@dataclass
class MatrixLayoutResult:
    """Complete matrix layout including containers and elements"""
    row_headers: List[ContainerPosition]
    column_headers: List[ContainerPosition]
    cells: List[ContainerPosition]  # Each cell is a container for elements
    elements: List[ElementPosition]


class MatrixLayout(LayoutEngine):
    """
    Matrix layout with row headers (primary grouping) and column headers (secondary grouping).

    Creates a table-like structure:

                    | Col 1          | Col 2          | Col 3          |
    ----------------|----------------|----------------|----------------|
    Row 1           | [elements]     | [elements]     | [elements]     |
    ----------------|----------------|----------------|----------------|
    Row 2           | [elements]     | [elements]     | [elements]     |
    ----------------|----------------|----------------|----------------|
    """

    # Layout dimensions
    ROW_HEADER_WIDTH = 150
    COLUMN_HEADER_HEIGHT = 40
    CELL_MIN_WIDTH = 180
    CELL_MIN_HEIGHT = 100
    CELL_PADDING = 20

    def __init__(self,
                 row_height: int = 120,
                 column_width: int = 200,
                 spacing: int = 10):
        super().__init__(spacing_x=spacing, spacing_y=spacing)
        self.row_height = row_height
        self.column_width = column_width

    def calculate_matrix_layout(self,
                                 elements: List[Dict[str, Any]],
                                 grouped_elements: Dict[str, Dict[str, List[str]]],
                                 row_order: List[str] = None,
                                 column_order: List[str] = None,
                                 row_labels: Dict[str, str] = None) -> MatrixLayoutResult:
        """
        Calculate positions for a matrix layout.

        Args:
            elements: List of element dicts with 'id' keys
            grouped_elements: Dict of row_name -> Dict of col_name -> List of element_ids
            row_order: Ordered list of row names (primary groups)
            column_order: Ordered list of column names (secondary groups)
            row_labels: Optional display labels for rows (e.g., {"H1": "Today (AS-IS)"})

        Returns:
            MatrixLayoutResult with all container and element positions
        """
        # Build element lookup
        element_by_id = {e['id']: e for e in elements}

        # Determine row and column order
        all_rows = set(grouped_elements.keys())
        all_columns = set()
        for cols in grouped_elements.values():
            all_columns.update(cols.keys())

        # Apply ordering (specified order first, then remaining alphabetically)
        if row_order:
            rows = [r for r in row_order if r in all_rows]
            rows.extend(sorted(r for r in all_rows if r not in row_order))
        else:
            rows = sorted(all_rows)

        if column_order:
            columns = [c for c in column_order if c in all_columns]
            columns.extend(sorted(c for c in all_columns if c not in column_order))
        else:
            columns = sorted(all_columns)

        # Remove '_ungrouped' from display if present, add at end
        if '_ungrouped' in rows:
            rows.remove('_ungrouped')
            rows.append('_ungrouped')
        if '_ungrouped' in columns:
            columns.remove('_ungrouped')
            columns.append('_ungrouped')

        # Calculate cell sizes based on content
        cell_widths = {}
        cell_heights = {}

        for row in rows:
            max_height = self.CELL_MIN_HEIGHT
            for col in columns:
                elem_ids = grouped_elements.get(row, {}).get(col, [])
                elem_count = len(elem_ids)
                if elem_count > 0:
                    # Stack elements vertically in cell
                    needed_height = (elem_count * (self.ELEMENT_HEIGHT + 10)) + self.CELL_PADDING * 2
                    max_height = max(max_height, needed_height)
            cell_heights[row] = max(max_height, self.row_height)

        for col in columns:
            max_width = self.CELL_MIN_WIDTH
            for row in rows:
                elem_ids = grouped_elements.get(row, {}).get(col, [])
                for eid in elem_ids:
                    elem = element_by_id.get(eid, {})
                    name_len = len(elem.get('name', '')) * 8  # Approximate character width
                    max_width = max(max_width, name_len + self.CELL_PADDING * 2)
            cell_widths[col] = max(max_width, self.column_width)

        # Calculate positions
        row_headers = []
        column_headers = []
        cells = []
        element_positions = []

        # Starting positions
        start_x = 50
        start_y = 50

        # Create column headers
        col_x = start_x + self.ROW_HEADER_WIDTH + self.spacing_x
        for col in columns:
            col_label = col if col != '_ungrouped' else 'Other'
            column_headers.append(ContainerPosition(
                container_id=f"col-{col.lower().replace(' ', '-').replace('&', '')}",
                label=col_label,
                x=col_x,
                y=start_y,
                w=cell_widths[col],
                h=self.COLUMN_HEADER_HEIGHT
            ))
            col_x += cell_widths[col] + self.spacing_x

        # Create rows and cells
        row_y = start_y + self.COLUMN_HEADER_HEIGHT + self.spacing_y

        for row in rows:
            row_label = row_labels.get(row, row) if row_labels else row
            if row == '_ungrouped':
                row_label = 'Other'

            row_height = cell_heights[row]

            # Row header
            row_headers.append(ContainerPosition(
                container_id=f"row-{row.lower().replace(' ', '-')}",
                label=row_label,
                x=start_x,
                y=row_y,
                w=self.ROW_HEADER_WIDTH,
                h=row_height
            ))

            # Cells for this row
            cell_x = start_x + self.ROW_HEADER_WIDTH + self.spacing_x

            for col in columns:
                cell_id = f"cell-{row.lower().replace(' ', '-')}-{col.lower().replace(' ', '-').replace('&', '')}"

                cells.append(ContainerPosition(
                    container_id=cell_id,
                    label="",  # Cells don't need labels
                    x=cell_x,
                    y=row_y,
                    w=cell_widths[col],
                    h=row_height
                ))

                # Position elements in this cell
                elem_ids = grouped_elements.get(row, {}).get(col, [])
                elem_y = row_y + self.CELL_PADDING

                for eid in elem_ids:
                    elem = element_by_id.get(eid)
                    if elem:
                        # Calculate width based on name length
                        name_len = len(elem.get('name', ''))
                        elem_width = max(self.ELEMENT_WIDTH, min(name_len * 8, cell_widths[col] - self.CELL_PADDING * 2))

                        element_positions.append(ElementPosition(
                            element_id=eid,
                            x=cell_x + self.CELL_PADDING,
                            y=elem_y,
                            w=elem_width,
                            h=self.ELEMENT_HEIGHT
                        ))
                        elem_y += self.ELEMENT_HEIGHT + 10

                cell_x += cell_widths[col] + self.spacing_x

            row_y += row_height + self.spacing_y

        return MatrixLayoutResult(
            row_headers=row_headers,
            column_headers=column_headers,
            cells=cells,
            elements=element_positions
        )

    def calculate_layout(self, elements: List[Dict[str, Any]],
                        relations: List[Dict[str, Any]] = None) -> List[ElementPosition]:
        """Fallback to grid layout if called without grouping info."""
        return GridLayout(columns=4).calculate_layout(elements, relations)


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
