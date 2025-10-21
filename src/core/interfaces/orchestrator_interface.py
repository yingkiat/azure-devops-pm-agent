"""
Common interface for PM and EA orchestrators.
Ensures consistent behavior across both personas.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class ClassifiedIntent:
    """Represents a classified user intent for any persona."""
    intent: str
    confidence: float
    description: str
    requires_context: bool
    suggested_actions: List[Dict[str, Any]]
    context_needed: List[str]
    ambiguities: List[str]
    persona: str  # "PM" or "EA"


class OrchestratorInterface(ABC):
    """Common interface that both PM and EA orchestrators must implement."""

    @property
    @abstractmethod
    def persona(self) -> str:
        """Return the persona type ('PM' or 'EA')"""
        pass

    @abstractmethod
    async def handle_request(self, user_request: str) -> Dict[str, Any]:
        """
        Process user request and return results.

        Args:
            user_request: Natural language request from user

        Returns:
            Dict containing success status, results, and metadata
        """
        pass

    @abstractmethod
    async def classify_intent(self, user_request: str) -> ClassifiedIntent:
        """
        Classify user intent for this persona.

        Args:
            user_request: Natural language request from user

        Returns:
            ClassifiedIntent with persona-specific classification
        """
        pass

    @abstractmethod
    def get_available_tools(self) -> List[str]:
        """
        Return list of available tools for this persona.

        Returns:
            List of tool names this orchestrator can execute
        """
        pass

    @abstractmethod
    def supports_intent(self, intent: str) -> bool:
        """
        Check if this orchestrator supports a given intent type.

        Args:
            intent: Intent type to check

        Returns:
            True if this orchestrator can handle the intent
        """
        pass

    def get_persona_info(self) -> Dict[str, Any]:
        """
        Get information about this persona's capabilities.

        Returns:
            Dict with persona metadata and capabilities
        """
        return {
            "persona": self.persona,
            "available_tools": self.get_available_tools(),
            "supported_intents": self.get_supported_intents()
        }

    def get_supported_intents(self) -> List[str]:
        """
        Get list of intents this persona supports.
        Default implementation - can be overridden by subclasses.

        Returns:
            List of supported intent types
        """
        return ["DISCOVERY", "QUERY", "ANALYSIS"]