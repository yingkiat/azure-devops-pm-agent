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
from ea.view_builder import ViewBuilder

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
        self.view_builder = ViewBuilder(archi_inputs_dir="archi_inputs", specs_dir="ea_inputs/views")
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
                    generate_archimate_xml=True
                )

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

    async def _ea_discover_directory(self, directory: str, file_pattern: str) -> Dict[str, Any]:
        """Batch process all files in a directory with smart caching and output validation."""
        try:
            from pathlib import Path
            from core.file_monitor import FileChangeMonitor

            dir_path = Path(directory)
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
                "files_processed": [],
                "aggregated_counts": {
                    "total_applications": 0,
                    "total_capabilities": 0,
                    "total_relationships": 0
                },
                "errors": []
            }

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

            # First pass: read all files and create batches
            for file_path in files:
                # Skip non-data files (views, templates, README)
                file_path_str = str(file_path).lower()
                if any(skip in file_path_str for skip in ['views/', 'view_templates/', 'readme.md', '.yaml', '.yml']):
                    print(f"[*] Skipping non-data file: {file_path}")
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()

                    if not content:
                        print(f"[!] Skipping empty file: {file_path}")
                        continue

                    file_tokens = self._estimate_tokens(content)

                    # CSV files ALWAYS get their own batch (tabular structure requires complete processing)
                    is_csv = str(file_path).lower().endswith('.csv')

                    if is_csv:
                        batches.append(([content], [file_path]))
                        print(f"[*] CSV file (solo batch): {file_path} ({file_tokens} tokens)")
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
                    print(f"[!] Error reading {file_path}: {e}")
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

                        # Mark ALL files in batch as successfully processed
                        for file_path in batch_files:
                            file_monitor.mark_processed(
                                file_path=file_path,
                                insights=[],
                                discovered_elements=discovered_elements,
                                success=True
                            )

                            file_result = {
                                "file": file_path,
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

                        for file_path in batch_files:
                            file_monitor.mark_processed(
                                file_path=file_path,
                                insights=[],
                                success=False
                            )

                            file_result = {
                                "file": file_path,
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

    # ===== MVP6 Tool Implementations =====

    async def _ea_generate_views_from_specs(self) -> Dict[str, Any]:
        """Generate views.csv from YAML specifications and update model.xml"""
        try:
            # Generate views.csv from specs
            result = self.view_builder.generate_views_from_specs()

            # Regenerate complete model.xml with updated views
            # This ensures the ArchiMate package includes the new views
            xml_updated = False
            if result.get('views_generated', 0) > 0:
                try:
                    # Call ea_generate_archi to regenerate full package (including model.xml)
                    archi_result = await self._ea_generate_archi(generate_xml=True)
                    if archi_result.get('success'):
                        xml_updated = True
                        print(f"[+] Updated model.xml with {result['views_generated']} views")
                except Exception as e:
                    print(f"[!] Warning: Failed to update model.xml: {e}")

            return {
                "success": True,
                "model_xml_updated": xml_updated,
                **result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
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
