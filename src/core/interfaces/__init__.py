"""
Core interfaces for the dual-persona AI assistant.
"""

from .orchestrator_interface import OrchestratorInterface
from .tool_interface import ToolInterface

__all__ = ['OrchestratorInterface', 'ToolInterface']