"""
Enhanced EA Orchestrator with Working Journal Integration

Integrates the AI working journal system with EA operations, providing:
- Persistent memory across sessions
- Iterative refinement capabilities
- MVP3 diagram generation for testing iterative workflows
- Smart file caching for ea_inputs/
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

# Core system imports
from core.working_journal import WorkingJournal
from core.file_monitor import FileChangeMonitor
from core.iteration_engine import IterationEngine, IntentType
from core.base_orchestrator import BaseOrchestrator, ExecutionPlan, ExecutionResult
from core.interfaces.orchestrator_interface import OrchestratorInterface, ClassifiedIntent

# EA-specific imports
from ea.ea_discovery import EADiscovery
from ea.ea_diagrams import EADiagramGenerator


class EnhancedEAOrchestrator(BaseOrchestrator, OrchestratorInterface):
    """
    Enhanced EA Orchestrator with working journal and iterative capabilities

    Features:
    - Persistent session memory
    - Reference resolution ("that analysis", "the diagram")
    - Iterative refinement of deliverables
    - Smart caching for ea_inputs/ files
    - MVP3 diagram generation with iteration support
    """

    def __init__(self):
        # Initialize base orchestrator
        super().__init__(persona="EA")

        # Initialize journal system
        self.journal = WorkingJournal()
        self.file_monitor = FileChangeMonitor()
        self.iteration_engine = IterationEngine(self.journal)

        # Initialize EA tools
        self.ea_discovery = EADiscovery()
        self.diagram_generator = EADiagramGenerator()

        # Session state
        self.session_info = None

    def _read_file_content(self, file_path) -> str:
        """Read content from various file formats."""
        from pathlib import Path
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()

        try:
            if suffix == '.txt':
                return file_path.read_text(encoding='utf-8')

            elif suffix == '.csv':
                import pandas as pd
                df = pd.read_csv(file_path)
                # Convert CSV to readable text format
                return f"CSV File: {file_path.name}\n" + df.to_string(index=False)

            elif suffix in ['.xlsx', '.xls']:
                import pandas as pd
                # Read all sheets
                excel_data = pd.read_excel(file_path, sheet_name=None)
                content = f"Excel File: {file_path.name}\n\n"

                for sheet_name, df in excel_data.items():
                    content += f"Sheet: {sheet_name}\n"
                    content += df.to_string(index=False) + "\n\n"

                return content

            elif suffix in ['.docx', '.doc']:
                try:
                    from docx import Document
                    doc = Document(file_path)
                    content = f"Word Document: {file_path.name}\n\n"

                    for paragraph in doc.paragraphs:
                        if paragraph.text.strip():
                            content += paragraph.text + "\n"

                    return content
                except ImportError:
                    return f"Word Document: {file_path.name}\nError: python-docx library not installed"

            else:
                # Fallback to text reading
                return file_path.read_text(encoding='utf-8')

        except Exception as e:
            return f"Error reading {file_path.name}: {str(e)}"

    async def start_session(self) -> Dict[str, Any]:
        """Initialize enhanced session with context recovery"""
        self.session_info = self.journal.start_session()

        # Log session start thought
        self.journal._log_thought(f"Enhanced EA session started with {self.session_info['recovered_deliverables']} deliverables")

        return {
            **self.session_info,
            "enhanced_features": [
                "persistent_memory",
                "iterative_refinement",
                "reference_resolution",
                "smart_file_caching",
                "mvp3_diagram_generation"
            ]
        }

    async def handle_request(self, user_request: str) -> Dict[str, Any]:
        """
        Enhanced request handling with iteration support

        Handles both new requests and iterative refinements
        """
        try:
            # Start session if not already started
            if not self.session_info:
                await self.start_session()

            # Log incoming request
            self.journal._log_thought(f"Processing request: {user_request}")

            # Step 1: Check if this is an iterative request
            iteration_intent = self.iteration_engine.classify_intent(user_request)

            # DEBUG: Print intent classification
            print(f" Intent Classification:")
            print(f"   Type: {iteration_intent.intent_type.value}")
            print(f"   Confidence: {iteration_intent.confidence}")
            print(f"   Target Deliverables: {iteration_intent.target_deliverables}")
            print(f"   Requires New: {iteration_intent.requires_new_deliverable}")

            if iteration_intent.intent_type != IntentType.NEW_REQUEST:
                # Handle iterative request
                return await self._handle_iterative_request(user_request, iteration_intent)
            else:
                # Handle new request with traditional flow
                return await self._handle_new_request(user_request)

        except Exception as e:
            error_msg = f"Enhanced EA orchestrator error: {e}"
            self.journal._log_thought(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "persona": "EA"
            }

    async def _handle_iterative_request(self, user_request: str, iteration_intent) -> Dict[str, Any]:
        """Handle iterative refinement requests"""

        self.journal._log_thought(f"Iterative request detected: {iteration_intent.intent_type.value}")

        if iteration_intent.intent_type == IntentType.VISUALIZATION:
            # Handle "create a diagram" requests
            return await self._handle_visualization_request(user_request, iteration_intent)

        elif iteration_intent.intent_type == IntentType.MODIFICATION:
            # Handle "make it more detailed" requests
            return await self._handle_modification_request(user_request, iteration_intent)

        elif iteration_intent.intent_type == IntentType.REFINEMENT:
            # Handle "that missed security" requests
            return await self._handle_refinement_request(user_request, iteration_intent)

        elif iteration_intent.intent_type == IntentType.REFERENCE_QUERY:
            # Handle "show me that analysis" requests
            return await self._handle_reference_query(user_request, iteration_intent)

        else:
            return {
                "success": False,
                "error": f"Iterative intent {iteration_intent.intent_type.value} not yet implemented",
                "persona": "EA"
            }

    async def _handle_visualization_request(self, user_request: str, iteration_intent) -> Dict[str, Any]:
        """Handle visualization requests using MVP3"""

        self.journal._log_thought("Handling visualization request with MVP3")

        # Get context for visualization
        if iteration_intent.target_deliverables:
            # Use specific deliverable as source
            target_id = iteration_intent.target_deliverables[0]
            metadata, content = self.journal.get_deliverable(target_id)

            if not content:
                return {
                    "success": False,
                    "error": f"Could not load deliverable {target_id} for visualization",
                    "persona": "EA"
                }

            source_description = f"Based on {metadata.title}"
        else:
            # Use current EA matrix as source
            content = "Current EA analysis context"  # This would be actual EA data
            source_description = "Based on current EA analysis"

        try:
            # Generate diagram using MVP3
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            # For testing, we'll create a mock diagram result
            diagram_result = {
                "image_path": f"ai_journal/deliverables/diagram_{timestamp}.png",
                "text_path": f"ai_journal/deliverables/diagram_{timestamp}.txt",
                "diagram_type": "overview",
                "success": True
            }

            # Track the diagram as a deliverable
            deliverable_id = self.journal.track_deliverable(
                content=f"Visual diagram generated from: {source_description}",
                content_type="diagram",
                title=f"EA Visual Diagram - {timestamp}",
                file_extension=".png",
                description=f"Generated via MVP3: {iteration_intent.modification_description}"
            )

            # Log conversation
            self.journal.log_conversation(
                user_input=user_request,
                ai_response=f"Created visual diagram: {deliverable_id}",
                intent="VISUALIZATION",
                deliverables_created=[deliverable_id],
                success=True
            )

            return {
                "success": True,
                "persona": "EA",
                "classified_intent": {
                    "intent": "VISUALIZATION",
                    "confidence": iteration_intent.confidence,
                    "description": f"Generated visual diagram from {source_description}"
                },
                "execution_result": {
                    "results": [{
                        "step": 1,
                        "tool": "ea_generate_visual_diagram",
                        "success": True,
                        "data": {
                            **diagram_result,
                            "deliverable_id": deliverable_id,
                            "source": source_description
                        },
                        "purpose": "Generate visual diagram using MVP3"
                    }]
                },
                "deliverable_created": deliverable_id,
                "context_summary": self.journal.get_context_summary()
            }

        except Exception as e:
            self.journal._log_thought(f"Visualization error: {e}")
            return {
                "success": False,
                "error": f"Failed to generate visual diagram: {e}",
                "persona": "EA"
            }

    async def _handle_modification_request(self, user_request: str, iteration_intent) -> Dict[str, Any]:
        """Handle modification requests (e.g., 'make it more detailed')"""

        if not iteration_intent.target_deliverables:
            return {
                "success": False,
                "error": "Could not identify what to modify. Please be more specific.",
                "persona": "EA"
            }

        target_id = iteration_intent.target_deliverables[0]
        metadata, content = self.journal.get_deliverable(target_id)

        if not metadata:
            return {
                "success": False,
                "error": f"Could not find deliverable to modify: {target_id}",
                "persona": "EA"
            }

        self.journal._log_thought(f"Modifying deliverable {target_id}: {iteration_intent.modification_description}")

        # For MVP test - create modified version
        modified_content = f"MODIFIED: {content}\n\nModification applied: {iteration_intent.modification_description}"

        # Create new version
        new_deliverable_id = self.journal.track_deliverable(
            content=modified_content,
            content_type=metadata.type,
            title=f"{metadata.title} (Modified)",
            file_extension=".md",
            parent_id=target_id,
            description=f"Modified version: {iteration_intent.modification_description}"
        )

        # Log conversation
        self.journal.log_conversation(
            user_input=user_request,
            ai_response=f"Modified {metadata.title} → {new_deliverable_id}",
            intent="MODIFICATION",
            deliverables_modified=[target_id],
            deliverables_created=[new_deliverable_id],
            success=True
        )

        return {
            "success": True,
            "persona": "EA",
            "classified_intent": {
                "intent": "MODIFICATION",
                "confidence": iteration_intent.confidence,
                "description": f"Modified {metadata.title}"
            },
            "execution_result": {
                "results": [{
                    "step": 1,
                    "tool": "deliverable_modification",
                    "success": True,
                    "data": {
                        "original_deliverable": target_id,
                        "modified_deliverable": new_deliverable_id,
                        "modification": iteration_intent.modification_description,
                        "original_title": metadata.title
                    },
                    "purpose": "Modify existing deliverable based on user feedback"
                }]
            },
            "deliverable_modified": new_deliverable_id,
            "context_summary": self.journal.get_context_summary()
        }

    async def _handle_refinement_request(self, user_request: str, iteration_intent) -> Dict[str, Any]:
        """Handle refinement requests (e.g., 'that missed the security layer')"""

        # Similar to modification but specifically for adding missing content
        return await self._handle_modification_request(user_request, iteration_intent)

    async def _handle_reference_query(self, user_request: str, iteration_intent) -> Dict[str, Any]:
        """Handle reference queries (e.g., 'show me that analysis')"""

        if not iteration_intent.target_deliverables:
            return {
                "success": False,
                "error": "Could not identify what you're referring to.",
                "persona": "EA"
            }

        target_id = iteration_intent.target_deliverables[0]
        metadata, content = self.journal.get_deliverable(target_id)

        if not metadata:
            return {
                "success": False,
                "error": f"Could not find deliverable: {target_id}",
                "persona": "EA"
            }

        # Log conversation
        self.journal.log_conversation(
            user_input=user_request,
            ai_response=f"Retrieved {metadata.title}",
            intent="REFERENCE_QUERY",
            success=True
        )

        return {
            "success": True,
            "persona": "EA",
            "classified_intent": {
                "intent": "REFERENCE_QUERY",
                "confidence": iteration_intent.confidence,
                "description": f"Retrieved {metadata.title}"
            },
            "execution_result": {
                "results": [{
                    "step": 1,
                    "tool": "deliverable_retrieval",
                    "success": True,
                    "data": {
                        "deliverable_id": target_id,
                        "title": metadata.title,
                        "type": metadata.type,
                        "created_at": metadata.created_at,
                        "content_preview": str(content)[:200] + "..." if len(str(content)) > 200 else str(content)
                    },
                    "purpose": "Retrieve referenced deliverable"
                }]
            },
            "context_summary": self.journal.get_context_summary()
        }

    async def _handle_new_request(self, user_request: str) -> Dict[str, Any]:
        """Handle new requests using smart file monitoring"""

        # Step 1: Check for file changes in ea_inputs
        # TEMPORARY FIX: Disable file monitoring to force processing
        # workload = self.file_monitor.get_incremental_workload("ea_inputs")
        workload = {
            'processing_required': 0,
            'files_to_skip': 0,
            'files_to_process': [],
            'efficiency_gain_percent': 0
        }

        self.journal._log_thought(f"Processing new EA request (file monitoring disabled)")
        print(f" Processing new EA request")

        # Step 2: Classify intent
        classified_intent = await self.classify_intent(user_request)
        print(f" Classified Intent: {classified_intent.intent}")

        # Step 3: Create execution plan using LLM
        # Read all files from ea_inputs directory RECURSIVELY for context
        import os
        from pathlib import Path

        ea_inputs_dir = Path("ea_inputs")
        combined_content = []
        file_list = []

        if ea_inputs_dir.exists():
            # Use rglob to recursively find all files
            for file_path in ea_inputs_dir.rglob("*"):
                if file_path.is_file() and file_path.name != "README.md":
                    try:
                        content = self._read_file_content(file_path)
                        relative_path = file_path.relative_to(ea_inputs_dir)
                        combined_content.append(f"\n\n=== FILE: {relative_path} ===\n{content}")
                        file_list.append(str(relative_path))
                        print(f" Read file: {relative_path} ({len(content)} chars)")
                    except Exception as e:
                        print(f" Error reading {file_path.name}: {e}")

        all_content = "\n".join(combined_content)
        print(f" Total content: {len(all_content)} characters from {len(combined_content)} files")

        # Add file context to self.context for LLM planning
        self.context = {
            "ea_inputs_content": all_content,
            "ea_inputs_files": file_list,
            "available_tools": ["ea_discovery", "ea_generate_archi", "ea_generate_diagrams"]
        }

        # Let LLM create execution plan
        plan = await self.create_execution_plan(classified_intent, user_request)

        print(f" Execution Plan: {len(plan.execution_plan)} steps")
        for i, step in enumerate(plan.execution_plan):
            print(f"   Step {i+1}: {step['tool']} - {step.get('purpose', 'no purpose')}")

        # Step 4: Execute plan (without file monitoring for now)
        result = await self.execute_plan(plan)
        print(f" Execution Result: success={result.success}, results={len(result.results)}, errors={len(result.errors)}")

        # Step 5: Track results as deliverables
        if result.success and result.results:
            deliverable_ids = []
            for step_result in result.results:
                if step_result.get("success") and "data" in step_result:
                    # Track EA discovery results
                    if step_result["tool"] == "ea_discovery":
                        deliv_id = self.journal.track_deliverable(
                            content=step_result["data"],
                            content_type="analysis",
                            title=f"EA Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                            description=f"EA discovery from: {user_request}"
                        )
                        deliverable_ids.append(deliv_id)

            # Log conversation with deliverables
            self.journal.log_conversation(
                user_input=user_request,
                ai_response=f"Completed EA analysis - created {len(deliverable_ids)} deliverables",
                intent=classified_intent.intent,
                deliverables_created=deliverable_ids,
                success=result.success
            )

        return {
            "success": result.success,
            "persona": "EA",
            "classified_intent": {
                "intent": classified_intent.intent,
                "confidence": classified_intent.confidence,
                "description": classified_intent.description
            },
            "execution_result": {
                "results": result.results,
                "errors": result.errors
            },
            "file_efficiency": {
                "files_processed": workload['processing_required'],
                "files_cached": workload['files_to_skip'],
                "efficiency_gain": workload['efficiency_gain_percent']
            },
            "context_summary": self.journal.get_context_summary()
        }

    async def _execute_plan_with_monitoring(self, plan: ExecutionPlan, workload: Dict) -> ExecutionResult:
        """Execute plan with smart file monitoring"""

        # For now, delegate to parent class but with monitoring awareness
        result = await self.execute_plan(plan)

        # Mark processed files
        for file_path in workload['files_to_process']:
            # In a real implementation, we'd extract insights from the processing
            self.file_monitor.mark_processed(file_path, ["ea_analysis"], success=True)

        return result

    # Interface implementations (delegate to parent or provide EA-specific)
    async def classify_intent(self, user_request: str) -> ClassifiedIntent:
        """EA-specific intent classification"""
        return await super()._classify_intent_with_llm(user_request, self.context)

    async def execute_plan(self, plan: ExecutionPlan) -> ExecutionResult:
        """Execute the planned sequence of EA operations with journal integration"""
        results = []
        errors = []
        context_learned = {}

        try:
            for step in plan.execution_plan:
                step_num = step.get("step", "unknown")
                tool_name = step["tool"]
                parameters = step["parameters"]
                purpose = step.get("purpose", "No purpose specified")

                self.journal._log_thought(f"Executing step {step_num}: {tool_name} - {purpose}")

                try:
                    # Execute EA tool with journal integration
                    if tool_name == "ea_discovery":
                        text_input = parameters.get("text_input", "")

                        # Use matrix-aware discovery (includes full JSON + matrix updates)
                        ea_result = self.ea_discovery.discover_and_update_matrix(text_input)

                        # Save discovery section to ea_outputs as JSON
                        output_file = None
                        if "error" not in ea_result and "discovery" in ea_result:
                            from datetime import datetime
                            from pathlib import Path
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            output_file = f"ea_outputs/ea_analysis_{timestamp}.json"
                            # Save the full result which includes discovery + changes + exploration
                            self.ea_discovery.save_discovery(ea_result, output_file)
                            print(f"     Saved EA analysis to: {output_file}")
                        elif "error" not in ea_result:
                            # If no discovery section but no error, still save what we have
                            from datetime import datetime
                            from pathlib import Path
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            output_file = f"ea_outputs/ea_analysis_{timestamp}.json"
                            self.ea_discovery.save_discovery(ea_result, output_file)
                            print(f"     Saved EA result to: {output_file}")

                        results.append({
                            "step": step_num,
                            "tool": tool_name,
                            "success": "error" not in ea_result,
                            "data": ea_result,
                            "output_file": output_file,
                            "purpose": purpose
                        })

                        print(f"     EA Discovery completed (JSON + Matrix updated)")
                        self.journal._log_thought(f"EA Discovery completed with output file: {output_file}")

                    elif tool_name == "ea_generate_archi":
                        # Generate Archi-compatible CSV files
                        from ea.archi_export import ArchiExporter
                        from pathlib import Path
                        import glob

                        # Get the most recent EA analysis file
                        ea_files = glob.glob("ea_outputs/ea_analysis_*.json")
                        if ea_files:
                            latest_ea_file = max(ea_files, key=lambda x: Path(x).stat().st_mtime)
                            print(f"     Using EA file: {latest_ea_file}")

                            exporter = ArchiExporter(output_dir="archi_inputs")
                            output_files = exporter.export(latest_ea_file, generate_views=True, generate_archimate_xml=True)

                            results.append({
                                "step": step_num,
                                "tool": tool_name,
                                "success": True,
                                "data": {"output_files": output_files, "ea_file": latest_ea_file},
                                "purpose": purpose
                            })

                            print(f"     Archi export completed: {len(output_files)} files created")
                            self.journal._log_thought(f"Archi export completed with {len(output_files)} files")
                        else:
                            print(f"     No EA analysis file found in ea_outputs/")
                            results.append({
                                "step": step_num,
                                "tool": tool_name,
                                "success": False,
                                "data": {"error": "No EA analysis file found"},
                                "purpose": purpose
                            })

                    elif tool_name == "ea_generate_diagrams":
                        # Generate visual diagrams using Gemini
                        from pathlib import Path
                        import glob

                        diagram_type = parameters.get("diagram_type", "overview")

                        # Get the most recent EA analysis file
                        ea_files = glob.glob("ea_outputs/ea_analysis_*.json")
                        if ea_files:
                            latest_ea_file = max(ea_files, key=lambda x: Path(x).stat().st_mtime)
                            print(f"     Using EA file: {latest_ea_file}")

                            result_path = self.diagram_generator.generate_from_file(latest_ea_file, diagram_type)

                            results.append({
                                "step": step_num,
                                "tool": tool_name,
                                "success": True,
                                "data": {"diagram_path": result_path, "type": diagram_type},
                                "purpose": purpose
                            })

                            print(f"     Diagram generated: {result_path}")
                            self.journal._log_thought(f"Diagram generated: {result_path}")
                        else:
                            print(f"     No EA analysis file found in ea_outputs/")
                            results.append({
                                "step": step_num,
                                "tool": tool_name,
                                "success": False,
                                "data": {"error": "No EA analysis file found"},
                                "purpose": purpose
                            })

                    else:
                        # Handle unknown tools
                        print(f"     Unknown tool: {tool_name}")
                        results.append({
                            "step": step_num,
                            "tool": tool_name,
                            "success": False,
                            "data": {"error": f"Unknown tool: {tool_name}"},
                            "purpose": purpose
                        })

                except Exception as e:
                    error_msg = f"Step {step_num} failed: {e}"
                    errors.append(error_msg)
                    self.journal._log_thought(f"Error in step {step_num}: {e}")

                    results.append({
                        "step": step_num,
                        "tool": tool_name,
                        "success": False,
                        "data": {"error": str(e)},
                        "purpose": purpose
                    })

        except Exception as e:
            error_msg = f"Plan execution failed: {e}"
            errors.append(error_msg)
            self.journal._log_thought(f"Plan execution error: {e}")

        return ExecutionResult(
            success=len(errors) == 0,
            results=results,
            summary=f"Executed {len(results)} steps with {len(errors)} errors",
            errors=errors,
            context_learned=context_learned,
            persona="EA"
        )

    async def create_execution_plan(self, classified_intent: ClassifiedIntent, context: dict) -> ExecutionPlan:
        """Create execution plan with journal awareness"""
        # Use base class logic but with journal enhancements
        plan = await super().create_execution_plan(classified_intent, context)

        # Log plan creation
        self.journal._log_thought(f"Created execution plan for {classified_intent.intent} with {len(plan.execution_plan)} steps")

        return plan

    def get_available_tools(self) -> List[str]:
        """Enhanced tool list with MVP3 and journal capabilities"""
        return [
            "ea_discovery",
            "ea_generate_artifacts",
            "ea_generate_visual_diagram",  # MVP3 integration
            "deliverable_modification",     # Journal integration
            "deliverable_retrieval",       # Journal integration
            "file_monitoring_status"       # Monitoring integration
        ]

    def get_supported_intents(self) -> List[str]:
        """Get list of intents this enhanced EA persona supports"""
        return [
            "EA_DISCOVERY", "ARCHITECTURE_ANALYSIS", "CAPABILITY_MAPPING",
            "SYSTEM_ANALYSIS", "TECHNICAL_DISCOVERY",
            "VISUALIZATION", "MODIFICATION", "REFINEMENT", "REFERENCE_QUERY"
        ]

    def supports_intent(self, intent: str) -> bool:
        """Enhanced intent support including iterative intents"""
        return intent.upper() in self.get_supported_intents()