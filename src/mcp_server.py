"""
Unified MCP Server for Azure DevOps PM Agent
Exposes both PM (Project Management) and EA (Enterprise Architecture) tools.
"""
import asyncio
import json
from typing import Any, Dict, List, Optional
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# Import PM server for Azure DevOps tools
from pm.tools.mcp_server import AzureDevOpsMCPServer

# Import EA modules
from ea.ea_discovery import EADiscovery
from ea.archi_export import ArchiExporter
from ea.artifact_generator import ArtifactGenerator
from ea.data_providers import ArchiMateCSVProvider
from ea.archi_generator import ArchiGenerator
from ea.view_finalizer import ViewFinalizer
from shared.ppt_generator import generate_ppt, inspect_template

from utils.settings import settings

# Initialize FastMCP server
mcp = FastMCP("pm-ea-agent")


class UnifiedMCPServer:
    """Unified MCP Server combining PM and EA capabilities."""

    def __init__(self):
        # Initialize PM server for Azure DevOps tools
        self.pm_server = AzureDevOpsMCPServer()

        # Initialize EA components
        self.ea_engine = EADiscovery()
        self.archi_exporter = ArchiExporter(output_dir="archi_inputs")
        self.archi_generator = ArchiGenerator(archi_inputs_dir="archi_inputs", specs_dir="ea_inputs/views")
        self.view_finalizer = ViewFinalizer(archi_inputs_dir="archi_inputs")
        self.archi_provider = ArchiMateCSVProvider("archi_inputs")

        # Register all tools
        self._register_tools()

    def _register_tools(self):
        """Register all MCP tools (PM + EA)."""

        # Note: PM tools are already registered in AzureDevOpsMCPServer
        # We just need to add EA-specific tools here

        # ===== EA (Enterprise Architecture) Tools =====

        @mcp.tool()
        async def ea_discover(input_text: str, update_archi: bool = True) -> str:
            """
            Discover EA objects (applications, capabilities, relationships) from text.

            Analyzes system descriptions and extracts ArchiMate elements automatically.

            Args:
                input_text: System or architecture description text
                update_archi: Whether to update archi_inputs/ files (default: True)

            Returns:
                Discovered EA elements with counts and summary

            Example:
                "Microsoft Dynamics CRM integrates with QAD EE for purchase order automation"
                -> Discovers: 2 applications, 1 capability, 1 relationship
            """
            result = await self._ea_discover(input_text, update_archi)
            return json.dumps(result, indent=2)

        @mcp.tool()
        async def ea_generate_archi(ea_analysis_file: str = None, generate_xml: bool = True) -> str:
            """
            Generate ArchiMate CSV/XML files for Archi tool import.

            Converts EA discovery results into Archi-compatible format:
            - elements.csv (applications, capabilities, etc.)
            - relations.csv (serving, flow, composition)
            - properties.csv (criticality, maturity)
            - model.xml (Open Group ArchiMate Model Exchange format)

            Args:
                ea_analysis_file: Path to EA analysis JSON (uses latest in ea_outputs/ if not specified)
                generate_xml: Generate model.xml for direct Archi import (default: True)

            Returns:
                Paths to generated files and element counts
            """
            result = await self._ea_generate_archi(ea_analysis_file, generate_xml)
            return json.dumps(result, indent=2)

        @mcp.tool()
        async def ea_generate_mermaid(diagram_type: str = "all") -> str:
            """
            Generate Mermaid diagram code from ArchiMate data.

            Creates technical documentation diagrams from archi_inputs/ data.

            Args:
                diagram_type: Type of diagram to generate
                    - "all": Generate all compatible diagrams
                    - "application_domains": Apps grouped by domain
                    - "capability_matrix": App-capability relationships
                    - "strategic_importance": Apps by strategic value
                    - "lifecycle_status": Apps by lifecycle stage

            Returns:
                Generated Mermaid code and output file paths
            """
            result = await self._ea_generate_mermaid(diagram_type)
            return json.dumps(result, indent=2)

        @mcp.tool()
        async def ea_get_data_summary() -> str:
            """
            Get summary of current EA knowledge base.

            Returns counts and details from archi_inputs/ data:
            - Number of applications, capabilities, relationships
            - Domains and their applications
            - Data quality metrics

            Returns:
                Summary statistics and data overview
            """
            result = await self._ea_get_data_summary()
            return json.dumps(result, indent=2)

        @mcp.tool()
        async def ea_discover_directory(directory: str = "ea_inputs", file_pattern: str = "*") -> str:
            """
            Batch discover EA objects from all files in a directory.

            Processes files incrementally with context awareness:
            - Reads existing archi_inputs/ before starting
            - Processes each file in order
            - Builds context incrementally (no duplicates)
            - Updates archi_inputs/ after each file

            Args:
                directory: Directory containing system description files (default: "ea_inputs")
                file_pattern: Glob pattern for files to process (default: "*" - all files)

            Returns:
                Aggregated discovery results with file-by-file breakdown

            Example:
                ea_discover_directory("ea_inputs", "*")
                -> Processes all files (txt, csv, etc.) in ea_inputs/ and subdirectories
            """
            result = await self._ea_discover_directory(directory, file_pattern)
            return json.dumps(result, indent=2)

        # ===== MVP6: Spec-Driven View Generation Tools =====
        # Note: View specs are YAML files that Claude Code writes/edits directly
        # Only provide essential read/generate operations here

        @mcp.tool()
        async def ea_generate_views_from_specs() -> str:
            """
            Generate views.csv from YAML specifications (deterministic) (MVP6).

            Reads all YAML specs from ea_inputs/views/ and generates deterministic
            views.csv for Archi import. Same spec always produces same output.

            Returns:
                Generation summary with view counts

            Example:
                -> Reads ea_inputs/views/*.yaml
                -> Writes archi_inputs/views.csv (deterministic output)
            """
            result = await self._ea_generate_views_from_specs()
            return json.dumps(result, indent=2)

        @mcp.tool()
        async def ea_finalize_views() -> str:
            """
            Finalize view generation after validation review (MVP6).

            Call this AFTER reviewing the validation report from ea_generate_views_from_specs.
            Generates views.csv and updates model.xml with validated views.

            Returns:
                Success/failure status with file paths

            Example:
                -> Reviews passed, generates views.csv
                -> Updates archi_inputs/model.xml with views
            """
            result = await self._ea_finalize_views()
            return json.dumps(result, indent=2)

        @mcp.tool()
        async def ea_list_view_specs() -> str:
            """
            List all view specifications and their contents (MVP6).

            Returns:
                List of view specs with element/relationship counts
            """
            result = await self._ea_list_view_specs()
            return json.dumps(result, indent=2)

        @mcp.tool()
        async def ea_list_available_elements(element_type: str = None) -> str:
            """
            List available elements that can be added to views (MVP6).

            Args:
                element_type: Optional filter by element type (e.g., "ApplicationComponent")

            Returns:
                List of available elements from archi_inputs/
            """
            result = await self._ea_list_available_elements(element_type)
            return json.dumps(result, indent=2)

        @mcp.tool()
        async def ea_generate_presentation_diagram(view_spec_path: str) -> str:
            """
            Generate a presentation-ready draw.io diagram from a YAML view spec.

            Intelligently curates elements and relationships to fit on a slide,
            then generates clean ArchiMate notation diagram in draw.io format.

            Args:
                view_spec_path: Path to YAML view spec (e.g., "ea_inputs/views/operations_app_landscape.yaml")

            Returns:
                Path to generated draw.io file ready for visual refinement and export

            Example:
                ea_generate_presentation_diagram("ea_inputs/views/commercial_asis_crm_current.yaml")
                -> Generates: ea_diagrams/commercial_asis_crm_current.drawio
            """
            result = await self._ea_generate_presentation_diagram(view_spec_path)
            return json.dumps(result, indent=2)

        @mcp.tool()
        async def ea_generate_diagram(spec_path: str) -> str:
            """
            Generate diagram from YAML spec with AI-driven layout (MVP8).

            Uses extended YAML schema with presentation and output sections.
            Supports ArchiMate layer colors and relationship styling.

            Args:
                spec_path: Path to YAML view spec (e.g., "ea_inputs/views/crm_landscape.yaml")

            Returns:
                Generated diagram file paths and metadata

            Example YAML spec:
                view:
                  name: "CRM Landscape"
                presentation:
                  color_by: "Lifecycle Status"
                output:
                  format: drawio  # or 'archi' or 'both'

            Example:
                ea_generate_diagram("ea_inputs/views/crm_landscape.yaml")
                -> Generates: ea_diagrams/crm_landscape.drawio
            """
            result = await self._ea_generate_diagram(spec_path)
            return json.dumps(result, indent=2)

        @mcp.tool()
        async def ea_reset_model() -> str:
            """
            Reset the EA model by clearing all cached data and generated files.

            This will:
            - Clear file processing cache (.file_cache/)
            - Remove all discovery outputs (ea_outputs/*.json)
            - Remove all ArchiMate files (archi_inputs/*.csv, *.xml)

            Use this when you want to regenerate the model from scratch after
            changing prompts or input files.

            Returns:
                Status message indicating what was cleared
            """
            result = await self._ea_reset_model()
            return json.dumps(result, indent=2)

        @mcp.tool()
        async def ea_ingest_images(input_dir: str = "ea_inputs/images", output_dir: str = "ea_inputs") -> str:
            """
            Ingest images (slides, diagrams, whiteboards) and extract EA information.

            Uses vision LLM to analyze architecture diagrams, presentation slides,
            and whiteboard photos, extracting system names, relationships, and
            capabilities into text files for subsequent EA discovery.

            Features:
            - Batch processes all images in directory (recursive)
            - Checksum-based caching (skips already-processed images)
            - Preserves directory structure: images/subfolder/img.png → subfolder/img.txt

            Args:
                input_dir: Directory containing images (default: "ea_inputs/images")
                output_dir: Base directory for extracted text files (default: "ea_inputs")
                           Subdirectory structure is preserved

            Returns:
                Processing summary with counts and any errors

            Workflow:
                1. Place images in ea_inputs/images/ (with subdirectories as needed)
                2. Run ea_ingest_images() to extract text
                3. Run ea_discover_directory() to build EA model from extracted text

            Example:
                ea_inputs/images/02_IT_systems/diagram.png → ea_inputs/02_IT_systems/diagram.txt

            Supported formats: PNG, JPG, JPEG, GIF, WEBP, BMP, TIFF
            """
            result = await self._ea_ingest_images(input_dir, output_dir)
            return json.dumps(result, indent=2)

        @mcp.tool()
        async def ea_clear_image_cache() -> str:
            """
            Clear the image ingestion cache.

            Use this to force re-processing of all images on next ingestion run.

            Returns:
                Previous cache statistics
            """
            result = await self._ea_clear_image_cache()
            return json.dumps(result, indent=2)

        # ===== Presentation Tools =====

        @mcp.tool()
        async def ea_generate_ppt(yaml_path: str, template_path: str = None) -> str:
            """
            Generate PowerPoint presentation from YAML slide plan.

            Creates .pptx files from structured YAML specifications.
            Supports corporate templates for consistent branding.

            Args:
                yaml_path: Path to YAML slide plan (e.g., "ea_inputs/presentations/roadmap.yaml")
                template_path: Optional path to corporate .pptx template

            Returns:
                Path to generated .pptx file

            YAML Schema:
                presentation:
                  title: "Deck Title"
                  template: "templates/corporate.pptx"  # Optional
                  output: "ea_outputs/my_deck.pptx"

                slides:
                  - layout: "title"
                    title: "Main Title"
                    subtitle: "Subtitle"

                  - layout: "section"
                    title: "Section Name"

                  - layout: "bullets"
                    title: "Slide Title"
                    bullets:
                      - "First point"
                      - "Second point"
                    notes: "Speaker notes here"

                  - layout: "image"
                    title: "Diagram Title"
                    image: "ea_diagrams/landscape.png"

                  - layout: "table"
                    title: "Comparison"
                    table:
                      headers: ["Col1", "Col2"]
                      rows:
                        - ["A", "B"]

            Supported layouts: title, section, bullets, image, table, two_column
            """
            result = await self._ea_generate_ppt(yaml_path, template_path)
            return json.dumps(result, indent=2)

        @mcp.tool()
        async def ea_inspect_ppt_template(template_path: str) -> str:
            """
            Inspect a PowerPoint template to see available layouts.

            Use this to understand what layouts exist in your corporate template,
            then configure layout_mapping in your YAML accordingly.

            Args:
                template_path: Path to .pptx template file

            Returns:
                List of available layouts with placeholder details
            """
            result = await self._ea_inspect_ppt_template(template_path)
            return json.dumps(result, indent=2)

        # Store reference for tool access
        mcp._unified_server = self

    # ===== EA Tool Implementations =====

    def _load_archi_context(self) -> Dict[str, Any]:
        """
        Load existing ArchiMate model as context for discovery.

        Returns:
            Dict with elements, element_names, relationships
            Returns empty dict if archi_inputs/ doesn't exist yet
        """
        try:
            provider = ArchiMateCSVProvider("archi_inputs")

            if not provider.is_available():
                return {
                    "elements": [],
                    "element_names": [],
                    "relationships": []
                }

            ea_data = provider.get_ea_data()

            # Convert to prompt-friendly format
            elements = [
                {
                    "id": f"existing-{i}",
                    "type": "ApplicationComponent",
                    "name": app.name
                }
                for i, app in enumerate(ea_data.applications)
            ]

            # Add capabilities
            elements.extend([
                {
                    "id": f"existing-cap-{i}",
                    "type": "Capability",
                    "name": cap.name
                }
                for i, cap in enumerate(ea_data.capabilities)
            ])

            element_names = [e["name"] for e in elements]

            # Extract relationships from app_capabilities
            relationships = [
                {
                    "type": "Serving",
                    "source": rel.application.name,
                    "target": rel.capability.name
                }
                for rel in ea_data.application_capabilities
            ]

            return {
                "elements": elements,
                "element_names": element_names,
                "relationships": relationships
            }

        except Exception as e:
            print(f"Warning: Could not load archi context: {e}")
            return {"elements": [], "element_names": [], "relationships": []}

    async def _ea_discover(self, input_text: str, update_archi: bool = True) -> Dict[str, Any]:
        """Execute EA discovery on input text."""
        try:
            # Load existing context for entity resolution
            existing_context = self._load_archi_context()

            # Run EA discovery with context
            discovery_result = self.ea_engine.discover(
                system_description=input_text,
                existing_model=existing_context
            )

            if not discovery_result or "error" in discovery_result:
                return {
                    "success": False,
                    "error": discovery_result.get("error", "Discovery failed")
                }

            # Save to ea_outputs/
            output_dir = Path("ea_outputs")
            output_dir.mkdir(exist_ok=True)

            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"ea_analysis_{timestamp}.json"

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(discovery_result, f, indent=2)

            # Update archi_inputs if requested
            archi_files = {}
            if update_archi:
                archi_files = self.archi_exporter.export(
                    str(output_file),
                    generate_views=True,
                    generate_archimate_xml=True,
                    incremental=True  # Adhoc mode: merge with existing data
                )

                # Append provenance for manual additions
                elements_and_props = self._extract_elements_and_properties({
                    "discovery_file": str(output_file)
                })
                if elements_and_props:
                    timestamp = datetime.now().strftime("%Y-%m-%d")
                    for record in elements_and_props:
                        record["source"] = "manual"
                        record["discovered"] = timestamp
                    self._append_provenance_csv(elements_and_props)

            # Extract counts
            discovery = discovery_result.get('discovery', {})

            app_count = len(discovery.get('ApplicationComponent', []))
            cap_count = len(discovery.get('Capability', []))
            rel_count = len(discovery_result.get('relationships', []))

            return {
                "success": True,
                "discovery_file": str(output_file),
                "element_counts": {
                    "applications": app_count,
                    "capabilities": cap_count,
                    "relationships": rel_count,
                    "total_elements": sum(len(v) for v in discovery.values() if isinstance(v, list))
                },
                "archi_files": archi_files if update_archi else None,
                "summary": f"Discovered {app_count} applications, {cap_count} capabilities, {rel_count} relationships"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _ea_generate_archi(self, ea_analysis_file: str = None,
                                 generate_xml: bool = True) -> Dict[str, Any]:
        """Generate ArchiMate files from EA analysis."""
        try:
            # Find latest EA analysis if not specified
            if not ea_analysis_file:
                output_dir = Path("ea_outputs")
                if not output_dir.exists():
                    return {
                        "success": False,
                        "error": "No EA analysis files found. Run ea_discover first."
                    }

                analysis_files = list(output_dir.glob("ea_analysis_*.json"))
                if not analysis_files:
                    return {
                        "success": False,
                        "error": "No EA analysis files found. Run ea_discover first."
                    }

                # Use most recent
                ea_analysis_file = str(sorted(analysis_files)[-1])

            # Generate ArchiMate files
            result = self.archi_exporter.export(
                ea_analysis_file,
                generate_views=True,
                generate_archimate_xml=generate_xml
            )

            return {
                "success": True,
                "source_file": ea_analysis_file,
                "generated_files": result,
                "archi_import": "Open Archi -> File -> Open -> Model from File -> archi_inputs/model.xml"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _ea_generate_mermaid(self, diagram_type: str = "all") -> Dict[str, Any]:
        """Generate Mermaid diagrams from ArchiMate data."""
        try:
            # Use ArchiMate provider as data source
            provider = ArchiMateCSVProvider("archi_inputs")

            if not provider.is_available():
                return {
                    "success": False,
                    "error": "ArchiMate data not found. Run ea_generate_archi first."
                }

            generator = ArtifactGenerator(provider)

            if diagram_type == "all":
                # Generate all compatible diagrams
                result = generator.generate_all_artifacts(
                    output_dir="ea_diagrams",
                    combined=True
                )
            else:
                # Generate specific diagram type
                from ea.artifact_generators import DiagramType
                try:
                    dt = DiagramType(diagram_type)
                    result = generator.generate_specific_diagram(dt, output_dir="ea_diagrams")
                except ValueError:
                    return {
                        "success": False,
                        "error": f"Unknown diagram type: {diagram_type}",
                        "available_types": [dt.value for dt in DiagramType]
                    }

            return result

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _ea_get_data_summary(self) -> Dict[str, Any]:
        """Get summary of EA knowledge base."""
        try:
            provider = ArchiMateCSVProvider("archi_inputs")

            if not provider.is_available():
                return {
                    "success": False,
                    "available": False,
                    "message": "No EA data found. Run ea_discover to create ArchiMate data."
                }

            ea_data = provider.get_ea_data()

            return {
                "success": True,
                "available": True,
                "data_source": "archi_inputs/",
                "format": "ArchiMate 3.0 CSV",
                "element_counts": {
                    "applications": len(ea_data.applications),
                    "capabilities": len(ea_data.capabilities),
                    "domains": len(ea_data.domains),
                    "app_capability_links": len(ea_data.application_capabilities)
                },
                "domains": [{"name": d.name, "app_count": len(d.applications)}
                           for d in ea_data.domains],
                "applications": [{"name": a.name, "domain": a.domain,
                                 "strategic_importance": a.strategic_importance.value}
                                for a in ea_data.applications[:10]],  # First 10
                "metadata": ea_data.metadata
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (rough approximation: 1 token ≈ 4 chars)."""
        return len(text) // 4

    def _chunk_csv_content(self, csv_content: str, max_rows: int = 25) -> List[str]:
        """
        Split CSV content into chunks by rows.

        Each chunk includes the header row plus up to max_rows data rows.
        This ensures each chunk can be processed independently while
        preserving column structure.

        Args:
            csv_content: Full CSV content as string
            max_rows: Maximum data rows per chunk (default 25)

        Returns:
            List of CSV content strings, each with header + data rows
        """
        lines = csv_content.strip().split('\n')
        if len(lines) <= 1:
            return [csv_content]  # Empty or header only

        header = lines[0]
        data_rows = lines[1:]

        # If small enough, return as-is
        if len(data_rows) <= max_rows:
            return [csv_content]

        # Split into chunks
        chunks = []
        for i in range(0, len(data_rows), max_rows):
            chunk_rows = data_rows[i:i + max_rows]
            chunk_content = header + '\n' + '\n'.join(chunk_rows)
            chunks.append(chunk_content)

        return chunks

    async def _ea_discover_directory(self, directory: str, file_pattern: str) -> Dict[str, Any]:
        """Batch process all files in a directory with smart caching and output validation."""
        try:
            from pathlib import Path
            from core.file_monitor import FileChangeMonitor

            # DEBUG: Check what file patterns are being used
            print(f"[DEBUG] Creating FileChangeMonitor instance...")
            monitor = FileChangeMonitor()
            print(f"[DEBUG] FileChangeMonitor created")

            # Test detect_changes to see what files it finds
            test_changeset = monitor.detect_changes(directory)
            print(f"[DEBUG] Test detect_changes found {test_changeset.total_files} files")
            xlsx_count = sum(1 for f in test_changeset.new_files + test_changeset.modified_files + test_changeset.unchanged_files if f.lower().endswith('.xlsx'))
            print(f"[DEBUG] Excel files found: {xlsx_count}")

            dir_path = Path(directory).resolve()
            if not dir_path.exists():
                return {
                    "success": False,
                    "error": f"Directory not found: {directory}"
                }

            # Initialize file monitor with output validation
            file_monitor = FileChangeMonitor()

            # Get incremental workload with granular content validation
            workload = file_monitor.get_incremental_workload(
                directory=directory,
                output_dir="archi_inputs",
                validate_output=True,
                granular_validation=True  # Enable per-file content matching
            )

            print(f"\n{'=' * 80}")
            print("SMART CACHING ANALYSIS (with Content Validation)")
            print(f"{'=' * 80}")
            print(f"Total files in directory: {workload['total_files']}")
            print(f"Files to process: {workload['processing_required']}")
            print(f"  - New files: {len(workload['new_files'])}")
            print(f"  - Modified files: {len(workload['modified_files'])}")
            if workload.get('output_invalidated_files'):
                print(f"  - Output-invalidated files: {len(workload['output_invalidated_files'])} (outputs missing/corrupted)")
            print(f"Files to skip (cached & validated): {workload['files_to_skip']}")
            print(f"Efficiency gain: {workload['efficiency_gain_percent']:.1f}% of files skipped")

            if not workload['cache_valid']:
                print(f"\n[!] Global cache invalidated: {workload['cache_invalidation_reason']}")
                print(f"    All files marked for re-processing.")

            if workload['processing_required'] == 0 and workload['cache_valid']:
                print(f"\n[+] All files already processed and outputs validated!")
                print(f"   No LLM calls needed - using existing archi_inputs/ data.")

                final_summary = await self._ea_get_data_summary()
                return {
                    "success": True,
                    "directory": directory,
                    "pattern": file_pattern,
                    "total_files": workload['total_files'],
                    "files_processed": [],
                    "all_cached": True,
                    "efficiency_gain_percent": 100.0,
                    "message": "All files already processed. Outputs validated. No processing needed!",
                    "final_model_state": final_summary.get("element_counts", {}) if final_summary.get("success") else {}
                }

            # Only process new/modified files
            files = workload['files_to_process']

            # Sort files for consistent processing order
            files = sorted(files)

            print(f"Found {len(files)} files to process in {directory}")
            print(f"Processing order:")
            for i, f in enumerate(files, 1):
                print(f"  {i}. {f}")

            results = {
                "success": True,
                "directory": directory,
                "pattern": file_pattern,
                "total_files": workload['total_files'],
                "files_to_process": len(files),
                "files_skipped_cached": workload['files_to_skip'],
                "efficiency_gain_percent": workload['efficiency_gain_percent'],
                "cache_valid": workload['cache_valid'],
                "files_in_workload": [str(f).split('\\\\')[-1] if '\\\\' in str(f) else str(f).split('/')[-1] for f in files],
                "files_processed": [],
                "aggregated_counts": {
                    "total_applications": 0,
                    "total_capabilities": 0,
                    "total_relationships": 0
                },
                "errors": []
            }

            # Provenance tracking: map element names to source files
            provenance_records = []  # List of {type, name, source, discovered}

            # Collect all discovery files for final merge
            discovery_files = []

            # SMART BATCHING: Group small files into batches to reduce OpenAI calls
            SMALL_FILE_THRESHOLD = 2000  # tokens (~ 8K chars)
            MAX_BATCH_SIZE = 6000  # tokens (~ 24K chars) - leave room for prompt

            batches = []  # List of (batch_content, [file_paths])
            current_batch_files = []
            current_batch_content = []
            current_batch_tokens = 0

            print(f"\n{'=' * 80}")
            print("BATCHING FILES FOR EFFICIENCY")
            print(f"{'=' * 80}")
            print(f"Processing {len(files)} files from workload:")
            for i, f in enumerate(files, 1):
                fname = str(f).split('\\\\')[-1] if '\\\\' in str(f) else str(f).split('/')[-1]
                print(f"  {i}. {fname}")

            # First pass: read all files and create batches
            for file_path in files:
                # Skip non-data files (views, templates, README)
                file_path_str = str(file_path).lower()
                if any(skip in file_path_str for skip in ['views/', 'view_templates/', 'readme.md', '.yaml', '.yml']):
                    print(f"[*] Skipping non-data file: {file_path}")
                    continue

                try:
                    # Check file type before reading
                    is_csv = str(file_path).lower().endswith('.csv')
                    is_xlsx = str(file_path).lower().endswith('.xlsx')

                    # Read file content (with XLSX conversion if needed)
                    if is_xlsx:
                        try:
                            from src.shared.file_converters import xlsx_to_csv
                        except ImportError:
                            # Fallback to relative import
                            from shared.file_converters import xlsx_to_csv
                        print(f"[*] Converting XLSX file: {file_path}")
                        content = xlsx_to_csv(str(file_path)).strip()
                    else:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read().strip()

                    if not content:
                        print(f"[!] Skipping empty file: {file_path}")
                        continue

                    file_tokens = self._estimate_tokens(content)

                    # CSV files and XLSX files: chunk by rows to handle large files
                    if is_csv or is_xlsx:
                        file_type = "XLSX" if is_xlsx else "CSV"
                        chunks = self._chunk_csv_content(content, max_rows=25)

                        if len(chunks) == 1:
                            # Small file - single batch
                            batches.append(([content], [file_path]))
                            print(f"[*] {file_type} file (solo batch): {file_path} ({file_tokens} tokens)")
                        else:
                            # Large file - multiple chunks
                            print(f"[*] {file_type} file chunked into {len(chunks)} parts: {file_path}")
                            for chunk_idx, chunk_content in enumerate(chunks, 1):
                                chunk_tokens = self._estimate_tokens(chunk_content)
                                # Create a virtual file path for tracking (file.csv becomes file.csv:chunk1)
                                chunk_file_path = f"{file_path}:chunk{chunk_idx}"
                                batches.append(([chunk_content], [chunk_file_path]))
                                print(f"    Chunk {chunk_idx}: {chunk_tokens} tokens")
                    # Large files get their own batch (processed individually)
                    elif file_tokens > SMALL_FILE_THRESHOLD:
                        batches.append(([content], [file_path]))
                        print(f"[*] Large file (solo batch): {file_path} ({file_tokens} tokens)")
                    else:
                        # Try to add to current batch (only for small non-CSV files)
                        if current_batch_tokens + file_tokens > MAX_BATCH_SIZE:
                            # Current batch is full, save it and start new one
                            if current_batch_files:
                                batches.append((
                                    current_batch_content.copy(),
                                    current_batch_files.copy()
                                ))
                                print(f"[*] Batch created: {len(current_batch_files)} files ({current_batch_tokens} tokens)")

                            # Start new batch
                            current_batch_files = []
                            current_batch_content = []
                            current_batch_tokens = 0

                        # Add to current batch
                        current_batch_files.append(file_path)
                        current_batch_content.append(f"=== File: {file_path} ===\n{content}")
                        current_batch_tokens += file_tokens

                except Exception as e:
                    import traceback
                    error_details = traceback.format_exc()
                    print(f"[!] Error reading {file_path}: {e}")
                    print(f"    Traceback: {error_details}")
                    # Log error for Excel files specifically
                    if str(file_path).lower().endswith(('.xlsx', '.xls')):
                        results["errors"].append(f"Excel file error in {file_path}: {e}")
                    continue

            # Don't forget the last batch
            if current_batch_files:
                batches.append((
                    current_batch_content.copy(),
                    current_batch_files.copy()
                ))
                print(f"[*] Batch created: {len(current_batch_files)} files ({current_batch_tokens} tokens)")

            print(f"\n[+] Created {len(batches)} batches from {len(files)} files")
            print(f"   OpenAI calls: {len(batches)} (vs {len(files)} without batching)")
            print(f"   Savings: {len(files) - len(batches)} calls ({100 * (len(files) - len(batches)) / max(len(files), 1):.0f}%)")

            # Second pass: process batches
            for batch_idx, (batch_content, batch_files) in enumerate(batches, 1):
                print(f"\n{'=' * 80}")
                print(f"Processing Batch {batch_idx}/{len(batches)} ({len(batch_files)} files)")
                print(f"{'=' * 80}")
                for fp in batch_files:
                    print(f"  - {fp}")

                try:
                    # Combine batch content with separators
                    combined_content = "\n\n".join(batch_content)

                    # Run discovery WITHOUT updating archi (saves to ea_outputs/ only)
                    # LLM will extract ALL CSV columns based on prompt instructions
                    discovery_result = await self._ea_discover(combined_content, update_archi=False)

                    if discovery_result.get("success"):
                        # Collect discovery file for final merge
                        discovery_files.append(discovery_result.get("discovery_file"))

                        # Update aggregated counts
                        counts = discovery_result.get("element_counts", {})
                        results["aggregated_counts"]["total_applications"] += counts.get("applications", 0)
                        results["aggregated_counts"]["total_capabilities"] += counts.get("capabilities", 0)
                        results["aggregated_counts"]["total_relationships"] += counts.get("relationships", 0)

                        # Extract discovered elements for content validation
                        discovered_elements = self._extract_discovered_elements(discovery_result)

                        # Record provenance for all discovered elements and properties
                        from datetime import datetime
                        import re
                        timestamp = datetime.now().strftime("%Y-%m-%d")

                        # Helper to extract original file path (strip :chunk* suffix)
                        def get_original_path(fp):
                            fp_str = str(fp)
                            return re.sub(r':chunk\d+$', '', fp_str)

                        # Source is comma-separated if multiple files in batch (use original paths)
                        original_files = list(set(get_original_path(fp) for fp in batch_files))
                        source_files = ", ".join(
                            str(Path(fp).relative_to(directory) if Path(fp).is_relative_to(Path(directory)) else fp)
                            for fp in original_files
                        )

                        # Extract elements and properties for provenance
                        elements_and_props = self._extract_elements_and_properties(discovery_result)

                        for record in elements_and_props:
                            record["source"] = source_files
                            record["discovered"] = timestamp
                            provenance_records.append(record)

                        # Mark original files as processed (not chunk paths)
                        for original_fp in original_files:
                            file_monitor.mark_processed(
                                file_path=original_fp,
                                insights=[],
                                discovered_elements=discovered_elements,
                                success=True
                            )

                        # Record results for each batch file (including chunk info)
                        for file_path in batch_files:
                            file_result = {
                                "file": str(file_path),
                                "original_file": get_original_path(file_path),
                                "status": "success",
                                "batch": batch_idx,
                                "counts": counts,
                                "summary": discovery_result.get("summary", "")
                            }
                            results["files_processed"].append(file_result)

                        print(f"[+] Batch success: {discovery_result.get('summary', '')}")
                    else:
                        # Batch failed - mark all files as failed
                        error = discovery_result.get("error", "Unknown error")
                        results["errors"].append(f"Batch {batch_idx} error: {error}")

                        # Helper to extract original file path (strip :chunk* suffix)
                        import re
                        def get_original_path(fp):
                            fp_str = str(fp)
                            return re.sub(r':chunk\d+$', '', fp_str)

                        original_files = list(set(get_original_path(fp) for fp in batch_files))
                        for original_fp in original_files:
                            file_monitor.mark_processed(
                                file_path=original_fp,
                                insights=[],
                                success=False
                            )

                        for file_path in batch_files:
                            file_result = {
                                "file": str(file_path),
                                "original_file": get_original_path(file_path),
                                "status": "error",
                                "batch": batch_idx,
                                "error": error
                            }
                            results["files_processed"].append(file_result)

                        print(f"[-] Batch error: {error}")

                except Exception as e:
                    error_msg = f"Failed to process batch {batch_idx}: {str(e)}"
                    results["errors"].append(error_msg)

                    for file_path in batch_files:
                        file_monitor.mark_processed(
                            file_path=file_path,
                            insights=[],
                            success=False
                        )

                        results["files_processed"].append({
                            "file": file_path,
                            "status": "error",
                            "batch": batch_idx,
                            "error": str(e)
                        })

                    print(f"[-] Batch error: {error_msg}")

            # Merge all discoveries and export to archi_inputs/
            if discovery_files:
                print(f"\n{'=' * 80}")
                print(f"MERGING DISCOVERIES AND EXPORTING TO ARCHI_INPUTS")
                print(f"{'=' * 80}")
                print(f"Merging {len(discovery_files)} discovery files...")

                try:
                    merged_discovery = self._merge_discoveries(discovery_files)

                    # Save merged discovery
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    merged_file = Path("ea_outputs") / f"ea_analysis_merged_{timestamp}.json"

                    with open(merged_file, 'w', encoding='utf-8') as f:
                        json.dump(merged_discovery, f, indent=2)

                    print(f"[+] Merged discovery saved to: {merged_file}")

                    # Export merged result to archi_inputs/
                    archi_files = self.archi_exporter.export(
                        str(merged_file),
                        generate_views=True,
                        generate_archimate_xml=True
                    )

                    print(f"[+] Exported merged model to archi_inputs/")

                    # Write provenance.csv (library catalog)
                    if provenance_records:
                        self._write_provenance_csv(provenance_records)
                        print(f"[+] Wrote provenance.csv with {len(provenance_records)} records")

                except Exception as e:
                    print(f"[-] Error merging discoveries: {e}")
                    results["errors"].append(f"Failed to merge discoveries: {e}")

            # Get final summary
            print(f"\n{'=' * 80}")
            print(f"BATCH PROCESSING COMPLETE")
            print(f"{'=' * 80}")
            print(f"Total files in directory: {workload['total_files']}")
            print(f"Files processed (LLM calls): {len(results['files_processed'])}")
            print(f"Files skipped (cached): {workload['files_to_skip']}")
            print(f"Efficiency gain: {workload['efficiency_gain_percent']:.1f}%")
            print(f"\nDiscovered from processed files:")
            print(f"  Applications: {results['aggregated_counts']['total_applications']}")
            print(f"  Capabilities: {results['aggregated_counts']['total_capabilities']}")
            print(f"  Relationships: {results['aggregated_counts']['total_relationships']}")

            if results["errors"]:
                print(f"\n[!] {len(results['errors'])} errors occurred during processing")

            # Get final state from archi_inputs
            final_summary = await self._ea_get_data_summary()
            if final_summary.get("success"):
                results["final_model_state"] = final_summary.get("element_counts", {})
                print(f"\n[*] Final Model State:")
                print(f"   Applications: {final_summary['element_counts']['applications']}")
                print(f"   Capabilities: {final_summary['element_counts']['capabilities']}")
                print(f"   App-Capability Links: {final_summary['element_counts']['app_capability_links']}")

            return results

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _extract_discovered_elements(self, discovery_result: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Extract element names from discovery result for cache content validation.

        Args:
            discovery_result: Result from ea_discover containing discovery data

        Returns:
            Dict mapping element type to list of discovered element names
        """
        discovered = {}

        # Read from ea_outputs file
        discovery_file = discovery_result.get("discovery_file")
        if not discovery_file:
            return discovered

        try:
            from pathlib import Path
            import json

            with open(discovery_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            discovery = data.get('discovery', {})

            # Extract element names by type
            for element_type, items in discovery.items():
                if not isinstance(items, list):
                    continue

                names = []
                for item in items:
                    if isinstance(item, dict):
                        name = item.get('name')
                        if name:
                            names.append(name)
                    elif isinstance(item, str):
                        names.append(item)

                if names:
                    discovered[element_type] = names

        except Exception as e:
            # If extraction fails, return empty dict (cache will still work, just less precise)
            pass

        return discovered

    def _extract_elements_and_properties(self, discovery_result: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Extract elements and properties from discovery result for provenance tracking.

        Args:
            discovery_result: Result from ea_discover containing discovery data

        Returns:
            List of provenance records for elements and properties
        """
        records = []

        discovery_file = discovery_result.get("discovery_file")
        if not discovery_file:
            return records

        try:
            with open(discovery_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            discovery = data.get('discovery', {})

            # Extract elements
            for element_type, items in discovery.items():
                if not isinstance(items, list):
                    continue

                for item in items:
                    if isinstance(item, dict):
                        name = item.get('name')
                        if name:
                            # Add element record
                            records.append({
                                "type": "element",
                                "name": name,
                                "element_type": element_type,
                                "note": ""
                            })

                            # Add property records from raw_data
                            skip_keys = {'name', 'description', 'capabilities_supported', 'lifecycle_signals'}
                            for key, value in item.items():
                                if key in skip_keys or not value:
                                    continue
                                if isinstance(value, (dict, list)):
                                    continue
                                records.append({
                                    "type": "property",
                                    "name": f"{name}:{key}",
                                    "element_type": element_type,
                                    "note": str(value)
                                })
                    elif isinstance(item, str):
                        records.append({
                            "type": "element",
                            "name": item,
                            "element_type": element_type,
                            "note": ""
                        })

            # Also extract from changes.inserts (business attributes)
            changes = data.get('changes', {})
            for insert in changes.get('inserts', []):
                if not isinstance(insert, dict):
                    continue
                app_name = insert.get('app_name')
                if not app_name:
                    continue

                skip_keys = {'app_name', 'capability'}
                for key, value in insert.items():
                    if key in skip_keys or not value:
                        continue
                    # Check if we already have this property
                    prop_name = f"{app_name}:{key}"
                    if not any(r['name'] == prop_name for r in records):
                        records.append({
                            "type": "property",
                            "name": prop_name,
                            "element_type": "ApplicationComponent",
                            "note": str(value)
                        })

        except Exception as e:
            pass

        return records

    def _merge_discoveries(self, discovery_files: List[str]) -> Dict[str, Any]:
        """
        Merge multiple EA discovery JSON files into a single combined discovery.

        Args:
            discovery_files: List of paths to ea_analysis_*.json files

        Returns:
            Merged discovery dict with all elements and relationships
        """
        merged = {
            "discovery": {},
            "relationships": [],
            "changes": {
                "inserts": [],
                "updates": [],
                "deletes": []
            },
            "exploration": {},
            "recommendations": []
        }

        # Track seen elements/relationships to avoid duplicates
        # For elements: deduplicate by (type, name) only
        # Same element name = same element, merge descriptions
        seen_elements = {}  # {(type, name): element_data}
        seen_relationships = set()  # {(type, source, target)}

        for file_path in discovery_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Merge discovery elements
                discovery = data.get('discovery', {})
                for element_type, items in discovery.items():
                    if not isinstance(items, list):
                        continue

                    if element_type not in merged["discovery"]:
                        merged["discovery"][element_type] = []

                    for item in items:
                        if isinstance(item, dict):
                            name = item.get('name')

                            # Deduplicate by (type, name) only
                            key = (element_type, name)

                            if key not in seen_elements:
                                # First occurrence - add it
                                seen_elements[key] = len(merged["discovery"][element_type])  # Store index
                                merged["discovery"][element_type].append(item)
                            else:
                                # Duplicate found - merge descriptions into existing element
                                existing_idx = seen_elements[key]
                                existing = merged["discovery"][element_type][existing_idx]

                                # Get existing description (check both capitalization variants)
                                existing_desc = existing.get('description', existing.get('Documentation', ''))
                                new_desc = item.get('description', item.get('Documentation', ''))

                                # Determine which key is being used in the data
                                desc_key = 'description' if 'description' in existing else 'Documentation'

                                # Merge descriptions if they're different and both non-empty
                                if new_desc and new_desc != existing_desc:
                                    if existing_desc:
                                        # Combine descriptions with semicolon separator
                                        combined = f"{existing_desc}; {new_desc}"
                                        existing[desc_key] = combined
                                    else:
                                        existing[desc_key] = new_desc
                        else:
                            # Handle string items
                            key = (element_type, str(item))
                            if key not in seen_elements:
                                seen_elements[key] = len(merged["discovery"][element_type])  # Store index
                                merged["discovery"][element_type].append(item)

                # Merge relationships
                relationships = data.get('relationships', [])
                for rel in relationships:
                    if isinstance(rel, dict):
                        rel_key = (rel.get('type'), rel.get('source'), rel.get('target'))

                        # Skip duplicate relationships
                        if rel_key not in seen_relationships:
                            seen_relationships.add(rel_key)
                            merged["relationships"].append(rel)

                # Merge changes (inserts/updates/deletes)
                changes = data.get('changes', {})
                for change_type in ['inserts', 'updates', 'deletes']:
                    if change_type in changes:
                        merged["changes"][change_type].extend(changes[change_type])

                # Merge recommendations
                recommendations = data.get('recommendations', [])
                if isinstance(recommendations, list):
                    merged["recommendations"].extend(recommendations)

            except Exception as e:
                print(f"[!] Warning: Failed to merge {file_path}: {e}")
                continue

        return merged

    def _write_provenance_csv(self, provenance_records: List[Dict[str, str]]) -> str:
        """
        Write provenance.csv - the library catalog tracking element and property sources.

        Args:
            provenance_records: List of dicts with type, name, element_type, source, note, discovered

        Returns:
            Path to generated provenance.csv
        """
        import csv

        output_file = Path("archi_inputs") / "provenance.csv"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Type', 'Name', 'Element Type', 'Source', 'Note', 'Discovered'])

            for record in provenance_records:
                writer.writerow([
                    record.get('type', 'element'),
                    record.get('name', ''),
                    record.get('element_type', ''),
                    record.get('source', ''),
                    record.get('note', ''),
                    record.get('discovered', '')
                ])

        print(f"   {output_file}")
        return str(output_file)

    def _append_provenance_csv(self, provenance_records: List[Dict[str, str]]) -> str:
        """
        Append to provenance.csv - used for manual ea_discover() additions.

        Args:
            provenance_records: List of dicts with type, name, element_type, source, note, discovered

        Returns:
            Path to provenance.csv
        """
        import csv

        output_file = Path("archi_inputs") / "provenance.csv"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Check if file exists to determine if we need header
        file_exists = output_file.exists()

        with open(output_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Write header only if file is new
            if not file_exists:
                writer.writerow(['Type', 'Name', 'Element Type', 'Source', 'Note', 'Discovered'])

            for record in provenance_records:
                writer.writerow([
                    record.get('type', 'element'),
                    record.get('name', ''),
                    record.get('element_type', ''),
                    record.get('source', ''),
                    record.get('note', ''),
                    record.get('discovered', '')
                ])

        print(f"   Appended {len(provenance_records)} records to {output_file}")
        return str(output_file)

    # ===== MVP6 Tool Implementations =====

    async def _ea_generate_views_from_specs(self) -> Dict[str, Any]:
        """
        Generate views.csv from YAML specifications with hybrid validation approach.

        Step 1: Generate views from specs (without XML yet)
        Step 2: Validate each view with ViewFinalizer
        Step 3: Return validation report for user approval (LLM interview)
        Step 4: User approves, then XML generation happens

        NOTE: This returns validation results. User must manually approve via
        'ea_finalize_views' tool to actually generate model.xml.
        """
        try:
            # Step 1: Generate views from specs
            result = self.archi_generator.generate_views_from_specs()

            if not result.get('view_definitions'):
                return {
                    "success": True,
                    "phase": "validation",
                    "views_found": 0,
                    "message": "No view specifications found. Create YAML files in ea_inputs/views/"
                }

            # Step 2: Validate each view
            validations = []
            for view_def in result.get('view_definitions', []):
                validation = self.view_finalizer.finalize_view(
                    view_name=view_def['name'],
                    selected_element_ids=view_def['elements'],
                    selected_relation_ids=view_def['relations'],
                    grouping_config=view_def.get('grouping', {}),
                    spec_file_name=view_def.get('spec_file')
                )
                validations.append(validation)

            # Step 3: Format validation report for user
            validation_report = self.view_finalizer.format_validation_report(validations)
            can_proceed = self.view_finalizer.should_proceed_with_generation(validations)

            # Step 4: Return validation results (no XML generation yet)
            return {
                "success": True,
                "phase": "validation_complete",
                "views_validated": len(validations),
                "can_proceed": can_proceed,
                "validation_report": validation_report,
                "view_definitions": [
                    {
                        'name': v.view_name,
                        'elements': v.element_count,
                        'relationships': v.relationship_count,
                        'is_valid': v.is_valid,
                        'issues': len(v.issues),
                        'warnings': len(v.warnings)
                    }
                    for v in validations
                ],
                "message": "View validation complete. Review the report above. Reply with 'generate the views' to proceed with model.xml generation."
            }

        except Exception as e:
            import traceback
            return {
                "success": False,
                "phase": "validation_failed",
                "error": str(e),
                "traceback": traceback.format_exc()
            }

    async def _ea_finalize_views(self) -> Dict[str, Any]:
        """
        Finalize view generation after user approval.

        This is called AFTER user reviews validation report and approves.
        Generates views.csv and updates model.xml with the validated views.
        """
        try:
            # Get the validated view definitions
            result = self.archi_generator.generate_views_from_specs()

            if not result.get('views_generated'):
                return {
                    "success": False,
                    "error": "No views to finalize"
                }

            # Regenerate complete model.xml with updated views
            xml_updated = False
            try:
                archi_result = await self._ea_generate_archi(generate_xml=True)
                if archi_result.get('success'):
                    xml_updated = True
                    print(f"[+] Generated model.xml with {result['views_generated']} views")
            except Exception as e:
                print(f"[!] Warning: Failed to generate model.xml: {e}")
                return {
                    "success": False,
                    "error": f"Failed to generate model.xml: {e}"
                }

            return {
                "success": True,
                "phase": "finalized",
                "views_generated": result.get('views_generated', 0),
                "model_xml_updated": xml_updated,
                "output_file": result.get('output_file'),
                "message": "View generation complete! Import archi_inputs/model.xml into Archi tool."
            }

        except Exception as e:
            import traceback
            return {
                "success": False,
                "phase": "finalization_failed",
                "error": str(e),
                "traceback": traceback.format_exc()
            }

    async def _ea_list_view_specs(self) -> Dict[str, Any]:
        """List all view specifications"""
        try:
            import yaml
            specs_dir = Path("ea_inputs/views")
            specs = []

            if not specs_dir.exists():
                return {
                    "success": True,
                    "specs": [],
                    "count": 0,
                    "message": "No view specs found. Create YAML files in ea_inputs/views/"
                }

            for spec_file in specs_dir.glob("*.yaml"):
                try:
                    with open(spec_file, 'r', encoding='utf-8') as f:
                        spec = yaml.safe_load(f)

                    view_config = spec.get('view', {})
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
                    print(f"[!] Failed to read {spec_file.name}: {e}")

            return {
                "success": True,
                "specs": specs,
                "count": len(specs)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _ea_list_available_elements(self, element_type: Optional[str] = None) -> Dict[str, Any]:
        """List available elements from archi_inputs/"""
        try:
            import pandas as pd
            elements_file = Path("archi_inputs/elements.csv")

            if not elements_file.exists():
                return {
                    "success": True,
                    "elements": [],
                    "count": 0,
                    "message": "No elements found. Run ea_discover to create ArchiMate data."
                }

            df = pd.read_csv(elements_file)
            elements = [
                {'id': row['ID'], 'name': row['Name'], 'type': row['Type']}
                for _, row in df.iterrows()
            ]

            if element_type:
                elements = [e for e in elements if e['type'] == element_type]

            return {
                "success": True,
                "elements": elements,
                "count": len(elements)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _ea_generate_presentation_diagram(self, view_spec_path: str) -> Dict[str, Any]:
        """Generate a presentation-ready draw.io diagram from YAML view spec."""
        try:
            from ea.presentation_diagram_generator import generate_presentation_diagram

            # Validate spec exists
            spec_file = Path(view_spec_path)
            if not spec_file.exists():
                return {
                    "success": False,
                    "error": f"View spec not found: {view_spec_path}"
                }

            # Generate diagram
            output_file = generate_presentation_diagram(view_spec_path)

            return {
                "success": True,
                "output_file": output_file,
                "view_spec": view_spec_path,
                "message": f"Generated presentation diagram: {output_file}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "view_spec": view_spec_path
            }

    async def _ea_generate_diagram(self, spec_path: str) -> Dict[str, Any]:
        """Generate diagram from YAML spec with AI-driven layout (MVP8)."""
        try:
            from ea.drawio_generator import DrawIOGenerator

            # Validate spec exists
            spec_file = Path(spec_path)
            if not spec_file.exists():
                return {
                    "success": False,
                    "error": f"View spec not found: {spec_path}"
                }

            # Generate diagram
            generator = DrawIOGenerator()
            result = generator.generate(spec_path)

            if 'error' in result:
                return {
                    "success": False,
                    "error": result['error'],
                    "view_spec": spec_path
                }

            return {
                "success": True,
                "view_name": result.get('view_name'),
                "element_count": result.get('element_count'),
                "relationship_count": result.get('relationship_count'),
                "output_files": result.get('output_files', []),
                "view_spec": spec_path,
                "message": f"Generated {len(result.get('output_files', []))} diagram file(s)"
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "view_spec": spec_path
            }

    async def _ea_reset_model(self) -> Dict[str, Any]:
        """Reset EA model by clearing all cached and generated files"""
        try:
            import shutil

            cleared_items = []

            # Clear file cache
            cache_dir = Path(".file_cache")
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                cleared_items.append(".file_cache/")

            # Clear EA outputs
            ea_outputs_dir = Path("ea_outputs")
            if ea_outputs_dir.exists():
                for json_file in ea_outputs_dir.glob("*.json"):
                    json_file.unlink()
                    cleared_items.append(f"ea_outputs/{json_file.name}")

            # Clear ArchiMate files
            archi_dir = Path("archi_inputs")
            if archi_dir.exists():
                for csv_file in archi_dir.glob("*.csv"):
                    csv_file.unlink()
                    cleared_items.append(f"archi_inputs/{csv_file.name}")
                for xml_file in archi_dir.glob("*.xml"):
                    xml_file.unlink()
                    cleared_items.append(f"archi_inputs/{xml_file.name}")

            return {
                "success": True,
                "cleared_items": cleared_items,
                "count": len(cleared_items),
                "message": f"EA model reset complete. Cleared {len(cleared_items)} items."
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _ea_ingest_images(self, input_dir: str, output_dir: str) -> Dict[str, Any]:
        """Ingest images from directory using vision LLM"""
        try:
            from ea.image_ingestion import ingest_images_from_directory

            result = ingest_images_from_directory(
                input_dir=input_dir,
                output_dir=output_dir
            )

            return {
                "success": True,
                "input_dir": input_dir,
                "output_dir": output_dir,
                "images_found": result.get("total_images_found", 0),
                "processed": len(result.get("processed", [])),
                "skipped": len(result.get("skipped", [])),
                "failed": len(result.get("failed", [])),
                "summary": result.get("summary", {}),
                "processed_files": [p["file"] for p in result.get("processed", [])],
                "skipped_files": [{"file": s["file"], "reason": s["reason"]} for s in result.get("skipped", [])],
                "failed_files": [{"file": f["file"], "error": f["error"]} for f in result.get("failed", [])],
                "message": f"Processed {len(result.get('processed', []))} images, skipped {len(result.get('skipped', []))}, failed {len(result.get('failed', []))}. "
                          f"Extracted text files in {output_dir}/. Run ea_discover_directory('{output_dir}') to build EA model."
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }

    async def _ea_clear_image_cache(self) -> Dict[str, Any]:
        """Clear image ingestion cache"""
        try:
            from ea.image_ingestion import clear_image_cache

            result = clear_image_cache()

            return {
                "success": True,
                "cleared": result.get("cleared", False),
                "previous_stats": result.get("previous_stats", {}),
                "message": "Image ingestion cache cleared. All images will be re-processed on next run."
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    # ===== Presentation Tool Implementations =====

    async def _ea_generate_ppt(self, yaml_path: str, template_path: Optional[str] = None) -> Dict[str, Any]:
        """Generate PowerPoint from YAML slide plan"""
        try:
            yaml_file = Path(yaml_path)
            if not yaml_file.exists():
                return {
                    "success": False,
                    "error": f"YAML slide plan not found: {yaml_path}"
                }

            # Override template if provided
            if template_path:
                template_file = Path(template_path)
                if not template_file.exists():
                    return {
                        "success": False,
                        "error": f"Template not found: {template_path}"
                    }

            output_path = generate_ppt(yaml_path, output_path=None)

            return {
                "success": True,
                "output_file": output_path,
                "yaml_source": yaml_path,
                "template_used": template_path,
                "message": f"Generated PowerPoint: {output_path}"
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }

    async def _ea_inspect_ppt_template(self, template_path: str) -> Dict[str, Any]:
        """Inspect PowerPoint template layouts"""
        try:
            template_file = Path(template_path)
            if not template_file.exists():
                return {
                    "success": False,
                    "error": f"Template not found: {template_path}"
                }

            result = inspect_template(template_path)

            return {
                "success": True,
                "template": template_path,
                "layout_count": result.get("layout_count", 0),
                "layouts": result.get("layouts", []),
                "sample_slide_count": result.get("sample_slide_count", 0),
                "sample_slides": result.get("sample_slides", []),
                "message": f"Found {result.get('layout_count', 0)} layouts and {result.get('sample_slide_count', 0)} sample slides."
            }
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }


def main():
    """Main entry point for unified MCP server."""
    # Initialize unified server to register all tools
    server = UnifiedMCPServer()

    print("[*] Starting Unified PM/EA MCP Server...")
    print(f"   Available tools: {len(server.pm_server.get_available_tools()) + 4}")
    print("   - PM Tools: Azure DevOps work items, PRs, batch operations")
    print("   - EA Tools: Discovery, ArchiMate generation, Mermaid diagrams")
    print()

    # Run FastMCP server on stdio
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
