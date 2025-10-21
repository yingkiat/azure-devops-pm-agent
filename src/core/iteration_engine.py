"""
Iterative Refinement and Reference Resolution Engine

Handles natural language references like "that analysis", "the diagram"
and enables iterative modification of deliverables through conversation.
"""

import re
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from .working_journal import WorkingJournal, DeliverableMetadata


class IntentType(Enum):
    """Types of user intents for iteration"""
    NEW_REQUEST = "new_request"           # "analyze our platform"
    REFINEMENT = "refinement"             # "that missed the security layer"
    VISUALIZATION = "visualization"       # "create a diagram of this"
    MODIFICATION = "modification"         # "make it more detailed"
    REFERENCE_QUERY = "reference_query"   # "show me that analysis"
    VERSIONING = "versioning"             # "save this as final"


@dataclass
class IterationIntent:
    """Classified user intent with resolution details"""
    intent_type: IntentType
    confidence: float
    target_deliverables: List[str]  # Resolved deliverable IDs
    modification_description: str
    requires_new_deliverable: bool
    context_keywords: List[str]


class ReferenceResolver:
    """
    Resolves natural language references to specific deliverables

    Handles patterns like:
    - "that analysis" → most recent analysis
    - "the diagram" → most recent diagram
    - "my last report" → most recent report
    - "the security analysis" → analysis containing "security"
    """

    def __init__(self, journal: WorkingJournal):
        self.journal = journal

    def resolve(self, user_input: str) -> List[str]:
        """
        Resolve references in user input to deliverable IDs

        Returns list of deliverable IDs that match the reference
        """
        input_lower = user_input.lower()
        resolved_ids = []

        # Check if there are any reference indicators at all
        has_reference_indicators = (
            self._contains_demonstrative(input_lower) or
            self._has_definite_article_reference(input_lower) or
            any(phrase in input_lower for phrase in ["my last", "my previous", "my recent"])
        )

        # Pattern 1: Demonstrative pronouns (that, this)
        if self._contains_demonstrative(input_lower):
            demonstrative_ids = self._resolve_demonstrative(input_lower)
            resolved_ids.extend(demonstrative_ids)

        # Pattern 2: Definite articles with type (the diagram, the analysis)
        if "the " in input_lower:
            definite_ids = self._resolve_definite_article(input_lower)
            resolved_ids.extend(definite_ids)

        # Pattern 3: Possessive with recency (my last, my previous)
        if any(phrase in input_lower for phrase in ["my last", "my previous", "my recent"]):
            possessive_ids = self._resolve_possessive_recency(input_lower)
            resolved_ids.extend(possessive_ids)

        # Pattern 4: Content-based reference - ONLY if there are reference indicators
        # This prevents "create overview for Operations systems" from being treated as a reference
        if has_reference_indicators:
            content_ids = self._resolve_content_based(input_lower)
            resolved_ids.extend(content_ids)

        # Remove duplicates while preserving order
        return list(dict.fromkeys(resolved_ids))

    def _contains_demonstrative(self, text: str) -> bool:
        """Check if text contains demonstrative pronouns"""
        demonstratives = ["that", "this", "those", "these"]
        return any(word in text for word in demonstratives)

    def _has_definite_article_reference(self, text: str) -> bool:
        """Check if text has definite article reference patterns like 'the diagram', 'the analysis'"""
        reference_types = ["analysis", "diagram", "report", "overview", "chart", "graph", "visual"]
        return any(f"the {ref_type}" in text for ref_type in reference_types)

    def _resolve_demonstrative(self, text: str) -> List[str]:
        """Resolve 'that', 'this' to most recent deliverable in context"""
        if not self.journal.active_context:
            return []

        # Return most recent deliverable
        return [self.journal.active_context[-1]]

    def _resolve_definite_article(self, text: str) -> List[str]:
        """Resolve 'the [type]' references"""
        deliverable_types = {
            "analysis": "analysis",
            "diagram": "diagram",
            "report": "report",
            "overview": "overview",
            "chart": "diagram",
            "graph": "diagram",
            "visual": "diagram"
        }

        resolved_ids = []

        for keyword, deliv_type in deliverable_types.items():
            if f"the {keyword}" in text:
                # Find most recent deliverable of this type
                for deliv_id in reversed(self.journal.active_context):
                    if deliv_id in self.journal.deliverables:
                        deliv = self.journal.deliverables[deliv_id]
                        if deliv_type in deliv.type.lower() or deliv_type in deliv.title.lower():
                            resolved_ids.append(deliv_id)
                            break

        return resolved_ids

    def _resolve_possessive_recency(self, text: str) -> List[str]:
        """Resolve 'my last [type]' references"""
        recency_patterns = {
            "my last": -1,
            "my previous": -2,
            "my recent": -1
        }

        for pattern, index in recency_patterns.items():
            if pattern in text:
                # Extract type after the pattern
                match = re.search(f"{pattern}\\s+(\\w+)", text)
                if match:
                    target_type = match.group(1)

                    # Find deliverables of this type
                    type_deliverables = []
                    for deliv_id in self.journal.active_context:
                        if deliv_id in self.journal.deliverables:
                            deliv = self.journal.deliverables[deliv_id]
                            if (target_type in deliv.type.lower() or
                                target_type in deliv.title.lower()):
                                type_deliverables.append(deliv_id)

                    # Return the one at the specified index
                    if type_deliverables and abs(index) <= len(type_deliverables):
                        return [type_deliverables[index]]

        return []

    def _resolve_content_based(self, text: str) -> List[str]:
        """Resolve references based on content keywords"""
        resolved_ids = []

        # Extract potential content keywords
        content_keywords = [
            "security", "business", "application", "data", "infrastructure",
            "overview", "detailed", "summary", "architecture", "platform",
            "microservices", "api", "database", "network", "cloud"
        ]

        found_keywords = [kw for kw in content_keywords if kw in text]

        if found_keywords:
            # Search for deliverables containing these keywords
            for deliv_id in self.journal.active_context:
                if deliv_id in self.journal.deliverables:
                    deliv = self.journal.deliverables[deliv_id]
                    deliv_text = f"{deliv.title} {deliv.description}".lower()

                    # Check if any keywords match
                    if any(kw in deliv_text for kw in found_keywords):
                        resolved_ids.append(deliv_id)

        return resolved_ids


