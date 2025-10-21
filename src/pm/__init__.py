"""
PM Module - Project Management persona for the dual-persona AI assistant.

This module contains all PM-specific functionality migrated from the legacy
ai_orchestrator module. It provides:

- Natural language PM request handling
- Azure DevOps work item management
- Business intelligence and insights
- Team workload analysis
- Interactive work item creation
- Context management and wiki reporting

The PM orchestrator inherits from BaseOrchestrator and follows the standard
OrchestratorInterface for consistent behavior across personas.
"""

from .orchestrator import PMOrchestrator

__all__ = ["PMOrchestrator"]