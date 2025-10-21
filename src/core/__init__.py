"""
Core infrastructure for dual-persona AI assistant.
Provides base interfaces and common functionality for PM and EA modules.

MVP4 Enhancement: Working Journal System with persistent memory,
iterative refinement, and intelligent caching.
"""

from .interfaces.orchestrator_interface import OrchestratorInterface
from .base_orchestrator import BaseOrchestrator
from .persona_detector import PersonaDetector, PersonaDecision

# MVP4: Working Journal System
from .working_journal import WorkingJournal, DeliverableMetadata, ConversationEntry
from .file_monitor import FileChangeMonitor, FileInfo, ChangeSet
from .iteration_engine import IterationEngine, IntentType, IterationIntent
from .enhanced_ea_orchestrator import EnhancedEAOrchestrator
from .journal_cleanup import JournalCleanup, ContentAssessment, CleanupRule

__all__ = [
    # Base system
    'OrchestratorInterface',
    'BaseOrchestrator',
    'PersonaDetector',
    'PersonaDecision',

    # MVP4: Working Journal System
    'WorkingJournal',
    'DeliverableMetadata',
    'ConversationEntry',
    'FileChangeMonitor',
    'FileInfo',
    'ChangeSet',
    'IterationEngine',
    'IntentType',
    'IterationIntent',
    'EnhancedEAOrchestrator',
    'JournalCleanup',
    'ContentAssessment',
    'CleanupRule'
]