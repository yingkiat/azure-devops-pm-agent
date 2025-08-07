"""
AI Orchestrator for Azure DevOps operations.
Coordinates natural language requests through intent classification and MCP tool execution.
"""
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from utils.openai_client import client
from utils.json_fence import extract
from mcp_server.server import AzureDevOpsMCPServer
from ai_orchestrator.query_builder import SmartWIQLBuilder, QueryContext
from ai_orchestrator.insights_engine import InsightsEngine, BusinessIntelligence
from ai_orchestrator.context_manager import ContextManager
from ai_orchestrator.wiki_reporter import create_wiki_entry_from_ai_result


@dataclass
class ClassifiedIntent:
    """Represents a classified user intent."""
    intent: str
    confidence: float
    description: str
    requires_context: bool
    suggested_actions: List[Dict[str, Any]]
    context_needed: List[str]
    ambiguities: List[str]


@dataclass
class ExecutionPlan:
    """Represents an execution plan for fulfilling a request."""
    execution_plan: List[Dict[str, Any]]
    expected_outcome: str
    alternative_approaches: List[str]
    context_assumptions: Dict[str, Any]


@dataclass
class ExecutionResult:
    """Results from executing an orchestrated request."""
    success: bool
    results: List[Dict[str, Any]]
    summary: str
    errors: List[str]
    context_learned: Dict[str, Any]


