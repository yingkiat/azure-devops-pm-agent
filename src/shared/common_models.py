"""
Common data models shared between PM and EA personas.
These models enable cross-persona communication and context sharing.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum


class PersonaType(Enum):
    """Enumeration of available personas."""
    PM = "PM"
    EA = "EA"


class ContextType(Enum):
    """Types of context that can be shared between personas."""
    PROJECT = "project"
    REPOSITORY = "repository"
    TEAM = "team"
    WORK_ITEM = "work_item"
    ARCHITECTURE = "architecture"
    TECHNOLOGY = "technology"


@dataclass
class ProjectContext:
    """
    Shared project context between PM and EA personas.
    Contains information relevant to both project management and architecture.
    """
    project_name: str
    project_id: Optional[str] = None
    repositories: List[str] = field(default_factory=list)
    teams: List[str] = field(default_factory=list)

    # PM-specific context (when available)
    pm_context: Optional[Dict[str, Any]] = None
    work_item_count: Optional[int] = None
    active_sprints: List[str] = field(default_factory=list)
    team_members: List[str] = field(default_factory=list)

    # EA-specific context (when available)
    ea_context: Optional[Dict[str, Any]] = None
    architecture_components: List[str] = field(default_factory=list)
    technology_stack: List[str] = field(default_factory=list)
    integration_points: List[str] = field(default_factory=list)

    # Shared metadata
    last_updated: datetime = field(default_factory=datetime.utcnow)
    update_source: PersonaType = PersonaType.PM


@dataclass
class RepositoryContext:
    """
    Repository information shared between personas.
    Includes both PM (work tracking) and EA (architecture) perspectives.
    """
    project_name: str
    repository_name: str
    repository_id: Optional[str] = None
    default_branch: str = "main"

    # PM perspective
    active_pull_requests: int = 0
    recent_commits: int = 0
    assigned_work_items: List[str] = field(default_factory=list)
    responsible_teams: List[str] = field(default_factory=list)

    # EA perspective
    architecture_role: Optional[str] = None  # e.g., "frontend", "api", "data"
    technology_stack: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    interfaces: List[str] = field(default_factory=list)

    # README analysis (shared)
    readme_summary: Optional[str] = None
    capabilities: List[str] = field(default_factory=list)

    last_analyzed: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TeamContext:
    """
    Team information relevant to both PM and EA personas.
    """
    team_name: str
    team_members: List[str] = field(default_factory=list)

    # PM perspective
    current_workload: Optional[int] = None
    capacity: Optional[int] = None
    active_work_items: List[str] = field(default_factory=list)

    # EA perspective
    technical_expertise: List[str] = field(default_factory=list)
    owned_components: List[str] = field(default_factory=list)
    architecture_responsibilities: List[str] = field(default_factory=list)

    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SharedInsight:
    """
    An insight that combines PM and EA perspectives.
    """
    title: str
    description: str
    insight_type: str  # e.g., "risk", "opportunity", "recommendation"

    pm_data: Optional[Dict[str, Any]] = None
    ea_data: Optional[Dict[str, Any]] = None

    confidence: float = 0.0  # 0.0 to 1.0
    priority: str = "medium"  # "low", "medium", "high", "critical"

    actionable_items: List[str] = field(default_factory=list)
    affected_teams: List[str] = field(default_factory=list)
    affected_components: List[str] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.utcnow)
    source_persona: PersonaType = PersonaType.PM


@dataclass
class CrossPersonaResult:
    """
    Result that combines information from both PM and EA personas.
    Used when a request needs insights from both perspectives.
    """
    primary_persona: PersonaType
    secondary_persona: Optional[PersonaType] = None

    # Primary result (from main persona handling the request)
    primary_result: Dict[str, Any] = field(default_factory=dict)

    # Secondary context (from other persona, if needed)
    secondary_context: Optional[Dict[str, Any]] = None

    # Combined insights
    shared_insights: List[SharedInsight] = field(default_factory=list)
    cross_references: Dict[str, List[str]] = field(default_factory=dict)

    # Request metadata
    original_request: str = ""
    execution_time: float = 0.0
    success: bool = True
    errors: List[str] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PersonaBridge:
    """
    Configuration for cross-persona communication.
    Defines what data can be shared between personas.
    """
    enabled: bool = True

    # What PM data can be shared with EA
    pm_to_ea_sharing: List[str] = field(default_factory=lambda: [
        "project_context", "repository_context", "team_context"
    ])

    # What EA data can be shared with PM
    ea_to_pm_sharing: List[str] = field(default_factory=lambda: [
        "architecture_context", "technology_context", "dependency_context"
    ])

    # Cross-persona query triggers
    cross_query_triggers: List[str] = field(default_factory=lambda: [
        "impact", "risk", "dependency", "architecture", "team", "component"
    ])

    # Maximum context size to share (to avoid overwhelming the other persona)
    max_context_items: int = 10


# Utility functions for working with shared models

def create_project_context(project_name: str, persona: PersonaType, **kwargs) -> ProjectContext:
    """Create a project context from a specific persona perspective."""
    context = ProjectContext(project_name=project_name, update_source=persona)

    if persona == PersonaType.PM:
        context.pm_context = kwargs.get('pm_data', {})
        context.work_item_count = kwargs.get('work_item_count')
        context.active_sprints = kwargs.get('active_sprints', [])
        context.team_members = kwargs.get('team_members', [])
    elif persona == PersonaType.EA:
        context.ea_context = kwargs.get('ea_data', {})
        context.architecture_components = kwargs.get('architecture_components', [])
        context.technology_stack = kwargs.get('technology_stack', [])
        context.integration_points = kwargs.get('integration_points', [])

    return context


def merge_project_contexts(pm_context: ProjectContext, ea_context: ProjectContext) -> ProjectContext:
    """Merge PM and EA project contexts into a unified context."""
    if pm_context.project_name != ea_context.project_name:
        raise ValueError("Cannot merge contexts for different projects")

    merged = ProjectContext(
        project_name=pm_context.project_name,
        project_id=pm_context.project_id or ea_context.project_id,
        repositories=list(set(pm_context.repositories + ea_context.repositories)),
        teams=list(set(pm_context.teams + ea_context.teams)),

        # Merge PM data
        pm_context=pm_context.pm_context,
        work_item_count=pm_context.work_item_count,
        active_sprints=pm_context.active_sprints,
        team_members=pm_context.team_members,

        # Merge EA data
        ea_context=ea_context.ea_context,
        architecture_components=ea_context.architecture_components,
        technology_stack=ea_context.technology_stack,
        integration_points=ea_context.integration_points,

        last_updated=max(pm_context.last_updated, ea_context.last_updated),
        update_source=PersonaType.PM if pm_context.last_updated > ea_context.last_updated else PersonaType.EA
    )

    return merged


def extract_cross_references(pm_data: Dict[str, Any], ea_data: Dict[str, Any]) -> Dict[str, List[str]]:
    """Extract cross-references between PM and EA data."""
    cross_refs = {}

    # Example cross-reference extraction logic
    # This would be enhanced based on actual data structures

    if 'repositories' in pm_data and 'components' in ea_data:
        cross_refs['repo_to_component'] = []
        # Logic to match repositories to architecture components

    if 'teams' in pm_data and 'architecture_components' in ea_data:
        cross_refs['team_to_component'] = []
        # Logic to match teams to their owned components

    return cross_refs