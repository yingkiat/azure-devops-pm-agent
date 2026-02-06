"""
Generate application catalogues from ArchiMate knowledge base.
Supports flexible hierarchies, multiple output formats, and dynamic filtering.
"""

import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any


class ApplicationCatalogueGenerator:
    """Generate application catalogues from ArchiMate CSV files with flexible hierarchies."""

    # Default hierarchy when not specified
    DEFAULT_HIERARCHY = ["Region", "Domain", "Sub-Domain"]

    def __init__(self, archi_inputs_dir: str = "archi_inputs"):
        self.archi_dir = Path(archi_inputs_dir)
        self.elements = {}
        self.properties = defaultdict(dict)
        self._load_data()

    def _load_data(self):
        """Load elements and properties from CSV files."""
        # Load elements
        elements_file = self.archi_dir / "elements.csv"
        if elements_file.exists():
            with open(elements_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['Type'] == 'ApplicationComponent':
                        self.elements[row['ID']] = {
                            'name': row['Name'],
                            'documentation': row['Documentation']
                        }

        # Load properties
        properties_file = self.archi_dir / "properties.csv"
        if properties_file.exists():
            with open(properties_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    element_id = row['ID']
                    if element_id in self.elements:
                        self.properties[element_id][row['Key']] = row['Value']

    def get_available_properties(self) -> List[str]:
        """Get all available properties from the knowledge base."""
        all_properties = set()
        for element_props in self.properties.values():
            all_properties.update(element_props.keys())
        return sorted(all_properties)

    def get_property_values(self, property_name: str) -> List[str]:
        """Get all distinct values for a property."""
        values = set()
        for element_props in self.properties.values():
            if property_name in element_props:
                values.add(element_props[property_name])
        return sorted(values)

    def _organize_by_hierarchy(
        self,
        hierarchy_levels: Optional[List[str]] = None,
        filters: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Organize applications by specified hierarchy.

        Args:
            hierarchy_levels: List of property names for hierarchy (e.g., ["Region", "Domain", "Sub-Domain"])
            filters: Dict of {property_name: value} for filtering

        Returns:
            Nested dict following the hierarchy structure
        """
        if hierarchy_levels is None:
            hierarchy_levels = self.DEFAULT_HIERARCHY

        if filters is None:
            filters = {}

        hierarchy = {}

        for element_id, element_data in self.elements.items():
            props = self.properties.get(element_id, {})

            # Apply filters
            passes_filters = all(
                props.get(key) == value
                for key, value in filters.items()
            )
            if not passes_filters:
                continue

            # Navigate/create hierarchy structure
            current = hierarchy
            for level_idx, level in enumerate(hierarchy_levels):
                level_value = props.get(level, "Unknown")

                if level_idx == len(hierarchy_levels) - 1:
                    # Last level: store applications
                    if level_value not in current:
                        current[level_value] = []
                    current[level_value].append(
                        (element_id, {**element_data, **props})
                    )
                else:
                    # Intermediate level: create dict
                    if level_value not in current:
                        current[level_value] = {}
                    current = current[level_value]

        return hierarchy

    def _format_hierarchy_markdown(
        self,
        hierarchy: Dict[str, Any],
        hierarchy_levels: List[str],
        prefix: str = "",
        columns: Optional[List[str]] = None
    ) -> List[str]:
        """Recursively format hierarchy as markdown."""
        if columns is None:
            columns = ['Application Type', 'Hosting Type', 'Tech Standard', 'Primary Language']

        lines = []

        for key in sorted(hierarchy.keys()):
            value = hierarchy[key]

            # Determine heading level (h2, h3, h4, etc.)
            level_idx = len(prefix.split(">")) - 1 if prefix else 0
            heading = "#" * (2 + level_idx)
            breadcrumb = f"{prefix} > {key}" if prefix else key

            if isinstance(value, list):
                # Leaf level - list applications
                lines.append(f"{heading} {key}\n")
                lines.append(f"**Applications:** {len(value)}\n")
                header = "| Application | " + " | ".join(columns) + " |"
                separator = "|" + "|".join(["---"] * (len(columns) + 1)) + "|"
                lines.append(header)
                lines.append(separator)

                for app_id, app_data in sorted(value, key=lambda x: x[1]['name']):
                    row_values = [app_data['name']]
                    for col in columns:
                        row_values.append(app_data.get(col, ''))

                    lines.append("| " + " | ".join(row_values) + " |")

                lines.append("")
            else:
                # Intermediate level - recurse
                lines.append(f"{heading} {key}\n")
                sub_lines = self._format_hierarchy_markdown(
                    value,
                    hierarchy_levels,
                    breadcrumb,
                    columns
                )
                lines.extend(sub_lines)

        return lines

    def generate_markdown(
        self,
        hierarchy_levels: Optional[List[str]] = None,
        filters: Optional[Dict[str, str]] = None,
        columns: Optional[List[str]] = None
    ) -> str:
        """Generate markdown catalogue with flexible hierarchy."""
        if hierarchy_levels is None:
            hierarchy_levels = self.DEFAULT_HIERARCHY

        if columns is None:
            columns = ['Application Type', 'Hosting Type', 'Tech Standard', 'Primary Language']

        hierarchy = self._organize_by_hierarchy(hierarchy_levels, filters)

        if not hierarchy:
            return "No applications found matching the specified filters."

        # Count totals
        def count_apps(h):
            total = 0
            for v in h.values():
                if isinstance(v, list):
                    total += len(v)
                else:
                    total += count_apps(v)
            return total

        total_apps = count_apps(hierarchy)

        lines = [
            "# Application Catalogue",
            f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Hierarchy:** {' > '.join(hierarchy_levels)}",
        ]

        if filters:
            filter_str = ", ".join(f"{k}={v}" for k, v in filters.items())
            lines.append(f"**Filters:** {filter_str}")

        lines.append(f"\n**Total Applications:** {total_apps}\n")
        lines.append("---\n")

        content_lines = self._format_hierarchy_markdown(hierarchy, hierarchy_levels, columns=columns)
        lines.extend(content_lines)

        return "\n".join(lines)

    def generate_csv(
        self,
        hierarchy_levels: Optional[List[str]] = None,
        filters: Optional[Dict[str, str]] = None,
        columns: Optional[List[str]] = None
    ) -> str:
        """Generate CSV catalogue."""
        if hierarchy_levels is None:
            hierarchy_levels = self.DEFAULT_HIERARCHY

        if columns is None:
            columns = ['Application Type', 'Hosting Type', 'Tech Standard', 'Primary Language']

        hierarchy = self._organize_by_hierarchy(hierarchy_levels, filters)

        # Build header
        header = hierarchy_levels + ["Application"] + columns
        lines = [",".join(header)]

        def process_hierarchy(h, path=[]):
            for key in sorted(h.keys()):
                value = h[key]
                if isinstance(value, list):
                    # Leaf level
                    for app_id, app_data in sorted(value, key=lambda x: x[1]['name']):
                        row = path + [key] + [app_data['name']]
                        for col in columns:
                            row.append(app_data.get(col, ''))
                        lines.append(",".join(f'"{v}"' for v in row))
                else:
                    # Intermediate
                    process_hierarchy(value, path + [key])

        process_hierarchy(hierarchy)
        return "\n".join(lines)

    def generate_html(
        self,
        hierarchy_levels: Optional[List[str]] = None,
        filters: Optional[Dict[str, str]] = None,
        columns: Optional[List[str]] = None
    ) -> str:
        """Generate HTML catalogue."""
        if hierarchy_levels is None:
            hierarchy_levels = self.DEFAULT_HIERARCHY

        if columns is None:
            columns = ['Application Type', 'Hosting Type', 'Tech Standard', 'Primary Language']

        hierarchy = self._organize_by_hierarchy(hierarchy_levels, filters)

        def count_apps(h):
            total = 0
            for v in h.values():
                if isinstance(v, list):
                    total += len(v)
                else:
                    total += count_apps(v)
            return total

        total_apps = count_apps(hierarchy)

        html = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "  <meta charset='UTF-8'>",
            "  <title>Application Catalogue</title>",
            "  <style>",
            "    body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }",
            "    .container { max-width: 1200px; margin: 0 auto; }",
            "    h1 { color: #333; border-bottom: 3px solid #0066cc; padding-bottom: 10px; }",
            "    h2, h3, h4 { color: #0066cc; margin-top: 30px; }",
            "    h3 { color: #0099ff; }",
            "    h4 { color: #00bbff; }",
            "    table { border-collapse: collapse; width: 100%; margin: 15px 0; background: white; }",
            "    th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }",
            "    th { background-color: #0066cc; color: white; font-weight: bold; }",
            "    tr:nth-child(even) { background-color: #f9f9f9; }",
            "    .summary { background: #e8f4f8; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 4px solid #0066cc; }",
            "    .stats { display: flex; gap: 20px; }",
            "    .stat { flex: 1; }",
            "    .stat strong { color: #0066cc; }",
            "  </style>",
            "</head>",
            "<body>",
            "  <div class='container'>",
            "    <h1>Application Catalogue</h1>",
            "    <div class='summary'>",
            f"      <div class='stats'>",
            f"        <div class='stat'><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>",
            f"        <div class='stat'><strong>Hierarchy:</strong> {' > '.join(hierarchy_levels)}</div>",
            f"        <div class='stat'><strong>Total Applications:</strong> {total_apps}</div>",
            f"      </div>",
            f"    </div>",
        ]

        def process_hierarchy(h, level=1):
            for key in sorted(h.keys()):
                value = h[key]
                heading = f"<h{level+1}>{key}</h{level+1}>"
                html.append(f"    {heading}")

                if isinstance(value, list):
                    # Leaf level
                    html.append(f"    <p><strong>Applications:</strong> {len(value)}</p>")
                    html.append("    <table>")
                    header_row = "<tr><th>Application</th>" + "".join(f"<th>{col}</th>" for col in columns) + "</tr>"
                    html.append(f"      {header_row}")

                    for app_id, app_data in sorted(value, key=lambda x: x[1]['name']):
                        row_cells = f"<td>{app_data['name']}</td>"
                        for col in columns:
                            row_cells += f"<td>{app_data.get(col, '')}</td>"
                        html.append(f"      <tr>{row_cells}</tr>")

                    html.append("    </table>")
                else:
                    # Intermediate
                    process_hierarchy(value, level + 1)

        process_hierarchy(hierarchy)

        html.extend([
            "  </div>",
            "</body>",
            "</html>"
        ])

        return "\n".join(html)

    def save_catalogue(
        self,
        format: str = "markdown",
        output_dir: str = "ea_outputs",
        hierarchy_levels: Optional[List[str]] = None,
        filters: Optional[Dict[str, str]] = None,
        columns: Optional[List[str]] = None
    ) -> str:
        """
        Generate and save catalogue to file.

        Args:
            format: "markdown", "csv", or "html"
            output_dir: Directory to save catalogue (default: ea_outputs)
            hierarchy_levels: List of property names for hierarchy
            filters: Dict of {property: value} for filtering
            columns: List of columns to include in the catalogue

        Returns:
            Path to generated file
        """
        Path(output_dir).mkdir(exist_ok=True)

        if format == "markdown":
            content = self.generate_markdown(hierarchy_levels, filters, columns)
            ext = "md"
        elif format == "csv":
            content = self.generate_csv(hierarchy_levels, filters, columns)
            ext = "csv"
        elif format == "html":
            content = self.generate_html(hierarchy_levels, filters, columns)
            ext = "html"
        else:
            raise ValueError(f"Unsupported format: {format}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"application_catalogue_{timestamp}.{ext}"

        filepath = Path(output_dir) / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return str(filepath)


if __name__ == "__main__":
    generator = ApplicationCatalogueGenerator()

    # Show available properties
    print("Available properties:", generator.get_available_properties())
    print()

    # Generate default hierarchy (Region > Domain > Sub-Domain)
    filepath = generator.save_catalogue(format="markdown")
    print(f"Generated: {filepath}")

    # Generate with custom hierarchy
    filepath = generator.save_catalogue(
        format="csv",
        hierarchy_levels=["Domain", "Hosting Type", "Tech Standard"]
    )
    print(f"Generated: {filepath}")

    # Generate with filters
    filepath = generator.save_catalogue(
        format="html",
        filters={"Region": "AEM"}
    )
    print(f"Generated: {filepath}")