class AzureDevOpsOrchestrator:
    """
    Orchestrates natural language requests through AI classification and MCP tool execution.
    """
    
    def __init__(self):
        self.client = client
        self.mcp_server = AzureDevOpsMCPServer()
        self.query_builder = SmartWIQLBuilder()
        self.insights_engine = InsightsEngine()
        self.context_manager = ContextManager()
        self.prompts_dir = Path(__file__).parent.parent.parent / "prompts"
        self.context = {}  # Maintains conversation context (legacy)
    
    def _load_prompt(self, prompt_name: str) -> str:
        """Load a prompt template from the prompts directory."""
        prompt_path = self.prompts_dir / f"{prompt_name}.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt not found: {prompt_path}")
        return prompt_path.read_text(encoding='utf-8')
    
    async def classify_intent(self, user_request: str) -> ClassifiedIntent:
        """Classify user intent using the intent classification prompt."""
        try:
            prompt_template = self._load_prompt("intent_classification")
            
            # Load domain knowledge for enhanced classification
            try:
                domain_knowledge = self._load_prompt("domain_knowledge")
                enhanced_prompt = f"{prompt_template}\n\n## Domain Knowledge Reference\n{domain_knowledge}"
            except:
                enhanced_prompt = prompt_template
            
            # Get relevant context for this request
            relevant_context = self.context_manager.get_relevant_context(user_request)
            
            # Format prompt with user request and context
            prompt = enhanced_prompt.replace("{{user_request}}", user_request)
            prompt = prompt.replace("{{context}}", json.dumps(relevant_context, indent=2))
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an Azure DevOps intent classifier. Respond only with valid JSON."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            # Extract and parse JSON response
            response_text = response.choices[0].message.content
            extracted_json = extract(response_text)
            
            if not extracted_json:
                raise ValueError("No valid JSON found in classification response")
            
            classification_data = json.loads(extracted_json)
            
            return ClassifiedIntent(
                intent=classification_data["intent"],
                confidence=classification_data["confidence"],
                description=classification_data["description"],
                requires_context=classification_data["requires_context"],
                suggested_actions=classification_data["suggested_actions"],
                context_needed=classification_data["context_needed"],
                ambiguities=classification_data["ambiguities"]
            )
            
        except Exception as e:
            # Fallback classification for errors
            return ClassifiedIntent(
                intent="QUERY",
                confidence=0.5,
                description=f"Fallback classification for: {user_request}",
                requires_context=True,
                suggested_actions=[{"tool": "get_projects", "parameters": {}, "reason": "Fallback discovery"}],
                context_needed=["clarification"],
                ambiguities=[f"Classification failed: {e}"]
            )
    
    async def create_execution_plan(self, classified_intent: ClassifiedIntent, user_request: str) -> ExecutionPlan:
        """Create execution plan using the execution planning prompt."""
        try:
            prompt_template = self._load_prompt("execution_planning")
            
            # Get relevant context for execution planning
            relevant_context = self.context_manager.get_relevant_context(user_request)
            
            # Format prompt
            prompt = prompt_template.replace("{{classified_intent}}", json.dumps(classified_intent.__dict__, indent=2))
            prompt = prompt.replace("{{context}}", json.dumps(relevant_context, indent=2))
            prompt = prompt.replace("{{user_request}}", user_request)
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an Azure DevOps execution planner. Respond only with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=1500
            )
            
            # Extract and parse JSON response
            response_text = response.choices[0].message.content
            extracted_json = extract(response_text)
            
            if not extracted_json:
                raise ValueError("No valid JSON found in execution plan response")
            
            plan_data = json.loads(extracted_json)
            
            return ExecutionPlan(
                execution_plan=plan_data["execution_plan"],
                expected_outcome=plan_data["expected_outcome"],
                alternative_approaches=plan_data.get("alternative_approaches", []),
                context_assumptions=plan_data.get("context_assumptions", {})
            )
            
        except Exception as e:
            # Fallback execution plan
            return ExecutionPlan(
                execution_plan=[
                    {
                        "step": 1,
                        "tool": "get_projects",
                        "parameters": {},
                        "purpose": f"Fallback discovery for failed planning: {e}",
                        "required": True
                    }
                ],
                expected_outcome="Basic project discovery due to planning failure",
                alternative_approaches=["Manual tool selection"],
                context_assumptions={"fallback_mode": True}
            )
    
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
                ambiguities=classified_intent.ambiguities
            )
            
        except Exception as e:
            print(f"⚠️  Query enhancement failed: {e}")
            return classified_intent  # Return original on failure
    
    async def handle_wiki_save(self, user_request: str) -> Optional[str]:
        """Handle wiki save requests by creating a wiki page from conversation context."""
        # Get content to push based on natural language request
        content_to_push = self.context_manager.get_wiki_push_content(user_request)
        
        if not content_to_push:
            print("⚠️  No conversation content available for wiki push")
            return None
        
        # Create the wiki content
        wiki_content = self._format_conversation_for_wiki(content_to_push, user_request)
        
        # Push to wiki using the wiki reporter
        from ai_orchestrator.wiki_reporter import AIWikiReporter
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
                f"**Success:** {'✅' if exchange.get('success') else '❌'}",
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
                                lines.append(f"- {tool}: {purpose}")
                        lines.append("")
        
        lines.extend([
            "---",
            f"*Manually documented at {timestamp}*",
            "",
            "**🔗 Related Actions:**",
            "- Continue analysis: `python -m src.cli.ai_cli chat`",
            f"- Related query: `python -m src.cli.ai_cli ask \"[related question]\"` "
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
                
                print(f"🔧 Step {step_num}: {tool_name} - {purpose}")
                
                try:
                    # Execute the MCP tool call
                    mcp_result = await self.mcp_server._handle_tool_call(tool_name, parameters)
                    
                    # Parse the MCP result (it returns TextContent objects)
                    if mcp_result and len(mcp_result) > 0:
                        result_text = mcp_result[0].text
                        result_data = json.loads(result_text)
                        
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
                                        "discovered_at": step_result.get("timestamp", "")
                                    })
                            elif tool_name == "get_repositories" and "repositories" in result_data:
                                repos = [r["name"] for r in result_data["repositories"]]
                                context_learned["available_repositories"] = repos
                            elif tool_name == "batch_project_overview" and "project_overviews" in result_data:
                                # Update project contexts with detailed information
                                for project_name, overview in result_data["project_overviews"].items():
                                    if "error" not in overview:
                                        self.context_manager.update_project_context(project_name, overview)
                        
                        print(f"   ✅ Success: {result_data.get('success', False)}")
                        
                    else:
                        raise ValueError("No result returned from MCP tool")
                        
                except Exception as step_error:
                    error_msg = f"Step {step_num} ({tool_name}) failed: {step_error}"
                    errors.append(error_msg)
                    print(f"   ❌ {error_msg}")
                    
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
                context_learned=context_learned
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                results=results,
                summary=f"Execution failed: {e}",
                errors=[str(e)],
                context_learned=context_learned
            )
    
    async def handle_request(self, user_request: str) -> Dict[str, Any]:
        """
        Handle a complete user request from natural language to results.
        This is the main entry point for the orchestrator.
        """
        print(f"🎯 Processing request: {user_request}")
        print("=" * 60)
        
        try:
            # Step 1: Classify intent
            print("🤖 Classifying intent...")
            classified_intent = await self.classify_intent(user_request)
            print(f"   Intent: {classified_intent.intent} (confidence: {classified_intent.confidence:.2f})")
            print(f"   Description: {classified_intent.description}")
            
            if classified_intent.ambiguities:
                print(f"   Ambiguities: {', '.join(classified_intent.ambiguities)}")
            
            # Step 1.5: Enhance with smart queries if applicable
            print("🔧 Enhancing with domain knowledge...")
            enhanced_intent = await self.enhance_with_smart_queries(classified_intent, user_request)
            if enhanced_intent.confidence > classified_intent.confidence:
                print(f"   Enhanced confidence: {enhanced_intent.confidence:.2f}")
                classified_intent = enhanced_intent
            
            # Step 2: Create execution plan
            print("\n📋 Creating execution plan...")
            execution_plan = await self.create_execution_plan(classified_intent, user_request)
            print(f"   Plan: {len(execution_plan.execution_plan)} steps")
            print(f"   Expected outcome: {execution_plan.expected_outcome}")
            
            # Step 3: Execute plan
            print("\n🚀 Executing plan...")
            execution_result = await self.execute_plan(execution_plan)
            
            print(f"\n📊 Results: {execution_result.summary}")
            
            # Generate business intelligence for ANALYSIS intents
            business_intelligence = None
            if classified_intent.intent == "ANALYSIS" and execution_result.success:
                print("\n🧠 Generating business intelligence...")
                try:
                    result_data = {
                        "execution_result": execution_result.__dict__
                    }
                    business_intelligence = self.insights_engine.create_business_intelligence(result_data)
                    print(f"   ✅ Generated insights for {len(business_intelligence.projects)} projects")
                except Exception as e:
                    print(f"   ⚠️  Business intelligence generation failed: {e}")
            
            # Return comprehensive result
            result = {
                "success": execution_result.success,
                "user_request": user_request,
                "classified_intent": classified_intent.__dict__,
                "execution_plan": execution_plan.__dict__,
                "execution_result": execution_result.__dict__,
                "context": self.context
            }
            
            if business_intelligence:
                result["business_intelligence"] = business_intelligence.__dict__
            
            # Learn from this interaction
            session_id = f"session_{hash(user_request + str(datetime.utcnow().timestamp()))}"
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
                        print(f"📝 Wiki entry created: {wiki_path}")
                    else:
                        result["wiki_error"] = "Failed to create wiki entry"
                except Exception as e:
                    result["wiki_error"] = f"Wiki creation failed: {e}"
                    print(f"⚠️  Wiki creation error: {e}")
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "user_request": user_request,
                "error": str(e),
                "context": self.context
            }