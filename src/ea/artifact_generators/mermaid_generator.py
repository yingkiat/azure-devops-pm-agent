"""
Mermaid Diagram Generator - Creates Mermaid diagrams from EA data.

Generates various types of enterprise architecture diagrams using Mermaid syntax.
"""

from typing import Dict, List, Any, Optional
import hashlib
from pathlib import Path

from ..data_models import EAData, Application, Capability, LifecycleStatus, StrategicImportance
from .diagram_types import DiagramType, get_diagram_config, get_available_diagram_types, get_diagram_priority


class MermaidGenerator:
    """Generates Mermaid diagrams from EA data."""

    def __init__(self):
        self.color_schemes = self._init_color_schemes()

    def generate_all_compatible_diagrams(self, ea_data: EAData, combined: bool = True) -> Dict[str, str]:
        """Generate all diagrams compatible with the available data."""
        available_fields = ea_data.schema.columns
        compatible_types = get_available_diagram_types(available_fields)

        if not compatible_types:
            return {"error": "No compatible diagram types found for available fields"}

        if combined:
            # Generate single combined diagram file
            combined_diagram = self._generate_combined_diagram(ea_data, compatible_types)
            return {"ea_diagrams_combined": combined_diagram}
        else:
            # Generate separate diagram files (original behavior)
            diagrams = {}
            for diagram_type in compatible_types:
                try:
                    mermaid_code = self.generate_diagram(ea_data, diagram_type)
                    diagrams[diagram_type.value] = mermaid_code
                except Exception as e:
                    diagrams[f"{diagram_type.value}_error"] = f"Error generating diagram: {e}"
            return diagrams

    def generate_diagram(self, ea_data: EAData, diagram_type: DiagramType) -> str:
        """Generate a specific diagram type."""
        config = get_diagram_config(diagram_type)

        # Check if we have required fields
        missing_fields = [field for field in config.required_fields if not ea_data.schema.has_field(field)]
        if missing_fields:
            raise ValueError(f"Missing required fields for {diagram_type.value}: {missing_fields}")

        # Generate based on diagram type
        if diagram_type == DiagramType.APPLICATION_DOMAINS:
            return self._generate_application_domains_diagram(ea_data)
        elif diagram_type == DiagramType.CAPABILITY_MATRIX:
            return self._generate_capability_matrix_diagram(ea_data)
        elif diagram_type == DiagramType.LIFECYCLE_STATUS:
            return self._generate_lifecycle_status_diagram(ea_data)
        elif diagram_type == DiagramType.STRATEGIC_IMPORTANCE:
            return self._generate_strategic_importance_diagram(ea_data)
        elif diagram_type == DiagramType.DOMAIN_CAPABILITIES:
            return self._generate_domain_capabilities_diagram(ea_data)
        else:
            raise ValueError(f"Unsupported diagram type: {diagram_type}")

    def _generate_application_domains_diagram(self, ea_data: EAData) -> str:
        """Generate diagram showing applications grouped by domain."""
        mermaid_lines = ["graph TD"]

        # Group applications by domain
        domain_groups = {}
        for app in ea_data.applications:
            if app.domain not in domain_groups:
                domain_groups[app.domain] = []
            domain_groups[app.domain].append(app)

        # Generate domain subgraphs
        for domain, apps in domain_groups.items():
            domain_id = self._sanitize_id(domain)
            mermaid_lines.append(f"    subgraph {domain_id}[\"{domain}\"]")

            for app in apps:
                app_id = self._sanitize_id(app.name)
                app_label = self._create_app_label(app)
                color_class = self._get_app_color_class(app)

                mermaid_lines.append(f"        {app_id}[\"{app_label}\"]")
                if color_class:
                    mermaid_lines.append(f"        class {app_id} {color_class}")

            mermaid_lines.append("    end")

        # Add color definitions
        mermaid_lines.extend(self._get_color_definitions())

        return "\n".join(mermaid_lines)

    def _generate_capability_matrix_diagram(self, ea_data: EAData) -> str:
        """Generate diagram showing applications and their capabilities."""
        mermaid_lines = ["graph LR"]

        # Create application nodes
        for app in ea_data.applications:
            app_id = self._sanitize_id(app.name)
            app_label = app.display_name
            color_class = self._get_app_color_class(app)

            mermaid_lines.append(f"    {app_id}[\"{app_label}\"]")
            if color_class:
                mermaid_lines.append(f"    class {app_id} {color_class}")

        # Create capability connections
        for capability in ea_data.capabilities:
            app_id = self._sanitize_id(capability.application_name)
            cap_id = self._sanitize_id(f"{capability.application_name}_{capability.name}")
            cap_label = capability.display_name

            # Add maturity indicator if available
            if capability.maturity:
                cap_label += f" ({capability.maturity}/5)"

            mermaid_lines.append(f"    {cap_id}(\"{cap_label}\")")
            mermaid_lines.append(f"    {app_id} --> {cap_id}")

        # Add color definitions
        mermaid_lines.extend(self._get_color_definitions())

        return "\n".join(mermaid_lines)

    def _generate_lifecycle_status_diagram(self, ea_data: EAData) -> str:
        """Generate diagram showing applications grouped by lifecycle status."""
        mermaid_lines = ["graph TD"]

        # Group by lifecycle status
        status_groups = {}
        for app in ea_data.applications:
            status = app.lifecycle_status.value
            if status not in status_groups:
                status_groups[status] = []
            status_groups[status].append(app)

        # Generate status subgraphs
        for status, apps in status_groups.items():
            status_id = self._sanitize_id(status)
            mermaid_lines.append(f"    subgraph {status_id}[\"{status}\"]")

            for app in apps:
                app_id = self._sanitize_id(f"{status}_{app.name}")
                app_label = self._create_app_label_with_years(app)

                mermaid_lines.append(f"        {app_id}[\"{app_label}\"]")

            mermaid_lines.append("    end")

        # Add lifecycle flow if we have apps in different statuses
        if len(status_groups) > 1:
            statuses = list(status_groups.keys())
            for i in range(len(statuses) - 1):
                current_status = self._sanitize_id(statuses[i])
                next_status = self._sanitize_id(statuses[i + 1])
                mermaid_lines.append(f"    {current_status} -.-> {next_status}")

        return "\n".join(mermaid_lines)

    def _generate_strategic_importance_diagram(self, ea_data: EAData) -> str:
        """Generate diagram showing applications grouped by strategic importance."""
        mermaid_lines = ["graph TD"]

        # Group by strategic importance
        importance_groups = {}
        for app in ea_data.applications:
            importance = app.strategic_importance.value
            if importance not in importance_groups:
                importance_groups[importance] = []
            importance_groups[importance].append(app)

        # Define importance order for layout
        importance_order = ["Critical", "Important", "Standard", "Low"]

        # Generate importance subgraphs in priority order
        for importance in importance_order:
            if importance in importance_groups:
                apps = importance_groups[importance]
                importance_id = self._sanitize_id(importance)
                mermaid_lines.append(f"    subgraph {importance_id}[\"{importance}\"]")

                for app in apps:
                    app_id = self._sanitize_id(f"{importance}_{app.name}")
                    app_label = self._create_app_label_with_domain(app)
                    color_class = self._get_importance_color_class(app.strategic_importance)

                    mermaid_lines.append(f"        {app_id}[\"{app_label}\"]")
                    if color_class:
                        mermaid_lines.append(f"        class {app_id} {color_class}")

                mermaid_lines.append("    end")

        # Add color definitions
        mermaid_lines.extend(self._get_importance_color_definitions())

        return "\n".join(mermaid_lines)

    def _generate_domain_capabilities_diagram(self, ea_data: EAData) -> str:
        """Generate diagram showing capabilities organized by domain."""
        mermaid_lines = ["graph TD"]

        # Group capabilities by domain
        domain_capabilities = {}
        for capability in ea_data.capabilities:
            domain = capability.domain
            if domain not in domain_capabilities:
                domain_capabilities[domain] = []
            domain_capabilities[domain].append(capability)

        # Generate domain subgraphs with capabilities
        for domain, capabilities in domain_capabilities.items():
            domain_id = self._sanitize_id(domain)
            mermaid_lines.append(f"    subgraph {domain_id}[\"{domain}\"]")

            for capability in capabilities:
                cap_id = self._sanitize_id(f"{domain}_{capability.name}")
                cap_label = capability.display_name

                # Add maturity if available
                if capability.maturity:
                    cap_label += f"<br/>Maturity: {capability.maturity}/5"

                mermaid_lines.append(f"        {cap_id}(\"{cap_label}\")")

            mermaid_lines.append("    end")

        return "\n".join(mermaid_lines)

    def _generate_combined_diagram(self, ea_data: EAData, compatible_types: List[DiagramType]) -> str:
        """Generate a single file with all diagrams separated by clear sections."""
        sections = []

        # Add header section
        header = self._create_header_section(ea_data, compatible_types)
        sections.append(header)

        # Sort diagram types by priority for better presentation order
        available_fields = ea_data.schema.columns
        sorted_types = sorted(compatible_types,
                            key=lambda dt: get_diagram_priority(dt, available_fields),
                            reverse=True)

        # Generate each diagram as a separate section
        for i, diagram_type in enumerate(sorted_types, 1):
            try:
                # Create section separator
                section_separator = self._create_section_separator(diagram_type, i, len(sorted_types))
                sections.append(section_separator)

                # Generate the actual diagram
                diagram_content = self.generate_diagram(ea_data, diagram_type)
                sections.append(diagram_content)

                # Add spacing after each diagram
                sections.append("\n" + "%" * 80 + "\n")

            except Exception as e:
                error_section = self._create_error_section(diagram_type, str(e))
                sections.append(error_section)

        return "\n\n".join(sections)

    def _create_header_section(self, ea_data: EAData, diagram_types: List[DiagramType]) -> str:
        """Create a header section with metadata."""
        header_lines = [
            "%%" * 40,
            "%%",
            f"%%  ENTERPRISE ARCHITECTURE DIAGRAMS",
            "%%",
            f"%%  Generated: {ea_data.metadata.get('source_file', 'Unknown source')}",
            f"%%  Applications: {len(ea_data.applications)} | Capabilities: {len(ea_data.capabilities)} | Domains: {len(ea_data.domains)}",
            f"%%  Diagram Types: {len(diagram_types)}",
            "%%",
            f"%%  Domains: {', '.join(ea_data.get_domains_list())}",
            "%%",
            "%%" * 40
        ]
        return "\n".join(header_lines)

    def _create_section_separator(self, diagram_type: DiagramType, index: int, total: int) -> str:
        """Create a visual separator between diagram sections."""
        config = get_diagram_config(diagram_type)
        title = diagram_type.value.replace('_', ' ').title()

        separator_lines = [
            "",
            "=" * 100,
            f"SECTION {index}/{total}: {title.upper()}",
            f"Description: {config.description}",
            "=" * 100,
            ""
        ]
        return "\n".join(separator_lines)

    def _create_error_section(self, diagram_type: DiagramType, error_msg: str) -> str:
        """Create an error section for failed diagrams."""
        title = diagram_type.value.replace('_', ' ').title()
        error_lines = [
            "",
            "!" * 60,
            f"ERROR: Failed to generate {title}",
            f"Reason: {error_msg}",
            "!" * 60,
            ""
        ]
        return "\n".join(error_lines)

    def _create_app_label(self, app: Application) -> str:
        """Create a label for an application node."""
        label = app.display_name

        # Add lifecycle and importance indicators
        indicators = []
        if app.lifecycle_status != LifecycleStatus.STRATEGIC:
            indicators.append(app.lifecycle_status.value[:3])
        if app.strategic_importance != StrategicImportance.STANDARD:
            indicators.append(app.strategic_importance.value[:3])

        if indicators:
            label += f"<br/>({', '.join(indicators)})"

        return label

    def _create_app_label_with_years(self, app: Application) -> str:
        """Create app label with remaining years info."""
        label = app.display_name

        if app.remaining_years:
            label += f"<br/>({app.remaining_years} years)"

        return label

    def _create_app_label_with_domain(self, app: Application) -> str:
        """Create app label with domain info."""
        label = app.display_name

        if app.domain:
            label += f"<br/>({app.domain})"

        return label

    def _sanitize_id(self, text: str) -> str:
        """Sanitize text for use as Mermaid node ID."""
        # Replace spaces and special characters with underscores
        sanitized = text.replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "")
        # Remove other problematic characters
        sanitized = "".join(c for c in sanitized if c.isalnum() or c == "_")
        # Ensure it starts with a letter
        if sanitized and not sanitized[0].isalpha():
            sanitized = "app_" + sanitized
        return sanitized or "unknown"

    def _get_app_color_class(self, app: Application) -> Optional[str]:
        """Get color class for an application based on its properties."""
        if app.lifecycle_status == LifecycleStatus.SUNSET:
            return "sunset"
        elif app.strategic_importance == StrategicImportance.CRITICAL:
            return "critical"
        elif app.lifecycle_status == LifecycleStatus.STRATEGIC:
            return "strategic"
        return None

    def _get_importance_color_class(self, importance: StrategicImportance) -> Optional[str]:
        """Get color class for strategic importance."""
        return {
            StrategicImportance.CRITICAL: "critical",
            StrategicImportance.IMPORTANT: "important",
            StrategicImportance.STANDARD: "standard",
            StrategicImportance.LOW: "low"
        }.get(importance)

    def _get_color_definitions(self) -> List[str]:
        """Get standard color class definitions."""
        return [
            "    classDef critical fill:#ffcccc,stroke:#ff0000,stroke-width:2px",
            "    classDef strategic fill:#ccffcc,stroke:#00aa00,stroke-width:2px",
            "    classDef sunset fill:#ffeecc,stroke:#ff8800,stroke-width:2px"
        ]

    def _get_importance_color_definitions(self) -> List[str]:
        """Get strategic importance color class definitions."""
        return [
            "    classDef critical fill:#ff4444,stroke:#cc0000,stroke-width:3px,color:#ffffff",
            "    classDef important fill:#ffaa44,stroke:#cc6600,stroke-width:2px",
            "    classDef standard fill:#44aaff,stroke:#0066cc,stroke-width:1px",
            "    classDef low fill:#aaaaaa,stroke:#666666,stroke-width:1px"
        ]

    def _init_color_schemes(self) -> Dict[str, Dict[str, str]]:
        """Initialize color schemes for different diagram types."""
        return {
            "lifecycle": {
                "Strategic": "#4CAF50",  # Green
                "Mature": "#2196F3",     # Blue
                "Maintenance": "#FF9800", # Orange
                "Sunset": "#F44336",     # Red
                "Retired": "#9E9E9E"     # Grey
            },
            "importance": {
                "Critical": "#F44336",   # Red
                "Important": "#FF9800",  # Orange
                "Standard": "#2196F3",   # Blue
                "Low": "#9E9E9E"        # Grey
            }
        }

    def save_diagram(self, mermaid_code: str, filename: str, output_dir: str = "ea_diagrams") -> str:
        """Save Mermaid diagram to file."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        file_path = output_path / f"{filename}.mermaid"

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(mermaid_code)

        return str(file_path)

    def generate_summary(self, ea_data: EAData, diagrams: Dict[str, str]) -> str:
        """Generate a summary of the artifact generation results."""
        summary_lines = [
            "EA ARTIFACT GENERATION SUMMARY",
            "=" * 50,
            "",
            f"Data Source: {ea_data.metadata.get('source_file', 'Unknown')}",
            f"Applications: {len(ea_data.applications)}",
            f"Capabilities: {len(ea_data.capabilities)}",
            f"Domains: {len(ea_data.domains)}",
            "",
            "Generated Diagrams:",
        ]

        for diagram_name, content in diagrams.items():
            if "error" in diagram_name:
                summary_lines.append(f"   {diagram_name}: {content}")
            else:
                line_count = len(content.split('\n'))
                summary_lines.append(f"   {diagram_name}: {line_count} lines")

        # Add data quality insights
        strategic_apps = ea_data.get_strategic_applications()
        sunset_apps = ea_data.get_sunset_applications()

        if strategic_apps:
            summary_lines.extend([
                "",
                f"Strategic Applications ({len(strategic_apps)}):"
            ])
            for app in strategic_apps[:5]:
                summary_lines.append(f"  • {app.display_name}")
            if len(strategic_apps) > 5:
                summary_lines.append("  • ...")

        if sunset_apps:
            summary_lines.extend([
                "",
                f"Sunset/Maintenance Applications ({len(sunset_apps)}):"
            ])
            for app in sunset_apps[:5]:
                summary_lines.append(f"  • {app.display_name}")
            if len(sunset_apps) > 5:
                summary_lines.append("  • ...")

        return "\n".join(summary_lines)