class IterationEngine:
    """
    Engine for iterative refinement of deliverables

    Handles:
    - Intent classification (NEW vs REFINEMENT vs MODIFICATION)
    - Reference resolution ("that", "this", "the diagram")
    - Content modification and versioning
    - Context management
    """

    def __init__(self, journal: WorkingJournal):
        self.journal = journal
        self.resolver = ReferenceResolver(journal)

    def classify_intent(self, user_input: str) -> IterationIntent:
        """
        Classify user intent and resolve any references

        Simple logic:
        1. Check for references to past deliverables
        2. If references found → REFERENCE_QUERY
        3. If no references → NEW_REQUEST
        """
        input_lower = user_input.lower()

        # Step 1: Try to resolve references
        target_deliverables = self.resolver.resolve(user_input)

        # Step 2: Simple classification
        if target_deliverables:
            # Found references to past work
            intent_type = IntentType.REFERENCE_QUERY
            requires_new = False
            confidence = 0.9
        else:
            # No references found - this is a new request
            intent_type = IntentType.NEW_REQUEST
            requires_new = True
            confidence = 0.95

        # Extract context keywords
        context_keywords = self._extract_context_keywords(user_input)

        return IterationIntent(
            intent_type=intent_type,
            confidence=confidence,
            target_deliverables=target_deliverables,
            modification_description="",
            requires_new_deliverable=requires_new,
            context_keywords=context_keywords
        )

    def _classify_intent_type(self, text: str) -> IntentType:
        """Classify the type of user intent"""

        # Refinement patterns
        refinement_patterns = [
            "that missed", "that's missing", "that lacks", "add to",
            "that's wrong", "incorrect", "fix", "update", "correct",
            "missing", "forgot", "should include", "also needs"
        ]

        # Modification patterns
        modification_patterns = [
            "make it", "make the", "more detailed", "more specific",
            "enhance", "improve", "better", "clearer", "larger",
            "smaller", "different", "change", "modify"
        ]

        # Visualization patterns
        visualization_patterns = [
            "create a diagram", "make a chart", "visualize", "show me",
            "generate diagram", "create visual", "draw", "illustrate"
        ]

        # Reference query patterns
        reference_patterns = [
            "show me that", "what was", "remind me", "tell me about",
            "display", "open", "view"
        ]

        # Versioning patterns
        versioning_patterns = [
            "save as", "save this", "final version", "keep this",
            "that's perfect", "good enough", "done"
        ]

        # Check patterns in order of specificity
        if any(pattern in text for pattern in versioning_patterns):
            return IntentType.VERSIONING
        elif any(pattern in text for pattern in refinement_patterns):
            return IntentType.REFINEMENT
        elif any(pattern in text for pattern in modification_patterns):
            return IntentType.MODIFICATION
        elif any(pattern in text for pattern in visualization_patterns):
            return IntentType.VISUALIZATION
        elif any(pattern in text for pattern in reference_patterns):
            return IntentType.REFERENCE_QUERY
        else:
            return IntentType.NEW_REQUEST

    def _extract_modification_description(self, user_input: str, intent_type: IntentType) -> str:
        """Extract what the user wants to modify/add"""

        if intent_type == IntentType.REFINEMENT:
            # Look for what's missing or needs to be added
            add_patterns = [
                r"add\s+(.+)",
                r"include\s+(.+)",
                r"missing\s+(.+)",
                r"needs?\s+(.+)",
                r"should\s+have\s+(.+)"
            ]

            for pattern in add_patterns:
                match = re.search(pattern, user_input, re.IGNORECASE)
                if match:
                    return match.group(1).strip()

        elif intent_type == IntentType.MODIFICATION:
            # Look for modification instructions
            mod_patterns = [
                r"make\s+it\s+(.+)",
                r"make\s+the\s+\w+\s+(.+)",
                r"more\s+(.+)",
                r"enhance\s+(.+)",
                r"improve\s+(.+)"
            ]

            for pattern in mod_patterns:
                match = re.search(pattern, user_input, re.IGNORECASE)
                if match:
                    return match.group(1).strip()

        return user_input  # Fallback to full input

    def _requires_new_deliverable(self, intent_type: IntentType,
                                 target_deliverables: List[str]) -> bool:
        """Determine if a new deliverable should be created"""

        if intent_type == IntentType.NEW_REQUEST:
            return True
        elif intent_type == IntentType.VISUALIZATION and not target_deliverables:
            return True
        elif intent_type == IntentType.VERSIONING:
            return True  # Create new version
        else:
            return False  # Modify existing

    def _extract_context_keywords(self, user_input: str) -> List[str]:
        """Extract relevant keywords for context"""
        keywords = [
            "security", "business", "application", "data", "infrastructure",
            "overview", "detailed", "architecture", "platform", "microservices",
            "api", "database", "network", "cloud", "diagram", "analysis", "report"
        ]

        found_keywords = [kw for kw in keywords if kw in user_input.lower()]
        return found_keywords

    def _calculate_confidence(self, text: str, intent_type: IntentType,
                            target_deliverables: List[str]) -> float:
        """Calculate confidence score for intent classification"""

        base_confidence = 0.7

        # Boost confidence for clear patterns
        if intent_type == IntentType.REFINEMENT and "missed" in text:
            base_confidence += 0.2
        elif intent_type == IntentType.MODIFICATION and "make it" in text:
            base_confidence += 0.2
        elif intent_type == IntentType.VISUALIZATION and "diagram" in text:
            base_confidence += 0.2

        # Boost confidence if references were resolved
        if target_deliverables:
            base_confidence += 0.1

        # Cap at 0.95
        return min(base_confidence, 0.95)

    def plan_iteration(self, iteration_intent: IterationIntent) -> Dict[str, Any]:
        """
        Plan how to execute the iteration

        Returns execution plan for the orchestrator
        """
        plan = {
            "intent": iteration_intent.intent_type.value,
            "confidence": iteration_intent.confidence,
            "target_deliverables": iteration_intent.target_deliverables,
            "modification_description": iteration_intent.modification_description,
            "execution_steps": []
        }

        if iteration_intent.intent_type == IntentType.REFINEMENT:
            # Plan to modify existing deliverable
            if iteration_intent.target_deliverables:
                plan["execution_steps"] = [
                    {
                        "action": "load_deliverable",
                        "target": iteration_intent.target_deliverables[0],
                        "purpose": "Load content for refinement"
                    },
                    {
                        "action": "refine_content",
                        "modification": iteration_intent.modification_description,
                        "purpose": "Apply user's refinement request"
                    },
                    {
                        "action": "save_deliverable",
                        "versioning": "increment",
                        "purpose": "Save refined version"
                    }
                ]
            else:
                plan["execution_steps"] = [
                    {
                        "action": "error",
                        "message": "Could not identify what to refine. Please be more specific."
                    }
                ]

        elif iteration_intent.intent_type == IntentType.VISUALIZATION:
            # Plan to create visual deliverable
            context_source = (iteration_intent.target_deliverables[0]
                            if iteration_intent.target_deliverables
                            else "current_context")

            plan["execution_steps"] = [
                {
                    "action": "load_context",
                    "source": context_source,
                    "purpose": "Get content to visualize"
                },
                {
                    "action": "generate_diagram",
                    "type": "visual",  # MVP3 integration point
                    "purpose": "Create visual representation"
                },
                {
                    "action": "save_deliverable",
                    "type": "diagram",
                    "purpose": "Store generated diagram"
                }
            ]

        elif iteration_intent.intent_type == IntentType.MODIFICATION:
            # Plan to modify existing deliverable
            if iteration_intent.target_deliverables:
                plan["execution_steps"] = [
                    {
                        "action": "load_deliverable",
                        "target": iteration_intent.target_deliverables[0],
                        "purpose": "Load content for modification"
                    },
                    {
                        "action": "modify_content",
                        "modification": iteration_intent.modification_description,
                        "purpose": "Apply user's modification request"
                    },
                    {
                        "action": "save_deliverable",
                        "versioning": "increment",
                        "purpose": "Save modified version"
                    }
                ]

        # Add context management
        plan["context_management"] = {
            "update_active_context": True,
            "new_deliverable_to_context": iteration_intent.requires_new_deliverable,
            "keywords_to_track": iteration_intent.context_keywords
        }

        return plan

    def execute_iteration_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single iteration step

        This is called by the orchestrator to perform specific iteration actions
        """
        action = step.get("action")

        if action == "load_deliverable":
            target_id = step.get("target")
            metadata, content = self.journal.get_deliverable(target_id)
            return {
                "success": True,
                "metadata": metadata,
                "content": content,
                "step_type": "load_deliverable"
            }

        elif action == "save_deliverable":
            # This would be called by orchestrator with actual content
            return {
                "success": True,
                "message": "Deliverable save planned - orchestrator will execute",
                "step_type": "save_deliverable"
            }

        elif action == "error":
            return {
                "success": False,
                "error": step.get("message", "Unknown error"),
                "step_type": "error"
            }

        else:
            return {
                "success": True,
                "message": f"Action '{action}' planned for orchestrator execution",
                "step_type": action
            }