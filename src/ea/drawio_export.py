"""
Draw.IO Export Module (MVP8 + MVP9)

Generates deterministic draw.io XML diagrams from EA layout data.
Provides programmatic baseline diagram generation for manual refinement in draw.io.

MVP9 additions:
- Emphasis treatments: prominent, faded, highlighted, normal
- Applied via visual.emphasis in YAML spec
"""

from dataclasses import dataclass
import hashlib
from typing import List, Dict, Optional, Tuple
from lxml import etree


# Lifecycle status colors (priority 1)
LIFECYCLE_COLORS = {
    "Strategic": "#81C784",   # Green
    "Maintain": "#FFB74D",    # Orange
    "Sunset": "#E57373",      # Red
    "New": "#64B5F6",         # Light blue
}

# ArchiMate layer colors (standard notation)
LAYER_COLORS = {
    "Strategy": "#F5DEAA",    # Beige/tan
    "Business": "#FFFFB5",    # Yellow
    "Application": "#B5D4E8", # Light blue
    "Technology": "#C9E7CB",  # Light green
    "Physical": "#F2D1C9",    # Light pink/salmon
    "Motivation": "#CCCCFF",  # Light purple
    "Implementation": "#FFE0E0",  # Light red
}

# Element type to ArchiMate layer mapping
ELEMENT_LAYERS = {
    # Application layer
    "ApplicationComponent": "Application",
    "ApplicationService": "Application",
    "ApplicationInterface": "Application",
    "ApplicationFunction": "Application",
    "ApplicationProcess": "Application",
    "ApplicationEvent": "Application",
    "ApplicationInteraction": "Application",
    "ApplicationCollaboration": "Application",
    "DataObject": "Application",
    # Business layer
    "BusinessProcess": "Business",
    "BusinessFunction": "Business",
    "BusinessService": "Business",
    "BusinessActor": "Business",
    "BusinessRole": "Business",
    "BusinessEvent": "Business",
    "BusinessObject": "Business",
    "BusinessInterface": "Business",
    "BusinessCollaboration": "Business",
    "BusinessInteraction": "Business",
    "Contract": "Business",
    "Product": "Business",
    "Representation": "Business",
    # Strategy layer
    "Capability": "Strategy",
    "Resource": "Strategy",
    "CourseOfAction": "Strategy",
    "ValueStream": "Strategy",
    # Technology layer
    "TechnologyService": "Technology",
    "TechnologyFunction": "Technology",
    "TechnologyProcess": "Technology",
    "TechnologyInterface": "Technology",
    "TechnologyEvent": "Technology",
    "TechnologyInteraction": "Technology",
    "TechnologyCollaboration": "Technology",
    "Node": "Technology",
    "Device": "Technology",
    "SystemSoftware": "Technology",
    "Path": "Technology",
    "CommunicationNetwork": "Technology",
    "Artifact": "Technology",
    # Physical layer
    "Equipment": "Physical",
    "Facility": "Physical",
    "DistributionNetwork": "Physical",
    "Material": "Physical",
    # Motivation layer
    "Stakeholder": "Motivation",
    "Driver": "Motivation",
    "Assessment": "Motivation",
    "Goal": "Motivation",
    "Outcome": "Motivation",
    "Principle": "Motivation",
    "Requirement": "Motivation",
    "Constraint": "Motivation",
    "Meaning": "Motivation",
    "Value": "Motivation",
    # Implementation layer
    "WorkPackage": "Implementation",
    "Deliverable": "Implementation",
    "ImplementationEvent": "Implementation",
    "Plateau": "Implementation",
    "Gap": "Implementation",
}

