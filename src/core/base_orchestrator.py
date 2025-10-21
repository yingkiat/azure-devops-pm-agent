"""
Base orchestrator providing common functionality for PM and EA personas.
"""

import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from utils.openai_client import client
from utils.json_fence import extract
from .interfaces.orchestrator_interface import OrchestratorInterface, ClassifiedIntent


@dataclass
class ExecutionPlan:
    """Represents an execution plan for fulfilling a request."""
    execution_plan: List[Dict[str, Any]]
    expected_outcome: str
    alternative_approaches: List[str]
    context_assumptions: Dict[str, Any]
    persona: str


@dataclass
class ExecutionResult:
    """Results from executing an orchestrated request."""
    success: bool
    results: List[Dict[str, Any]]
    summary: str
    errors: List[str]
    context_learned: Dict[str, Any]
    persona: str


class BaseOrchestrator:
    """
    Base class providing common orchestration functionality.
    To be inherited by PM and EA specific orchestrators.
    """

    def __init__(self, persona: str):
        self.client = client
        self._persona = persona
        self.context = {}  # Basic context storage

        # Set up prompts directory based on persona
        self.prompts_dir = Path(__file__).parent.parent.parent / "prompts" / persona.lower()

        # Create prompts directory if it doesn't exist
        self.prompts_dir.mkdir(parents=True, exist_ok=True)

    @property
    def persona(self) -> str:
        """Return the persona type"""
        return self._persona

    def _load_prompt(self, prompt_name: str) -> str:
        """Load a prompt template from the persona-specific prompts directory."""
        prompt_path = self.prompts_dir / f"{prompt_name}.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt not found: {prompt_path}")
        return prompt_path.read_text(encoding='utf-8')

    async def _classify_intent_with_llm(self, user_request: str, context: Dict[str, Any]) -> ClassifiedIntent:
        """
        Classify intent using LLM with persona-specific prompts.
        This is a common implementation that can be overridden by subclasses.
        """
        try:
            prompt_template = self._load_prompt("intent_classification")

            # Load domain knowledge for enhanced classification
            try:
                domain_knowledge = self._load_prompt("domain_knowledge")
                enhanced_prompt = f"{prompt_template}\n\n## Domain Knowledge Reference\n{domain_knowledge}"
            except FileNotFoundError:
                enhanced_prompt = prompt_template

            # Format prompt with user request and context
            prompt = enhanced_prompt.replace("{{user_request}}", user_request)
            prompt = prompt.replace("{{context}}", json.dumps(context, indent=2))

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a {self.persona} assistant intent classifier. Respond only with valid JSON."
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
                ambiguities=classification_data["ambiguities"],
                persona=self.persona
            )

        except Exception as e:
            # Fallback classification for errors
            return ClassifiedIntent(
                intent="QUERY",
                confidence=0.5,
                description=f"Fallback classification for: {user_request}",
                requires_context=True,
                suggested_actions=[{"tool": "discovery", "parameters": {}, "reason": "Fallback discovery"}],
                context_needed=["clarification"],
                ambiguities=[f"Classification failed: {e}"],
                persona=self.persona
            )

    async def create_execution_plan(self, classified_intent: ClassifiedIntent, user_request: str) -> ExecutionPlan:
        """Create execution plan using persona-specific execution planning prompt."""
        try:
            prompt_template = self._load_prompt("execution_planning")

            # Serialize classified_intent properly (handle nested objects)
            intent_dict = {
                "intent": classified_intent.intent,
                "confidence": classified_intent.confidence,
                "description": classified_intent.description,
                "requires_context": classified_intent.requires_context,
                "suggested_actions": classified_intent.suggested_actions if hasattr(classified_intent, 'suggested_actions') else [],
                "persona": classified_intent.persona if hasattr(classified_intent, 'persona') else self.persona
            }

            # Format prompt
            prompt = prompt_template.replace("{{classified_intent}}", json.dumps(intent_dict, indent=2))
            prompt = prompt.replace("{{context}}", json.dumps(self.context, indent=2) if self.context else "{}")
            prompt = prompt.replace("{{user_request}}", user_request)

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a {self.persona} execution planner. Respond only with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=10000  # Increased to handle large file content in execution plans
            )

            # Extract and parse JSON response
            response_text = response.choices[0].message.content
            extracted_json = extract(response_text)

            if not extracted_json:
                print(f"🐛 LLM Response (first 500 chars): {response_text[:500]}")
                raise ValueError("No valid JSON found in execution plan response")

            plan_data = json.loads(extracted_json)

            return ExecutionPlan(
                execution_plan=plan_data["execution_plan"],
                expected_outcome=plan_data["expected_outcome"],
                alternative_approaches=plan_data.get("alternative_approaches", []),
                context_assumptions=plan_data.get("context_assumptions", {}),
                persona=self.persona
            )

        except Exception as e:
            # Fallback execution plan
            return ExecutionPlan(
                execution_plan=[
                    {
                        "step": 1,
                        "tool": "discovery",
                        "parameters": {},
                        "purpose": f"Fallback discovery for failed planning: {e}",
                        "required": True
                    }
                ],
                expected_outcome="Basic discovery due to planning failure",
                alternative_approaches=["Manual tool selection"],
                context_assumptions={"fallback_mode": True},
                persona=self.persona
            )

    def _generate_session_id(self, user_request: str) -> str:
        """Generate a unique session ID for this interaction."""
        return f"{self.persona.lower()}_{hash(user_request + str(datetime.utcnow().timestamp()))}"

    def log_interaction(self, user_request: str, result: Dict[str, Any]):
        """
        Log interaction for debugging and learning.
        Subclasses can override for more sophisticated logging.
        """
        session_id = self._generate_session_id(user_request)
        print(f"[{self.persona}] Session {session_id}: {result.get('success', False)}")

    # Abstract methods that must be implemented by subclasses
    async def handle_request(self, user_request: str) -> Dict[str, Any]:
        """Must be implemented by persona-specific orchestrators"""
        raise NotImplementedError("Subclasses must implement handle_request")

    async def classify_intent(self, user_request: str) -> ClassifiedIntent:
        """Must be implemented by persona-specific orchestrators"""
        raise NotImplementedError("Subclasses must implement classify_intent")

    def get_available_tools(self) -> List[str]:
        """Must be implemented by persona-specific orchestrators"""
        raise NotImplementedError("Subclasses must implement get_available_tools")

    def supports_intent(self, intent: str) -> bool:
        """Must be implemented by persona-specific orchestrators"""
        raise NotImplementedError("Subclasses must implement supports_intent")