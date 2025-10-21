"""
Common interface for tools used by both PM and EA orchestrators.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class ToolInterface(ABC):
    """Common interface for tools that can be executed by orchestrators."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the tool name"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Return the tool description"""
        pass

    @abstractmethod
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute tool with given parameters.

        Args:
            parameters: Tool-specific parameters

        Returns:
            Dict containing execution results
        """
        pass

    @abstractmethod
    def get_parameter_schema(self) -> Dict[str, Any]:
        """
        Return tool parameter schema for validation.

        Returns:
            JSON schema describing expected parameters
        """
        pass

    @abstractmethod
    def get_supported_personas(self) -> List[str]:
        """
        Return list of personas that can use this tool.

        Returns:
            List of persona types ("PM", "EA", or both)
        """
        pass

    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Validate parameters against schema.
        Default implementation - can be enhanced by subclasses.

        Args:
            parameters: Parameters to validate

        Returns:
            True if parameters are valid
        """
        # Basic validation - real implementation would use jsonschema
        required_fields = self.get_parameter_schema().get("required", [])
        return all(field in parameters for field in required_fields)

    def supports_persona(self, persona: str) -> bool:
        """
        Check if tool supports a specific persona.

        Args:
            persona: Persona type to check ("PM" or "EA")

        Returns:
            True if tool supports the persona
        """
        return persona in self.get_supported_personas()