# Relationship line styles for draw.io
RELATIONSHIP_STYLES = {
    "Serving": {"dashed": "0", "endArrow": "open", "startArrow": "none"},
    "Flow": {"dashed": "1", "endArrow": "classic", "startArrow": "none"},
    "Composition": {"dashed": "0", "endArrow": "diamondThin", "startArrow": "none", "endFill": "1"},
    "Aggregation": {"dashed": "0", "endArrow": "diamondThin", "startArrow": "none", "endFill": "0"},
    "Realization": {"dashed": "1", "endArrow": "block", "startArrow": "none", "endFill": "0"},
    "Assignment": {"dashed": "0", "endArrow": "block", "startArrow": "oval", "endFill": "1", "startFill": "1"},
    "Access": {"dashed": "1", "endArrow": "open", "startArrow": "none"},
    "Influence": {"dashed": "1", "endArrow": "open", "startArrow": "none"},
    "Triggering": {"dashed": "0", "endArrow": "classic", "startArrow": "none"},
    "Association": {"dashed": "0", "endArrow": "none", "startArrow": "none"},
    "Specialization": {"dashed": "0", "endArrow": "block", "startArrow": "none", "endFill": "0"},
}

# Legacy colors (kept for backward compatibility)
ARCHIMATE_COLORS = {
    "ApplicationComponent": "#B3E5FC",  # Light blue
    "ApplicationInterface": "#FFE082",  # Light yellow
    "DataObject": "#C8E6C9",            # Light green
    "BusinessProcess": "#F8BBD0",       # Light pink
    "Capability": "#D1C4E9",            # Light purple
    "TechnologyService": "#FFCCBC",     # Light orange
    "Infrastructure": "#D7CCC8",        # Light brown
}

DEFAULT_COLOR = "#B3B3B3"  # Gray

# MVP9: Emphasis treatments for visual differentiation
EMPHASIS_STYLES = {
    "prominent": {
        "strokeWidth": "3",
        "strokeColor": "#2E7D32",  # Dark green
        "opacity": "100",
        "fontStyle": "1",  # Bold
    },
    "faded": {
        "strokeWidth": "1",
        "strokeColor": "#999999",
        "opacity": "50",
        "fontColor": "#666666",
    },
    "highlighted": {
        "strokeWidth": "3",
        "strokeColor": "#1976D2",  # Blue
        "opacity": "100",
        "shadow": "1",
    },
    "normal": {},  # Default styling, no modifications
}


@dataclass
class DrawIOElement:
    """Positioned element in draw.io diagram."""
    id: str
    name: str
    x: int
    y: int
    width: int = 120
    height: int = 60
    elem_type: str = "ApplicationComponent"
    parent_id: Optional[str] = None
    color: str = DEFAULT_COLOR
    emphasis: str = "normal"  # MVP9: prominent, faded, highlighted, normal


@dataclass
class DrawIOContainer:
    """Swimlane or container (region, domain, etc.)."""
    id: str
    label: str
    x: int
    y: int
    width: int
    height: int
    parent_id: Optional[str] = None
    style: Optional[str] = None  # Custom style override


@dataclass
class DrawIOEdge:
    """Connection between elements."""
    from_id: str
    to_id: str
    label: str = ""
    edge_type: str = "Serving"
    style_overrides: Optional[Dict[str, str]] = None


