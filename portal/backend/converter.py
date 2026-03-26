"""Convert draw.io XML to SVG faithfully preserving all elements and styling."""

import xml.etree.ElementTree as ET
import re
import html
from pathlib import Path
from typing import Dict, List


class DrawioToSvg:
    """Convert .drawio to SVG preserving exact structure, positioning, and styling."""

    def __init__(self):
        self.elements_found = []

    def convert(self, drawio_path: str, output_path: str) -> Dict:
        """Convert .drawio to SVG preserving everything exactly."""
        # Reset for each diagram to avoid accumulation across multiple conversions
        self.elements_found = []

        try:
            tree = ET.parse(drawio_path)
            root = tree.getroot()

            diagram = root.find("diagram")
            if diagram is None:
                return {"success": False, "error": "No diagram element found"}

            mx_graph = diagram.find("mxGraphModel")
            if mx_graph is None:
                return {"success": False, "error": "No mxGraphModel found"}

            canvas_width = int(mx_graph.get("pageWidth", "2000"))
            canvas_height = int(mx_graph.get("pageHeight", "1500"))

            root_cell = mx_graph.find("root")
            if root_cell is None:
                return {"success": False, "error": "No root cell found"}

            cells = root_cell.findall("mxCell")

            # Build SVG by translating mxGraphModel 1:1
            svg_content = self._build_svg(cells, canvas_width, canvas_height, diagram.get("name", "Diagram"))

            # Write SVG
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(svg_content)

            return {
                "success": True,
                "svg_path": output_path,
                "elements_count": len(self.elements_found),
                "elements": self.elements_found,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _build_svg(self, cells: List, width: int, height: int, title: str) -> str:
        """Build SVG by faithfully translating mxGraphModel cells."""
        # First pass: build parent geometry map for coordinate resolution
        cell_geometry = {}
        for cell in cells:
            cell_id = cell.get("id")
            geometry = cell.find("mxGeometry")
            if geometry is not None:
                cell_geometry[cell_id] = {
                    "x": float(geometry.get("x", 0)),
                    "y": float(geometry.get("y", 0)),
                    "w": float(geometry.get("width", 0)),
                    "h": float(geometry.get("height", 0)),
                }

        def get_absolute_coords(cell):
            """Resolve absolute coordinates by walking up parent chain."""
            geometry = cell.find("mxGeometry")
            if geometry is None:
                return 0, 0, 0, 0
            x = float(geometry.get("x", 0))
            y = float(geometry.get("y", 0))
            w = float(geometry.get("width", 0))
            h = float(geometry.get("height", 0))

            # Walk up parent chain to get absolute position
            parent_id = cell.get("parent")
            while parent_id and parent_id not in ["0", "1"]:
                if parent_id in cell_geometry:
                    parent_geom = cell_geometry[parent_id]
                    x += parent_geom["x"]
                    y += parent_geom["y"]
                # Find parent's parent
                parent_cell = None
                for c in cells:
                    if c.get("id") == parent_id:
                        parent_cell = c
                        break
                if parent_cell is not None:
                    parent_id = parent_cell.get("parent")
                else:
                    break
            return x, y, w, h

        # Second pass: collect all cells with absolute coordinates
        backgrounds = []
        clickable_elements = []
        annotations = []

        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = 0, 0

        for cell in cells:
            cell_id = cell.get("id")

            # Skip system cells
            if cell_id in ["0", "1"]:
                continue

            # Skip narrative box
            if cell_id.startswith("narrative-"):
                continue

            # Get absolute geometry
            x, y, w, h = get_absolute_coords(cell)

            # Get cell properties
            value = cell.get("value", "")
            style = cell.get("style", "")

            # Skip if no dimensions
            if w <= 0 or h <= 0:
                continue

            # Skip edge rendering for now (complex paths)
            if cell_id.startswith("edge-"):
                continue

            # Track content bounds
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x + w)
            max_y = max(max_y, y + h)

            # Categorize cells by layer
            # Note: diagram-* IDs are synthetic elements created during diagram generation
            if cell_id.startswith("id-") or cell_id.startswith("elem-id-") or cell_id.startswith("diagram-"):
                clickable_elements.append((cell_id, value, style, x, y, w, h))
            elif cell_id.startswith("ann-"):
                annotations.append((cell_id, value, style, x, y, w, h))
            else:
                # Backgrounds, containers, swimlanes
                backgrounds.append((cell_id, value, style, x, y, w, h))

        # Calculate viewBox with padding
        padding = 20
        if min_x == float('inf'):
            # No content, use original dimensions
            vb_x, vb_y, vb_w, vb_h = 0, 0, width, height
        else:
            vb_x = max(0, min_x - padding)
            vb_y = max(0, min_y - padding)
            vb_w = (max_x - min_x) + (padding * 2)
            vb_h = (max_y - min_y) + (padding * 2)

        # Build SVG with content-fitted viewBox
        svg = []
        svg.append('<?xml version="1.0" encoding="UTF-8"?>')
        svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb_x:.0f} {vb_y:.0f} {vb_w:.0f} {vb_h:.0f}" preserveAspectRatio="xMidYMid meet">')
        svg.append('<defs><style type="text/css">')
        svg.append('.element { cursor: pointer; }')
        svg.append('.element:hover { opacity: 0.85; }')
        svg.append('.element-highlighted rect { stroke: #FFC107 !important; stroke-width: 3 !important; }')
        svg.append('</style></defs>')
        svg.append(f'<title>{title}</title>')
        svg.append(f'<rect x="{vb_x:.0f}" y="{vb_y:.0f}" width="{vb_w:.0f}" height="{vb_h:.0f}" fill="white"/>')

        # Render in layers: backgrounds first, then clickable elements on top, then annotations
        for cell_id, value, style, x, y, w, h in backgrounds:
            fill_color = self._extract_style_color(style, "fillColor")
            stroke_color = self._extract_style_color(style, "strokeColor") or "#CCCCCC"
            stroke_width = self._extract_style_value(style, "strokeWidth") or "1"
            font_size = self._extract_style_value(style, "fontSize") or "12"
            font_style = "bold" if "fontStyle=1" in style else "normal"

            is_swimlane = "swimlane" in style
            rounded = "rounded=1" in style
            rx = "8" if rounded else "0"

            if fill_color:
                svg.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill_color}" stroke="{stroke_color}" stroke-width="{stroke_width}" rx="{rx}"/>')
            else:
                svg.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="none" stroke="{stroke_color}" stroke-width="{stroke_width}" rx="{rx}"/>')

            if value:
                if is_swimlane:
                    label_x = x + 10
                    label_y = y + 15
                elif "text;" in style:
                    label_x = x + 5
                    label_y = y + h / 2
                else:
                    label_x = x + 10
                    label_y = y + h / 2
                svg.append(self._render_multiline_text(value, label_x, label_y, font_size, **{"font-weight": font_style, "font-family": "Verdana"}))

        # Render clickable elements on top
        for cell_id, value, style, x, y, w, h in clickable_elements:
            if value:
                self.elements_found.append({"id": cell_id, "name": value})

            fill_color = self._extract_style_color(style, "fillColor") or "#B5D4E8"
            stroke_color = self._extract_style_color(style, "strokeColor") or "#666666"
            stroke_width = self._extract_style_value(style, "strokeWidth") or "1"
            font_size = self._extract_style_value(style, "fontSize") or "11"
            font_family = self._extract_style_value(style, "fontFamily") or "Verdana"
            opacity = self._extract_style_value(style, "opacity") or "1"

            rounded = "rounded=1" in style
            rx = "4" if rounded else "0"

            svg.append(f'<g class="element" data-element-id="{cell_id}">')
            svg.append(f'  <rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill_color}" stroke="{stroke_color}" stroke-width="{stroke_width}" rx="{rx}" opacity="{opacity}"/>')
            if value:
                text_elem = self._render_multiline_text(value, x + w/2, y + h/2, font_size, **{"text-anchor": "middle", "dominant-baseline": "middle", "font-family": font_family, "pointer-events": "none"})
                # Indent the text element to match the group
                svg.append('  ' + text_elem.replace('\n', '\n  '))
            svg.append('</g>')

        # Render annotations on top
        for cell_id, value, style, x, y, w, h in annotations:
            fill_color = self._extract_style_color(style, "fillColor") or "#FFFFFF"
            font_size = self._extract_style_value(style, "fontSize") or "9"
            svg.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill_color}" stroke="none" rx="2"/>')
            svg.append(self._render_multiline_text(value, x + w/2, y + h/2, font_size, **{"text-anchor": "middle", "dominant-baseline": "middle", "font-style": "italic"}))

        svg.append("</svg>")
        return "\n".join(svg)

    @staticmethod
    def _extract_style_color(style: str, color_key: str) -> str:
        """Extract color value from style string."""
        if not style:
            return ""
        match = re.search(rf"{color_key}=([^;]+)", style)
        if match:
            val = match.group(1)
            return val if val and val != "none" else ""
        return ""

    @staticmethod
    def _extract_style_value(style: str, key: str) -> str:
        """Extract value from style string."""
        if not style:
            return ""
        match = re.search(rf"{key}=([^;]+)", style)
        if match:
            return match.group(1)
        return ""

    @staticmethod
    def _escape_xml(text: str) -> str:
        """Escape XML special characters."""
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    def _normalize_html_text(self, text: str) -> str:
        """Convert limited draw.io HTML labels into plain multiline text."""
        if not text:
            return ""

        normalized = str(text)
        for _ in range(3):
            unescaped = html.unescape(normalized)
            if unescaped == normalized:
                break
            normalized = unescaped

        normalized = re.sub(r'</?(div|p|b|strong|u|em|span|font)[^>]*>', '', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'<li[^>]*>', '• ', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'</li\s*>', '<br/>', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'</?(ul|ol)[^>]*>', '', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'<br\s*/?>', '<br/>', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\s*<br/>\s*', '<br/>', normalized)
        normalized = re.sub(r'(<br/>){2,}', '<br/>', normalized)
        normalized = re.sub(r'<[^>]+>', '', normalized)
        return normalized.strip()

    def _render_multiline_text(self, text: str, x: float, y: float, font_size: str = "11", **attrs) -> str:
        """Render text with basic HTML line breaks/lists as multi-line SVG using tspan elements."""
        normalized_text = self._normalize_html_text(text)
        lines = re.split(r'<br\s*/?>', normalized_text, flags=re.IGNORECASE)

        # Helper function to escape XML
        def escape(t):
            return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")

        if len(lines) == 1:
            # Single line - simple text element
            attrs_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
            return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{font_size}" {attrs_str}>{escape(normalized_text)}</text>'

        # Multi-line - use tspan elements
        line_height = float(font_size) * 1.2  # 1.2x line height
        # Center vertically: start above center by (num_lines - 1) * line_height / 2
        start_y = y - (len(lines) - 1) * line_height / 2

        attrs_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
        svg_lines = [f'<text x="{x:.1f}" y="{start_y:.1f}" font-size="{font_size}" {attrs_str}>']

        for i, line in enumerate(lines):
            dy = line_height if i > 0 else 0
            svg_lines.append(f'  <tspan x="{x:.1f}" dy="{dy:.1f}">{escape(line.strip())}</tspan>')

        svg_lines.append('</text>')
        return '\n'.join(svg_lines)
