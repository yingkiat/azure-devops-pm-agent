"""
PM Context - Context management and persistence for PM persona.

This package contains context-related functionality:
- Context manager for session memory and learning
- Wiki reporter for diary-style documentation
- User preference tracking and project context
"""

from .context_manager import ContextManager
from .wiki_reporter import AIWikiReporter

__all__ = ["ContextManager", "AIWikiReporter"]