class DrawIOExporter:
    """Generate deterministic draw.io XML from EA layout data."""

    CANVAS_WIDTH = 2000
    CANVAS_HEIGHT = 1500

    def __init__(self):
        self.mxfile = None
        self.diagram = None
        self.root_cell = None
        self.cell_counter = 2  # Cells 0 and 1 are reserved

    def export(self,
               elements: List[DrawIOElement],
               edges: List[DrawIOEdge],
               containers: Optional[List[DrawIOContainer]] = None,
               view_name: str = "Diagram") -> str:
        """
        Generate draw.io XML.

        Args:
            elements: Positioned elements
            edges: Connections between elements
            containers: Optional swimlanes/containers for grouping
            view_name: Name of the diagram

        Returns:
            XML string (UTF-8, pretty-printed)
        """
        self._init_mxfile(view_name)

        # Add containers (swimlanes) first if provided
        if containers:
            for container in sorted(containers, key=lambda c: c.id):
                self._add_container(container)

        # Add elements
        for elem in sorted(elements, key=lambda e: e.id):
            self._add_element(elem)

        # Add edges (relationships)
        for edge in sorted(edges, key=lambda e: (e.from_id, e.to_id)):
            self._add_edge(edge)

        # Generate XML string
        xml_str = etree.tostring(
            self.mxfile,
            pretty_print=True,
            encoding='unicode'
        )
        # Add XML declaration manually
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str

    def _init_mxfile(self, view_name: str) -> None:
        """Initialize draw.io XML structure."""
        self.mxfile = etree.Element('mxfile')
        self.mxfile.set('host', 'app.diagrams.net')
        self.mxfile.set('modified', '2025-01-01T00:00:00.000Z')
        self.mxfile.set('version', '24.0.0')
        self.mxfile.set('type', 'device')

        self.diagram = etree.SubElement(self.mxfile, 'diagram')
        self.diagram.set('name', view_name)

        model = etree.SubElement(self.diagram, 'mxGraphModel')
        model.set('dx', '1200')
        model.set('dy', '800')
        model.set('grid', '1')
        model.set('gridSize', '10')
        model.set('guides', '1')
        model.set('tooltips', '1')
        model.set('connect', '1')
        model.set('arrows', '1')
        model.set('fold', '1')
        model.set('page', '1')
        model.set('pageScale', '1')
        model.set('pageWidth', str(self.CANVAS_WIDTH))
        model.set('pageHeight', str(self.CANVAS_HEIGHT))
        model.set('background', '#FFFFFF')
        model.set('math', '0')
        model.set('shadow', '0')

        self.root_cell = etree.SubElement(model, 'root')

        # Add required base cells
        parent0 = etree.SubElement(self.root_cell, 'mxCell')
        parent0.set('id', '0')

        parent1 = etree.SubElement(self.root_cell, 'mxCell')
        parent1.set('id', '1')
        parent1.set('parent', '0')

        self.cell_counter = 2

    def _add_container(self, container: DrawIOContainer) -> None:
        """Add a swimlane/container."""
        cell_id = str(self.cell_counter)
        self.cell_counter += 1

        cell = etree.SubElement(self.root_cell, 'mxCell')
        cell.set('id', container.id)
        cell.set('value', container.label)
        # Use custom style if provided, otherwise default swimlane style
        style = container.style or ('swimlane;startSize=40;fillColor=none;'
                                    'strokeColor=#CCCCCC;rounded=0;fontSize=12;fontStyle=1')
        cell.set('style', style)
        cell.set('vertex', '1')
        cell.set('parent', container.parent_id or '1')

        geo = etree.SubElement(cell, 'mxGeometry')
        geo.set('x', str(container.x))
        geo.set('y', str(container.y))
        geo.set('width', str(container.width))
        geo.set('height', str(container.height))
        geo.set('as', 'geometry')

    def _add_element(self, elem: DrawIOElement) -> None:
        """Add an application/element as a rounded box with optional emphasis styling."""
        cell = etree.SubElement(self.root_cell, 'mxCell')
        cell.set('id', elem.id)
        cell.set('value', elem.name)
        cell.set('vertex', '1')
        cell.set('parent', elem.parent_id or '1')

        # Base style: rounded box with colors
        style_parts = [
            'rounded=1',
            'whiteSpace=wrap',
            'html=1',
            f'fillColor={elem.color}',
            'strokeColor=#666666',
            'fontSize=11',
            'fontFamily=Verdana',
            'aspect=fixed',
        ]

        # MVP9: Apply emphasis styling
        emphasis_style = EMPHASIS_STYLES.get(elem.emphasis, {})
        if emphasis_style:
            if 'strokeWidth' in emphasis_style:
                style_parts.append(f"strokeWidth={emphasis_style['strokeWidth']}")
            if 'strokeColor' in emphasis_style:
                # Override default stroke color
                style_parts = [s for s in style_parts if not s.startswith('strokeColor=')]
                style_parts.append(f"strokeColor={emphasis_style['strokeColor']}")
            if 'opacity' in emphasis_style:
                style_parts.append(f"opacity={emphasis_style['opacity']}")
            if 'fontStyle' in emphasis_style:
                style_parts.append(f"fontStyle={emphasis_style['fontStyle']}")
            if 'fontColor' in emphasis_style:
                style_parts.append(f"fontColor={emphasis_style['fontColor']}")
            if 'shadow' in emphasis_style:
                style_parts.append(f"shadow={emphasis_style['shadow']}")

        style = ';'.join(style_parts) + ';'
        cell.set('style', style)

        geo = etree.SubElement(cell, 'mxGeometry')
        geo.set('x', str(elem.x))
        geo.set('y', str(elem.y))
        geo.set('width', str(elem.width))
        geo.set('height', str(elem.height))
        geo.set('as', 'geometry')

    def _add_edge(self, edge: DrawIOEdge) -> None:
        """Add a connection between two elements with relationship-specific styling."""
        edge_key = f'{edge.from_id}|{edge.to_id}|{edge.edge_type}|{edge.label}'
        edge_suffix = hashlib.md5(edge_key.encode('utf-8')).hexdigest()[:10]
        cell_id = f'{edge.from_id}_to_{edge.to_id}_{edge_suffix}'

        cell = etree.SubElement(self.root_cell, 'mxCell')
        cell.set('id', cell_id)
        cell.set('value', edge.label)
        cell.set('edge', '1')
        cell.set('parent', '1')
        cell.set('source', edge.from_id)
        cell.set('target', edge.to_id)

        # Style: use relationship-specific styling
        style = get_relationship_style(edge.edge_type)
        if edge.style_overrides:
            style = style[:-1] + ';' + ''.join(f"{k}={v};" for k, v in edge.style_overrides.items())
        cell.set('style', style)

        geo = etree.SubElement(cell, 'mxGeometry')
        geo.set('relative', '1')
        geo.set('as', 'geometry')


