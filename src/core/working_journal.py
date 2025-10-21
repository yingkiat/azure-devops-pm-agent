"""
AI Working Journal System - Persistent Memory and Session Management

Provides the AI with persistent memory across sessions, deliverable tracking,
and intelligent context reconstruction for iterative workflows.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import hashlib


@dataclass
class DeliverableMetadata:
    """Metadata for tracking AI-generated deliverables"""
    id: str
    type: str  # "analysis", "diagram", "report"
    title: str
    created_at: str
    modified_at: str
    file_path: str
    version: int
    parent_id: Optional[str] = None  # For versioning
    tags: List[str] = None
    description: str = ""

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class ConversationEntry:
    """Single conversation exchange for context tracking"""
    timestamp: str
    user_input: str
    ai_response: str
    intent: str
    deliverables_created: List[str]  # Deliverable IDs
    deliverables_modified: List[str]  # Deliverable IDs
    success: bool


class WorkingJournal:
    """
    AI Working Journal - Persistent memory and session management

    Provides:
    - Session persistence across restarts
    - Deliverable tracking and versioning
    - Context reconstruction
    - Reference resolution ("that analysis", "the diagram")
    """

    def __init__(self, journal_dir: str = "ai_journal"):
        self.journal_dir = Path(journal_dir)
        self.session_date = datetime.now().strftime('%Y-%m-%d')
        self.session_file = self.journal_dir / f"session_{self.session_date}.md"

        # Core directories
        self.context_dir = self.journal_dir / "context"
        self.deliverables_dir = self.journal_dir / "deliverables"
        self.thoughts_dir = self.journal_dir / "thoughts"

        # Core files
        self.deliverable_index_file = self.context_dir / "deliverable_index.json"
        self.conversation_context_file = self.context_dir / "conversation_context.json"
        self.current_analysis_file = self.context_dir / "current_analysis.md"

        # Runtime state
        self.deliverables: Dict[str, DeliverableMetadata] = {}
        self.conversation_history: List[ConversationEntry] = []
        self.active_context: List[str] = []  # Stack of what user is working on
        self.session_started = False

        self._ensure_structure()

    def _ensure_structure(self):
        """Create journal directory structure if it doesn't exist"""
        self.journal_dir.mkdir(exist_ok=True)
        self.context_dir.mkdir(exist_ok=True)
        self.deliverables_dir.mkdir(exist_ok=True)
        self.thoughts_dir.mkdir(exist_ok=True)

    def start_session(self) -> Dict[str, Any]:
        """
        Initialize session with context recovery
        Returns session info and recovered context
        """
        if self.session_started:
            return self._get_session_info()

        self._load_deliverable_index()
        self._load_conversation_context()

        # Log session start
        self._log_to_session(f"# AI Working Session - {self.session_date}\n")
        self._log_to_session(f"**Started:** {datetime.now().isoformat()}\n\n")

        # Check if automatic cleanup should be triggered
        cleanup_triggered = self._check_automatic_cleanup()

        # Context recovery
        context_summary = self._reconstruct_context()

        self.session_started = True
        return {
            "session_date": self.session_date,
            "recovered_deliverables": len(self.deliverables),
            "conversation_entries": len(self.conversation_history),
            "active_context": self.active_context.copy(),
            "context_summary": context_summary,
            "cleanup_triggered": cleanup_triggered
        }

    def _reconstruct_context(self) -> str:
        """Reconstruct working context from previous sessions"""
        if not self.conversation_history:
            return "No previous context found - starting fresh session."

        # Get recent successful conversations
        recent_convos = [c for c in self.conversation_history[-5:] if c.success]

        if not recent_convos:
            return "Previous session had no successful operations."

        # Identify active deliverables
        recent_deliverables = set()
        for convo in recent_convos:
            recent_deliverables.update(convo.deliverables_created)
            recent_deliverables.update(convo.deliverables_modified)

        context_parts = []
        context_parts.append(f"Found {len(recent_deliverables)} recent deliverables:")

        for deliv_id in recent_deliverables:
            if deliv_id in self.deliverables:
                deliv = self.deliverables[deliv_id]
                context_parts.append(f"  - {deliv.id}: {deliv.title} ({deliv.type})")
                self.active_context.append(deliv_id)

        # Log context reconstruction
        self._log_thought(f"Context Reconstruction: {'; '.join(context_parts)}")

        return "\n".join(context_parts)

    def log_conversation(self, user_input: str, ai_response: str,
                        intent: str, deliverables_created: List[str] = None,
                        deliverables_modified: List[str] = None, success: bool = True):
        """Log a conversation exchange"""
        if deliverables_created is None:
            deliverables_created = []
        if deliverables_modified is None:
            deliverables_modified = []

        entry = ConversationEntry(
            timestamp=datetime.now().isoformat(),
            user_input=user_input,
            ai_response=ai_response,
            intent=intent,
            deliverables_created=deliverables_created,
            deliverables_modified=deliverables_modified,
            success=success
        )

        self.conversation_history.append(entry)
        self._save_conversation_context()

        # Log to session file
        self._log_to_session(f"## {entry.timestamp}\n")
        self._log_to_session(f"**User:** {user_input}\n")
        self._log_to_session(f"**AI:** {ai_response}\n")
        self._log_to_session(f"**Intent:** {intent} | **Success:** {success}\n")
        if deliverables_created:
            self._log_to_session(f"**Created:** {', '.join(deliverables_created)}\n")
        if deliverables_modified:
            self._log_to_session(f"**Modified:** {', '.join(deliverables_modified)}\n")
        self._log_to_session("\n")

    def track_deliverable(self, content: Any, content_type: str,
                         title: str, file_extension: str = ".md",
                         parent_id: Optional[str] = None,
                         description: str = "") -> str:
        """
        Store and track a deliverable (analysis, diagram, report)
        Returns the deliverable ID for future reference
        """
        # Generate unique ID
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        deliv_id = f"{content_type}_{timestamp}"

        # Handle versioning
        version = 1
        if parent_id and parent_id in self.deliverables:
            version = self.deliverables[parent_id].version + 1
            deliv_id = f"{parent_id}_v{version}"

        # Determine file path
        file_name = f"{deliv_id}{file_extension}"
        file_path = self.deliverables_dir / file_name

        # Save content
        if isinstance(content, (dict, list)):
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
        else:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(str(content))

        # Create metadata
        metadata = DeliverableMetadata(
            id=deliv_id,
            type=content_type,
            title=title,
            created_at=datetime.now().isoformat(),
            modified_at=datetime.now().isoformat(),
            file_path=str(file_path),
            version=version,
            parent_id=parent_id,
            description=description
        )

        # Store and save
        self.deliverables[deliv_id] = metadata
        self._save_deliverable_index()

        # Add to active context
        if deliv_id not in self.active_context:
            self.active_context.append(deliv_id)

        self._log_thought(f"Tracked new deliverable: {deliv_id} - {title}")
        return deliv_id

    def get_deliverable(self, deliv_id: str) -> Tuple[Optional[DeliverableMetadata], Optional[Any]]:
        """Retrieve deliverable metadata and content"""
        if deliv_id not in self.deliverables:
            return None, None

        metadata = self.deliverables[deliv_id]

        try:
            file_path = Path(metadata.file_path)
            if not file_path.exists():
                return metadata, None

            # Try to load as JSON first, then as text
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = json.load(f)
            except json.JSONDecodeError:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

            return metadata, content
        except Exception as e:
            self._log_thought(f"Error loading deliverable {deliv_id}: {e}")
            return metadata, None

    def resolve_reference(self, user_input: str) -> List[str]:
        """
        Resolve natural language references to deliverable IDs
        Examples: "that analysis", "the diagram", "my last report"
        """
        input_lower = user_input.lower()

        # Simple reference patterns (to be enhanced)
        if "that" in input_lower or "this" in input_lower:
            # Return most recent deliverable in active context
            if self.active_context:
                return [self.active_context[-1]]

        if "diagram" in input_lower:
            # Find most recent diagram
            for deliv_id in reversed(self.active_context):
                if deliv_id in self.deliverables and "diagram" in self.deliverables[deliv_id].type:
                    return [deliv_id]

        if "analysis" in input_lower:
            # Find most recent analysis
            for deliv_id in reversed(self.active_context):
                if deliv_id in self.deliverables and "analysis" in self.deliverables[deliv_id].type:
                    return [deliv_id]

        return []

    def _log_thought(self, thought: str):
        """Log AI reasoning to thoughts file"""
        thoughts_file = self.thoughts_dir / "reasoning_log.md"
        timestamp = datetime.now().isoformat()

        with open(thoughts_file, 'a', encoding='utf-8') as f:
            f.write(f"**{timestamp}:** {thought}\n")

    def _log_to_session(self, content: str):
        """Append content to session log"""
        with open(self.session_file, 'a', encoding='utf-8') as f:
            f.write(content)

    def _load_deliverable_index(self):
        """Load deliverable index from disk"""
        if self.deliverable_index_file.exists():
            try:
                with open(self.deliverable_index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self.deliverables = {
                    deliv_id: DeliverableMetadata(**deliv_data)
                    for deliv_id, deliv_data in data.items()
                }
            except Exception as e:
                self._log_thought(f"Error loading deliverable index: {e}")

    def _save_deliverable_index(self):
        """Save deliverable index to disk"""
        try:
            data = {
                deliv_id: asdict(metadata)
                for deliv_id, metadata in self.deliverables.items()
            }

            with open(self.deliverable_index_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self._log_thought(f"Error saving deliverable index: {e}")

    def _load_conversation_context(self):
        """Load conversation history from disk"""
        if self.conversation_context_file.exists():
            try:
                with open(self.conversation_context_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self.conversation_history = [
                    ConversationEntry(**entry_data)
                    for entry_data in data.get("conversations", [])
                ]
                self.active_context = data.get("active_context", [])
            except Exception as e:
                self._log_thought(f"Error loading conversation context: {e}")

    def _save_conversation_context(self):
        """Save conversation history to disk"""
        try:
            data = {
                "conversations": [asdict(entry) for entry in self.conversation_history],
                "active_context": self.active_context
            }

            with open(self.conversation_context_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self._log_thought(f"Error saving conversation context: {e}")

    def _get_session_info(self) -> Dict[str, Any]:
        """Get current session information"""
        return {
            "session_date": self.session_date,
            "deliverables_count": len(self.deliverables),
            "conversation_entries": len(self.conversation_history),
            "active_context": self.active_context.copy(),
            "session_started": self.session_started
        }

    def get_context_summary(self) -> str:
        """Get a human-readable summary of current context"""
        if not self.active_context:
            return "No active context - ready for new work."

        summary_parts = [f"Working with {len(self.active_context)} deliverables:"]

        for deliv_id in self.active_context[-3:]:  # Show last 3
            if deliv_id in self.deliverables:
                deliv = self.deliverables[deliv_id]
                summary_parts.append(f"  - {deliv.title} ({deliv.type})")

        return "\n".join(summary_parts)

    def _check_automatic_cleanup(self) -> bool:
        """Check if automatic cleanup should be triggered"""
        try:
            # Import here to avoid circular dependencies
            from .journal_cleanup import JournalCleanup

            cleanup_system = JournalCleanup(self)
            should_cleanup = cleanup_system.schedule_cleanup(max_age_days=7, max_deliverables=50)

            if should_cleanup:
                self._log_thought("Automatic cleanup triggered - recommend running cleanup")
                return True
            else:
                return False

        except Exception as e:
            self._log_thought(f"Cleanup check failed: {e}")
            return False

    def cleanup_journal(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Perform intelligent cleanup of journal content

        Args:
            dry_run: If True, only simulate cleanup without making changes

        Returns:
            Cleanup report with results and recommendations
        """
        try:
            from .journal_cleanup import JournalCleanup

            cleanup_system = JournalCleanup(self)
            report = cleanup_system.smart_cleanup(dry_run=dry_run)

            # Log cleanup activity
            action = "Simulated" if dry_run else "Executed"
            self._log_thought(f"{action} cleanup: {report['analysis']['to_delete']} items identified for removal")

            return report

        except Exception as e:
            error_msg = f"Cleanup failed: {e}"
            self._log_thought(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }