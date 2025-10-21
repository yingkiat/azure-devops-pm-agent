"""
EA Diagram Generation using Gemini Flash 2.5
Generates visual diagrams from EA discovery data using AI drawing capabilities.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from utils.gemini_client import get_gemini_client


class EADiagramGenerator:
    """Generates EA diagrams using Gemini's visual capabilities."""

    def __init__(self):
        self.client = get_gemini_client()
        self.output_dir = Path(__file__).parent.parent.parent / "ea_diagrams"
        self.output_dir.mkdir(exist_ok=True)

    def generate_from_file(self, ea_file: str, diagram_type: str = "overview", output_file: str = None) -> str:
        """
        Generate diagram from EA analysis JSON file.

        Args:
            ea_file: Path to EA analysis JSON file
            diagram_type: Type of diagram to generate
            output_file: Optional output file path

        Returns:
            Path to generated diagram or diagram content
        """
        ea_path = Path(ea_file)
        if not ea_path.exists():
            raise FileNotFoundError(f"EA file not found: {ea_file}")

        with open(ea_path, 'r', encoding='utf-8') as f:
            ea_data = json.load(f)

        return self.generate_diagram(ea_data, diagram_type, output_file)

    def generate_diagram(self, ea_data: Dict[str, Any], diagram_type: str = "overview", output_file: str = None) -> str:
        """
        Generate diagram from EA data.

        Args:
            ea_data: EA discovery data
            diagram_type: Type of diagram to generate
            output_file: Optional output file path

        Returns:
            Path to generated diagram or diagram content
        """
        print(f"Generating {diagram_type} diagram using Gemini Flash 2.5...")

        # Get the appropriate prompt for the diagram type
        prompt = self._get_diagram_prompt(diagram_type, ea_data)

        # Generate diagram with Gemini
        result = self.client.generate_diagram(prompt, ea_data)

        if result is None:
            raise Exception("Failed to generate diagram with Gemini")

        # Save result
        if output_file:
            output_path = Path(output_file)
        else:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            output_path = self.output_dir / f"ea-{diagram_type}-{timestamp}.txt"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Clean the result text to handle encoding issues
            if isinstance(result, str):
                # Remove or replace problematic characters
                clean_result = result.encode('utf-8', errors='replace').decode('utf-8')
            else:
                clean_result = str(result)

            with open(output_path, 'w', encoding='utf-8', errors='replace') as f:
                f.write(clean_result)

            print(f"Diagram generated: {output_path}")
            return str(output_path)

        except UnicodeEncodeError as e:
            print(f" Encoding error: {e}")
            # Fallback: save as binary then read back
            try:
                with open(output_path, 'wb') as f:
                    f.write(result.encode('utf-8', errors='replace'))
                print(f"Diagram generated (binary mode): {output_path}")
                return str(output_path)
            except Exception as e2:
                print(f" Failed to save diagram: {e2}")
                raise

    def _get_diagram_prompt(self, diagram_type: str, ea_data: Dict[str, Any]) -> str:
        """Get the appropriate prompt for the diagram type."""

        base_prompt = {
            "overview": "Create a high-level enterprise architecture overview diagram showing all major components and their relationships",
            "business-process": "Create a detailed business process flow diagram showing the step-by-step workflow",
            "application": "Create an application architecture diagram showing systems, interfaces, and data flows",
            "data": "Create a data architecture diagram showing entities, relationships, and data flows",
            "infrastructure": "Create an infrastructure diagram showing servers, networks, and deployment architecture",
            "security": "Create a security architecture diagram showing controls, threats, and compliance boundaries",
            "integration": "Create an integration architecture diagram focusing on system interfaces and data exchanges"
        }

        prompt = base_prompt.get(diagram_type, base_prompt["overview"])

        # Add specific instructions based on diagram type
        if diagram_type == "business-process":
            prompt += """
Focus on:
- Process steps and decision points
- Stakeholder swim lanes
- Input/output documents
- System touchpoints
Use flowchart or swimlane diagram format.
"""
        elif diagram_type == "application":
            prompt += """
Focus on:
- Application components and services
- API connections and interfaces
- User interactions
- External system integrations
Use boxes and arrows with clear labeling.
"""
        elif diagram_type == "data":
            prompt += """
Focus on:
- Data entities and their relationships
- Data stores and databases
- Data flow directions
- Data transformation points
Use entity-relationship or data flow diagram format.
"""
        elif diagram_type == "infrastructure":
            prompt += """
Focus on:
- Physical and virtual infrastructure
- Network connections
- Deployment environments
- Scalability and availability zones
Use infrastructure diagram conventions.
"""
        elif diagram_type == "security":
            prompt += """
Focus on:
- Security controls and boundaries
- Threat vectors and mitigations
- Compliance zones
- Access control points
Use security architecture diagram format.
"""
        elif diagram_type == "integration":
            prompt += """
Focus on:
- System-to-system connections
- API endpoints and protocols
- Message flows and formats
- Integration patterns
Use integration architecture diagram format.
"""

        return prompt

    def list_supported_types(self) -> list:
        """List all supported diagram types."""
        return [
            "overview",
            "business-process",
            "application",
            "data",
            "infrastructure",
            "security",
            "integration"
        ]

    def get_diagram_info(self, diagram_type: str) -> str:
        """Get information about a specific diagram type."""
        info = {
            "overview": "High-level EA overview showing all major components",
            "business-process": "Detailed business process flows and workflows",
            "application": "Application architecture with systems and interfaces",
            "data": "Data architecture with entities and flows",
            "infrastructure": "Infrastructure deployment and network architecture",
            "security": "Security controls, threats, and compliance boundaries",
            "integration": "System integration patterns and data exchanges"
        }
        return info.get(diagram_type, "Unknown diagram type")

    def format_results(self, diagram_path: str, diagram_type: str) -> str:
        """Format the results for display."""
        return f"""
EA DIAGRAM GENERATED
==================

Type: {diagram_type}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Output: {diagram_path}

The diagram has been generated using Gemini Flash 2.5's visual capabilities.
You can view the result at: {diagram_path}

Supported diagram types:
{chr(10).join(f"- {t}: {self.get_diagram_info(t)}" for t in self.list_supported_types())}
"""