def get_element_color(element_dict: Dict, lifecycle_property: Optional[str] = None) -> str:
    """
    Determine fill color based on element properties.

    Priority:
    1. Lifecycle Status property (Strategic, Maintain, Sunset, New)
    2. ArchiMate layer color based on element type
    3. Default gray

    Args:
        element_dict: Element data (must have 'type' key)
        lifecycle_property: Value of "Lifecycle Status" property, if available

    Returns:
        Color hex code
    """
    # Priority 1: Lifecycle Status property (if provided and known)
    if lifecycle_property and lifecycle_property in LIFECYCLE_COLORS:
        return LIFECYCLE_COLORS[lifecycle_property]

    # Priority 2: ArchiMate layer color based on element type
    elem_type = element_dict.get('type', 'ApplicationComponent')
    layer = ELEMENT_LAYERS.get(elem_type)
    if layer and layer in LAYER_COLORS:
        return LAYER_COLORS[layer]

    # Priority 3: Legacy type-specific color (backward compatibility)
    if elem_type in ARCHIMATE_COLORS:
        return ARCHIMATE_COLORS[elem_type]

    return DEFAULT_COLOR


def get_relationship_style(rel_type: str) -> str:
    """
    Get draw.io edge style for a relationship type.

    Args:
        rel_type: ArchiMate relationship type (Serving, Flow, etc.)

    Returns:
        draw.io style string
    """
    style_parts = [
        "edgeStyle=orthogonalEdgeStyle",
        "rounded=0",
        "orthogonalLoop=1",
        "jettySize=auto",
        "html=1",
        "strokeColor=#666666",
        "fontSize=10",
    ]

    # Get relationship-specific styling
    rel_style = RELATIONSHIP_STYLES.get(rel_type, {})
    if rel_style:
        if "dashed" in rel_style:
            style_parts.append(f"dashed={rel_style['dashed']}")
        if "endArrow" in rel_style:
            style_parts.append(f"endArrow={rel_style['endArrow']}")
        if "startArrow" in rel_style:
            style_parts.append(f"startArrow={rel_style['startArrow']}")
        if "endFill" in rel_style:
            style_parts.append(f"endFill={rel_style['endFill']}")
        if "startFill" in rel_style:
            style_parts.append(f"startFill={rel_style['startFill']}")

    return ";".join(style_parts) + ";"


def calculate_element_width(name: str, min_width: int = 120, max_width: int = 300,
                           char_width: int = 8, padding: int = 20) -> int:
    """
    Calculate element width based on name length.

    Args:
        name: Element name
        min_width: Minimum width in pixels
        max_width: Maximum width in pixels
        char_width: Approximate width per character
        padding: Extra padding for margins

    Returns:
        Width in pixels
    """
    calculated = len(name) * char_width + padding
    return max(min_width, min(calculated, max_width))
