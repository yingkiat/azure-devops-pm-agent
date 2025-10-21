"""
EA Artifact Generator - Main orchestrator for generating EA artifacts.

Coordinates data providers, diagram generators, and output management.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
import json

from .data_providers import EADataProvider, DataProviderFactory
from .data_models import EAData
from .artifact_generators import MermaidGenerator, DiagramType
from .artifact_generators.diagram_types import get_available_diagram_types, get_diagram_priority


class ArtifactGenerator:
    """Main orchestrator for EA artifact generation."""

    def __init__(self, data_provider: Optional[EADataProvider] = None):
        self.data_provider = data_provider or DataProviderFactory.get_default_provider()
        self.mermaid_generator = MermaidGenerator()

    def generate_all_artifacts(self, output_dir: str = "ea_diagrams", combined: bool = True) -> Dict[str, Any]:
        """Generate all possible artifacts and save to output directory."""
        # Load EA data
        if not self.data_provider.is_available():
            return {
                "error": "Data source not available",
                "data_source": str(self.data_provider.csv_path) if hasattr(self.data_provider, 'csv_path') else "unknown"
            }

        try:
            ea_data = self.data_provider.get_ea_data()
        except Exception as e:
            return {"error": f"Failed to load EA data: {e}"}

        if not ea_data.applications:
            return {
                "error": "No applications found in data source",
                "metadata": ea_data.metadata
            }

        # Generate diagrams
        diagrams = self.mermaid_generator.generate_all_compatible_diagrams(ea_data, combined=combined)

        if "error" in diagrams:
            return diagrams

        # Save diagrams to files
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True, parents=True)

        saved_files = {}
        for diagram_type, mermaid_code in diagrams.items():
            if not diagram_type.endswith("_error"):
                try:
                    file_path = self.mermaid_generator.save_diagram(mermaid_code, diagram_type, output_dir)
                    saved_files[diagram_type] = file_path
                except Exception as e:
                    saved_files[f"{diagram_type}_save_error"] = str(e)

        # Generate summary
        summary = self.mermaid_generator.generate_summary(ea_data, diagrams)

        # Save summary to file
        summary_path = output_path / "generation_summary.txt"
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(summary)

        # Save metadata
        metadata_path = output_path / "generation_metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump({
                "ea_data_metadata": ea_data.metadata,
                "generated_diagrams": list(diagrams.keys()),
                "saved_files": saved_files,
                "schema_info": {
                    "columns": ea_data.schema.columns,
                    "version": ea_data.schema.version,
                    "required_fields": ea_data.schema.required_fields
                }
            }, f, indent=2)

        return {
            "success": True,
            "output_directory": str(output_path),
            "generated_diagrams": list(diagrams.keys()),
            "saved_files": saved_files,
            "summary": summary,
            "ea_data": {
                "applications": len(ea_data.applications),
                "capabilities": len(ea_data.capabilities),
                "domains": len(ea_data.domains)
            }
        }

    def generate_specific_diagram(self, diagram_type: DiagramType, output_dir: str = "ea_diagrams") -> Dict[str, Any]:
        """Generate a specific diagram type."""
        try:
            ea_data = self.data_provider.get_ea_data()
            mermaid_code = self.mermaid_generator.generate_diagram(ea_data, diagram_type)

            # Save to file
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True, parents=True)
            file_path = self.mermaid_generator.save_diagram(mermaid_code, diagram_type.value, output_dir)

            return {
                "success": True,
                "diagram_type": diagram_type.value,
                "file_path": file_path,
                "mermaid_code": mermaid_code
            }
        except Exception as e:
            return {
                "error": f"Failed to generate {diagram_type.value} diagram: {e}",
                "diagram_type": diagram_type.value
            }

    def get_compatible_diagram_types(self) -> List[str]:
        """Get list of diagram types compatible with current data."""
        try:
            ea_data = self.data_provider.get_ea_data()
            compatible_types = get_available_diagram_types(ea_data.schema.columns)
            return [dt.value for dt in compatible_types]
        except Exception:
            return []

    def get_data_info(self) -> Dict[str, Any]:
        """Get information about the current data source."""
        try:
            ea_data = self.data_provider.get_ea_data()
            return {
                "available": True,
                "metadata": ea_data.metadata,
                "schema": {
                    "columns": ea_data.schema.columns,
                    "version": ea_data.schema.version,
                    "required_fields": ea_data.schema.required_fields,
                    "optional_fields": ea_data.schema.optional_fields
                },
                "data_summary": {
                    "applications": len(ea_data.applications),
                    "capabilities": len(ea_data.capabilities),
                    "domains": len(ea_data.domains),
                    "domain_names": ea_data.get_domains_list()
                },
                "compatible_diagrams": self.get_compatible_diagram_types()
            }
        except Exception as e:
            return {
                "available": self.data_provider.is_available(),
                "error": str(e)
            }

    def preview_diagrams(self) -> Dict[str, Any]:
        """Preview what diagrams would be generated without actually creating files."""
        try:
            ea_data = self.data_provider.get_ea_data()
            available_fields = ea_data.schema.columns
            compatible_types = get_available_diagram_types(available_fields)

            preview_info = []
            for diagram_type in compatible_types:
                priority = get_diagram_priority(diagram_type, available_fields)
                config = diagram_type  # This would use get_diagram_config in a real implementation

                preview_info.append({
                    "type": diagram_type.value,
                    "priority": priority,
                    "description": f"Shows {diagram_type.value.replace('_', ' ')}"
                })

            # Sort by priority
            preview_info.sort(key=lambda x: x["priority"], reverse=True)

            return {
                "success": True,
                "data_source": ea_data.metadata.get('source_file', 'Unknown'),
                "available_diagrams": preview_info,
                "data_summary": {
                    "applications": len(ea_data.applications),
                    "capabilities": len(ea_data.capabilities),
                    "domains": len(ea_data.domains)
                }
            }
        except Exception as e:
            return {"error": f"Failed to preview diagrams: {e}"}


def create_artifact_generator(data_source: Optional[str] = None) -> ArtifactGenerator:
    """Factory function to create ArtifactGenerator with appropriate data provider."""
    if data_source:
        provider = DataProviderFactory.create_provider(data_source)
    else:
        provider = DataProviderFactory.get_default_provider()

    return ArtifactGenerator(provider)