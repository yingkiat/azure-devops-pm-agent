"""
PM Orchestrator - Project Management persona orchestrator.

Migrated from src/ai_orchestrator/orchestrator.py to implement the new dual-persona architecture.
Inherits from BaseOrchestrator and implements OrchestratorInterface.
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime

# Core architecture imports
from core.base_orchestrator import BaseOrchestrator, ExecutionPlan, ExecutionResult
from core.interfaces.orchestrator_interface import OrchestratorInterface, ClassifiedIntent

# PM-specific tool imports (migrated to new locations)
from .tools.mcp_client import OnDemandMCPClient
from .tools.query_builder import SmartWIQLBuilder, QueryContext
from .tools.insights_engine import InsightsEngine, BusinessIntelligence
from .context.context_manager import ContextManager
from .tools.work_item_classifier import WorkItemClassifier
from .tools.interactive_planner import InteractivePlanner


class PMOrchestrator(BaseOrchestrator, OrchestratorInterface):
    """
    PM Orchestrator for Azure DevOps project management operations.

    Coordinates natural language PM requests through intent classification and tool execution.
    Inherits common functionality from BaseOrchestrator and implements OrchestratorInterface.
    """

    def __init__(self):
        # Initialize base orchestrator with PM persona
        super().__init__(persona="PM")

        # Initialize PM-specific tools (on-demand MCP server creation)
        self.mcp_client = OnDemandMCPClient()
        self.query_builder = SmartWIQLBuilder()
        self.insights_engine = InsightsEngine()
        self.context_manager = ContextManager()
        self.work_item_classifier = WorkItemClassifier()
        self.interactive_planner = InteractivePlanner(self.mcp_client)

    # OrchestratorInterface implementation
    async def classify_intent(self, user_request: str) -> ClassifiedIntent:
        """Classify user intent using PM-specific prompts and context."""
        try:
            # Get relevant context for this request
            relevant_context = self.context_manager.get_relevant_context(user_request)

            # Use base class LLM classification with PM context
            classified_intent = await self._classify_intent_with_llm(user_request, relevant_context)

            return classified_intent

        except Exception as e:
            # Fallback classification for errors
            return ClassifiedIntent(
                intent="QUERY",
                confidence=0.5,
                description=f"Fallback PM classification for: {user_request}",
                requires_context=True,
                suggested_actions=[{"tool": "get_projects", "parameters": {}, "reason": "Fallback discovery"}],
                context_needed=["clarification"],
                ambiguities=[f"Classification failed: {e}"],
                persona="PM"
            )

    def get_available_tools(self) -> List[str]:
        """Return list of available PM tools dynamically."""
        # Get MCP tools dynamically
        mcp_tools = self.mcp_server.get_available_tools()

        # Add PM-specific orchestration tools
        pm_specific_tools = [
            "smart_wiql_builder",
            "insights_engine",
            "interactive_planner",
            "wiki_reporter"
        ]

        return mcp_tools + pm_specific_tools

    def supports_intent(self, intent: str) -> bool:
        """Check if this orchestrator supports a given intent type."""
        pm_intents = [
            "DISCOVERY",
            "QUERY",
            "ANALYSIS",
            "CREATE",
            "CREATE_WORK_ITEM",
            "CREATE_EPIC",
            "CREATE_FEATURE",
            "UPDATE",
            "WIKI_SAVE"
        ]
        return intent.upper() in pm_intents

    def get_supported_intents(self) -> List[str]:
        """Get list of intents this PM persona supports."""
        return [
            "DISCOVERY",
            "QUERY",
            "ANALYSIS",
            "CREATE",
            "CREATE_WORK_ITEM",
            "CREATE_EPIC",
            "CREATE_FEATURE",
            "UPDATE",
            "WIKI_SAVE"
        ]

    # PM-specific functionality (migrated from original orchestrator)
    async def enhance_with_smart_queries(self, classified_intent: ClassifiedIntent, user_request: str) -> ClassifiedIntent:
        """Enhance classified intent with smart WIQL queries where appropriate."""
        try:
            # Only enhance QUERY and ANALYSIS intents that might benefit from smart queries
            if classified_intent.intent not in ["QUERY", "ANALYSIS"]:
                return classified_intent

            # Parse the request to build query context
            available_projects = self.context.get("available_projects", [])
            query_context = self.query_builder.parse_natural_language_to_context(user_request, available_projects)

            # Generate optimized queries
            suggested_queries = self.query_builder.get_suggested_queries(query_context)

            # Enhance the suggested actions with smart queries
            enhanced_actions = []
            for action in classified_intent.suggested_actions:
                if action.get("tool") == "get_work_items":
                    # Replace basic query with smart query
                    if "work_items" in suggested_queries:
                        enhanced_action = action.copy()
                        enhanced_action["parameters"]["wiql_query"] = suggested_queries["work_items"]
                        enhanced_action["reason"] = f"Smart WIQL query based on: {query_context.__dict__}"
                        enhanced_actions.append(enhanced_action)

                        # Add summary query if it would be useful
                        if len(classified_intent.suggested_actions) == 1:  # Only one action, add summary
                            enhanced_actions.append({
                                "tool": "get_work_items",
                                "parameters": {"wiql_query": suggested_queries["summary"]},
                                "reason": "Summary query for better insights"
                            })
                    else:
                        enhanced_actions.append(action)
                else:
                    enhanced_actions.append(action)

            # Create enhanced intent
            return ClassifiedIntent(
                intent=classified_intent.intent,
                confidence=min(classified_intent.confidence + 0.1, 1.0),  # Slight confidence boost
                description=f"Enhanced: {classified_intent.description}",
                requires_context=classified_intent.requires_context,
                suggested_actions=enhanced_actions,
                context_needed=classified_intent.context_needed,
                ambiguities=classified_intent.ambiguities,
                persona="PM"
            )

        except Exception as e:
            print(f"  Query enhancement failed: {e}")
            return classified_intent  # Return original on failure

    async def handle_wiki_save(self, user_request: str) -> Optional[str]:
        """Handle wiki save requests by creating a wiki page from conversation context."""
        # Get content to push based on natural language request
        content_to_push = self.context_manager.get_wiki_push_content(user_request)

        if not content_to_push:
            print("  No conversation content available for wiki push")
            return None

        # Create the wiki content
        wiki_content = self._format_conversation_for_wiki(content_to_push, user_request)

        # Push to wiki using the wiki reporter
        from .context.wiki_reporter import AIWikiReporter
        reporter = AIWikiReporter()

        # Create a mock AI result for the wiki formatting
        mock_result = {
            "success": True,
            "user_request": f"Wiki documentation: {user_request}",
            "session_id": f"manual_push_{hash(user_request + str(datetime.utcnow().timestamp()))}",
            "conversation_content": content_to_push,
            "manual_push": True
        }

        return reporter.create_ai_report_entry(mock_result)

    def _format_conversation_for_wiki(self, content: List[Dict], original_request: str) -> str:
        """Format conversation content for wiki display."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

        lines = [
            f"# Conversation Documentation - {timestamp}",
            "",
            f"**Requested by:** {original_request}",
            f"**Content:** {len(content)} conversation exchange(s)",
            "",
            "## Conversation Details",
            ""
        ]

        for i, exchange in enumerate(content, 1):
            lines.extend([
                f"### Exchange {i} - {exchange.get('timestamp', 'Unknown time')}",
                f"**User:** {exchange['user_request']}",
                f"**AI Response:** {exchange['ai_response']}",
                f"**Intent:** {exchange.get('intent', 'Unknown')}",
                f"**Success:** {'' if exchange.get('success') else ''}",
                ""
            ])

            # Add detailed results if available
            if exchange.get('full_result') and exchange['success']:
                full_result = exchange['full_result']
                if 'execution_result' in full_result:
                    exec_result = full_result['execution_result']
                    if exec_result.get('results'):
                        lines.append("**Technical Details:**")
                        for result in exec_result['results']:
                            if result.get('success'):
                                tool = result.get('tool', 'unknown')
                                purpose = result.get('purpose', 'No purpose specified')
                                lines.append(f"- **{tool}**: {purpose}")
                        lines.append("")

        lines.extend([
            "---",
            f"*Manually documented at {timestamp}*",
            "",
            "** Quick Actions:**",
            "- Continue analysis: `python -m src.cli.ai_cli chat`",
            f"- Related query: `python -m src.cli.ai_cli ask \"[related question]\"`"
        ])

        return "\n".join(lines)

    async def execute_plan(self, plan: ExecutionPlan) -> ExecutionResult:
        """Execute the planned sequence of MCP tool calls."""
        results = []
        errors = []
        context_learned = {}

        try:
            for step in plan.execution_plan:
                step_num = step.get("step", "unknown")
                tool_name = step["tool"]
                parameters = step["parameters"]
                purpose = step.get("purpose", "No purpose specified")

                print(f" Step {step_num}: {tool_name} - {purpose}")

                try:
                    # Execute the MCP tool call using on-demand client
                    mcp_results = await self.mcp_client.call_tool(tool_name, parameters)

                    # Process the results (already parsed by the client)
                    if mcp_results and len(mcp_results) > 0:
                        result_data = mcp_results[0]  # Client returns parsed JSON directly

                        results.append({
                            "step": step_num,
                            "tool": tool_name,
                            "success": result_data.get("success", False),
                            "data": result_data,
                            "purpose": purpose
                        })

                        # Learn context from successful operations
                        if result_data.get("success"):
                            if tool_name == "get_projects" and "projects" in result_data:
                                projects = [p["name"] for p in result_data["projects"]]
                                context_learned["available_projects"] = projects
                                # Update context manager with discovered projects
                                for project in result_data["projects"]:
                                    self.context_manager.update_session_context(f"project_{project['name']}", {
                                        "id": project.get("id"),
                                        "state": project.get("state"),
                                        "discovered_at": result_data.get("timestamp", "")
                                    })
                            elif tool_name == "get_repositories" and "repositories" in result_data:
                                repos = [r["name"] for r in result_data["repositories"]]
                                context_learned["available_repositories"] = repos
                            elif tool_name == "batch_project_overview" and "project_overviews" in result_data:
                                # Update project contexts with detailed information
                                for project_name, overview in result_data["project_overviews"].items():
                                    if "error" not in overview:
                                        self.context_manager.update_project_context(project_name, overview)

                        print(f"     Success: {result_data.get('success', False)}")

                    else:
                        raise ValueError("No result returned from MCP tool")

                except Exception as step_error:
                    error_msg = f"Step {step_num} ({tool_name}) failed: {step_error}"
                    errors.append(error_msg)
                    print(f"     {error_msg}")

                    # Add failed step to results for transparency
                    results.append({
                        "step": step_num,
                        "tool": tool_name,
                        "success": False,
                        "error": str(step_error),
                        "purpose": purpose
                    })

            # Update orchestrator context
            self.context.update(context_learned)

            # Generate summary
            successful_steps = sum(1 for r in results if r.get("success", False))
            total_steps = len(results)
            summary = f"Executed {total_steps} steps, {successful_steps} successful"

            if errors:
                summary += f", {len(errors)} errors occurred"

            return ExecutionResult(
                success=len(errors) == 0,
                results=results,
                summary=summary,
                errors=errors,
                context_learned=context_learned,
                persona="PM"
            )

        except Exception as e:
            return ExecutionResult(
                success=False,
                results=results,
                summary=f"Execution failed: {e}",
                errors=[str(e)],
                context_learned=context_learned,
                persona="PM"
            )

    # Main orchestrator entry point (implements OrchestratorInterface)
    async def handle_request(self, user_request: str) -> Dict[str, Any]:
        """
        Handle a complete user request from natural language to results.
        This is the main entry point for the PM orchestrator.
        """
        print(f" [PM] Processing request: {user_request}")
        print("=" * 60)

        try:
            # Step 1: Classify intent
            print(" Classifying intent...")
            classified_intent = await self.classify_intent(user_request)
            print(f"   Intent: {classified_intent.intent} (confidence: {classified_intent.confidence:.2f})")
            print(f"   Description: {classified_intent.description}")

            if classified_intent.ambiguities:
                print(f"   Ambiguities: {', '.join(classified_intent.ambiguities)}")

            # Step 1.5: Enhance with smart queries if applicable
            print(" Enhancing with domain knowledge...")
            enhanced_intent = await self.enhance_with_smart_queries(classified_intent, user_request)
            if enhanced_intent.confidence > classified_intent.confidence:
                print(f"   Enhanced confidence: {enhanced_intent.confidence:.2f}")
                classified_intent = enhanced_intent

            # Check if this is a work item creation intent requiring interactive planning
            creation_intents = ["CREATE", "CREATE_WORK_ITEM", "CREATE_EPIC", "CREATE_FEATURE"]
            if any(keyword in classified_intent.intent.upper() for keyword in creation_intents):
                # Use interactive planning workflow
                return await self._handle_interactive_creation(user_request, classified_intent)

            # Step 2: Create execution plan (for non-creation intents)
            print("\n Creating execution plan...")
            execution_plan = await self.create_execution_plan(classified_intent, user_request)
            print(f"   Plan: {len(execution_plan.execution_plan)} steps")
            print(f"   Expected outcome: {execution_plan.expected_outcome}")

            # Step 3: Execute plan
            print("\n Executing plan...")
            execution_result = await self.execute_plan(execution_plan)

            print(f"\n Results: {execution_result.summary}")

            # Generate business intelligence for ANALYSIS intents
            business_intelligence = None
            if classified_intent.intent == "ANALYSIS" and execution_result.success:
                print("\n Generating business intelligence...")
                try:
                    result_data = {
                        "execution_result": execution_result.__dict__
                    }
                    business_intelligence = self.insights_engine.create_business_intelligence(result_data)
                    print(f"    Generated insights for {len(business_intelligence.projects)} projects")
                except Exception as e:
                    print(f"     Business intelligence generation failed: {e}")

            # Return comprehensive result
            result = {
                "success": execution_result.success,
                "user_request": user_request,
                "classified_intent": classified_intent.__dict__,
                "execution_plan": execution_plan.__dict__,
                "execution_result": execution_result.__dict__,
                "context": self.context,
                "persona": "PM"
            }

            if business_intelligence:
                result["business_intelligence"] = business_intelligence.__dict__

            # Learn from this interaction
            session_id = self._generate_session_id(user_request)
            self.context_manager.learn_from_interaction(
                user_request=user_request,
                classified_intent=classified_intent.__dict__,
                execution_result=result,
                session_id=session_id
            )

            # Add session context to result for reference
            result["session_id"] = session_id
            result["context_stats"] = self.context_manager.get_context_stats()

            # Handle WIKI_SAVE intent - manual wiki creation
            if classified_intent.intent == "WIKI_SAVE":
                try:
                    wiki_path = await self.handle_wiki_save(user_request)
                    if wiki_path:
                        result["wiki_report"] = wiki_path
                        print(f" Wiki entry created: {wiki_path}")
                    else:
                        result["wiki_error"] = "Failed to create wiki entry"
                except Exception as e:
                    result["wiki_error"] = f"Wiki creation failed: {e}"
                    print(f"  Wiki creation error: {e}")

            # Log interaction using base class method
            self.log_interaction(user_request, result)

            return result

        except Exception as e:
            error_result = {
                "success": False,
                "user_request": user_request,
                "error": str(e),
                "context": self.context,
                "persona": "PM"
            }

            # Log error interaction
            self.log_interaction(user_request, error_result)

            return error_result

    async def _handle_interactive_creation(self, user_request: str, classified_intent: ClassifiedIntent) -> Dict[str, Any]:
        """
        Handle work item creation requests with interactive approval workflow.
        Multi-stage process: Understand → Analyze → Propose → Approve → Execute
        """
        try:
            print("\n INTERACTIVE WORK ITEM CREATION MODE")
            print("=" * 50)

            # Get available projects (assuming user has access to all or specific ones)
            # This should be configurable or derived from context
            projects = self.context_manager.get_preferred_projects()
            if not projects:
                projects = ["DefaultProject"]  # Fallback - should be configurable

            # Stage 1: Multi-stage planning
            print(" Generating work item proposal...")
            proposal = await self.interactive_planner.plan_work_items(
                user_request, classified_intent.intent, projects
            )

            # Stage 2: Present proposal for approval
            print("\n" + "=" * 60)
            proposal_text = self.interactive_planner.format_proposal_for_approval(proposal)
            print(proposal_text)
            print("=" * 60)

            # Stage 3: Get user approval (interactive input)
            approval_response = input("\n Your decision: ").strip().lower()

            if approval_response in ['y', 'yes', 'approve']:
                # Stage 4: Execute approved proposal
                print("\n PROPOSAL APPROVED - Executing...")
                execution_result = await self.interactive_planner.execute_approved_proposal(proposal)

                if execution_result["success"]:
                    print(f" {execution_result['summary']}")

                    # Display created work items
                    print("\n CREATED WORK ITEMS:")
                    for item in execution_result["created_work_items"]:
                        parent_info = f" (Parent: #{item['parent_id']})" if item.get('parent_id') else ""
                        print(f"  #{item['id']}: {item['title']} ({item['type']}){parent_info}")
                        print(f"    Repository: {item['repository']}")
                else:
                    print(f" Execution failed: {execution_result['summary']}")
                    if execution_result["errors"]:
                        print("\nErrors:")
                        for error in execution_result["errors"]:
                            print(f"   {error}")

                # Learn from this interaction
                session_id = self._generate_session_id(user_request)
                self.context_manager.learn_from_interaction(
                    user_request=user_request,
                    classified_intent=classified_intent.__dict__,
                    execution_result={
                        "proposal": proposal.__dict__,
                        "execution_result": execution_result,
                        "approved": True
                    },
                    session_id=session_id
                )

                return {
                    "success": execution_result["success"],
                    "user_request": user_request,
                    "classified_intent": classified_intent.__dict__,
                    "proposal": {
                        "title": proposal.hierarchical_plan.primary_work_item.title,
                        "work_item_type": proposal.hierarchical_plan.primary_work_item.work_item_type.value,
                        "repository": proposal.hierarchical_plan.primary_work_item.target_repository,
                        "child_items_count": len(proposal.hierarchical_plan.child_items),
                        "estimated_timeline": proposal.estimated_timeline,
                        "confidence": proposal.confidence_score
                    },
                    "execution_result": execution_result,
                    "session_id": session_id,
                    "interaction_type": "interactive_creation_approved",
                    "persona": "PM"
                }

            elif approval_response in ['edit', 'modify', 'change']:
                print("\n EDIT MODE - This would allow proposal modifications")
                print("(Edit functionality not yet implemented)")
                return {
                    "success": False,
                    "user_request": user_request,
                    "message": "Edit mode requested but not yet implemented",
                    "interaction_type": "interactive_creation_edit_requested",
                    "persona": "PM"
                }

            elif approval_response in ['preview', 'details', 'show']:
                print("\n DETAILED PREVIEW")
                # Show more detailed work item content
                self._show_detailed_proposal_preview(proposal)

                # Ask for approval again after preview
                final_approval = input("\n After seeing details, approve? [y/N]: ").strip().lower()
                if final_approval in ['y', 'yes']:
                    # Recursive call to execute
                    return await self._handle_interactive_creation(user_request, classified_intent)
                else:
                    return {
                        "success": False,
                        "user_request": user_request,
                        "message": "Proposal rejected after detailed preview",
                        "interaction_type": "interactive_creation_rejected",
                        "persona": "PM"
                    }

            else:
                print("\n PROPOSAL REJECTED")
                return {
                    "success": False,
                    "user_request": user_request,
                    "message": "Work item creation proposal was rejected by user",
                    "interaction_type": "interactive_creation_rejected",
                    "persona": "PM"
                }

        except KeyboardInterrupt:
            print("\n\n Operation cancelled by user")
            return {
                "success": False,
                "user_request": user_request,
                "message": "Operation cancelled by user",
                "interaction_type": "interactive_creation_cancelled",
                "persona": "PM"
            }
        except Exception as e:
            print(f"\n Interactive creation failed: {e}")
            return {
                "success": False,
                "user_request": user_request,
                "error": str(e),
                "interaction_type": "interactive_creation_error",
                "persona": "PM"
            }

    def _show_detailed_proposal_preview(self, proposal):
        """Show detailed preview of the proposal including acceptance criteria."""
        print("\n DETAILED WORK ITEM PREVIEW")
        print("=" * 50)

        # Primary work item details
        primary = proposal.hierarchical_plan.primary_work_item
        print(f"\n PRIMARY: {primary.title}")
        print(f"Type: {primary.work_item_type.value}")
        print(f"Repository: {primary.target_repository}")
        print(f"Description: {primary.description}")
        print(f"Estimated Effort: {primary.estimated_effort}")

        if primary.acceptance_criteria:
            print("\nAcceptance Criteria:")
            for i, criteria in enumerate(primary.acceptance_criteria, 1):
                print(f"  {i}. {criteria}")

        if primary.dependencies:
            print(f"\nDependencies: {', '.join(primary.dependencies)}")

        # Child work items details
        if proposal.hierarchical_plan.child_items:
            print(f"\n CHILD ITEMS ({len(proposal.hierarchical_plan.child_items)}):")
            for i, child in enumerate(proposal.hierarchical_plan.child_items, 1):
                print(f"\n  {i}. {child.title} ({child.work_item_type.value})")
                print(f"     Repository: {child.target_repository}")
                print(f"     Effort: {child.estimated_effort}")
                if child.acceptance_criteria:
                    print(f"     Criteria: {len(child.acceptance_criteria)} items")

        print("\n" + "=" * 50)