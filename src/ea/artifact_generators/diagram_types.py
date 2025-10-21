"""
Diagram Types - Enums and configurations for different EA diagram types.
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any


class DiagramType(Enum):
    """Available EA diagram types."""
    APPLICATION_DOMAINS = "application_domains"
    CAPABILITY_MATRIX = "capability_matrix"
    LIFECYCLE_STATUS = "lifecycle_status"
    STRATEGIC_IMPORTANCE = "strategic_importance"
    DOMAIN_CAPABILITIES = "domain_capabilities"


@dataclass
class DiagramConfig:
    """Configuration for diagram generation."""
    required_fields: List[str]
    optional_fields: List[str]
    fallback_mode: str
    description: str
    mermaid_type: str  # 'graph', 'flowchart', 'pie', 'quadrantChart', etc.


# Configuration for each diagram type
DIAGRAM_CONFIGS: Dict[DiagramType, DiagramConfig] = {
    DiagramType.APPLICATION_DOMAINS: DiagramConfig(
        required_fields=['app_name', 'domain'],
        optional_fields=['strategic_importance', 'lifecycle_status'],
        fallback_mode='simple_app_list',
        description='Shows applications grouped by business domain',
        mermaid_type='graph'
    ),

    DiagramType.CAPABILITY_MATRIX: DiagramConfig(
        required_fields=['app_name', 'capability'],
        optional_fields=['domain', 'maturity'],
        fallback_mode='app_capability_list',
        description='Matrix showing applications and their capabilities',
        mermaid_type='graph'
    ),

    DiagramType.LIFECYCLE_STATUS: DiagramConfig(
        required_fields=['app_name', 'lifecycle_status'],
        optional_fields=['strategic_importance', 'remaining_years'],
        fallback_mode='app_list',
        description='Applications grouped by lifecycle status',
        mermaid_type='graph'
    ),

    DiagramType.STRATEGIC_IMPORTANCE: DiagramConfig(
        required_fields=['app_name', 'strategic_importance'],
        optional_fields=['domain', 'lifecycle_status'],
        fallback_mode='app_list',
        description='Applications grouped by strategic importance',
        mermaid_type='graph'
    ),

    DiagramType.DOMAIN_CAPABILITIES: DiagramConfig(
        required_fields=['domain', 'capability'],
        optional_fields=['app_name', 'maturity'],
        fallback_mode='domain_list',
        description='Business capabilities organized by domain',
        mermaid_type='graph'
    )
}


def get_diagram_config(diagram_type: DiagramType) -> DiagramConfig:
    """Get configuration for a specific diagram type."""
    return DIAGRAM_CONFIGS[diagram_type]


def get_available_diagram_types(available_fields: List[str]) -> List[DiagramType]:
    """Get list of diagram types that can be generated with available fields."""
    compatible_types = []

    for diagram_type, config in DIAGRAM_CONFIGS.items():
        # Check if all required fields are available
        if all(field in available_fields for field in config.required_fields):
            compatible_types.append(diagram_type)

    return compatible_types


def get_diagram_priority(diagram_type: DiagramType, available_optional_fields: List[str]) -> int:
    """Get priority score for diagram type based on available optional fields."""
    config = get_diagram_config(diagram_type)

    # Base priority
    base_priorities = {
        DiagramType.APPLICATION_DOMAINS: 100,
        DiagramType.CAPABILITY_MATRIX: 90,
        DiagramType.STRATEGIC_IMPORTANCE: 80,
        DiagramType.LIFECYCLE_STATUS: 70,
        DiagramType.DOMAIN_CAPABILITIES: 60
    }

    base_priority = base_priorities.get(diagram_type, 50)

    # Bonus for available optional fields
    available_optional = [field for field in config.optional_fields if field in available_optional_fields]
    optional_bonus = len(available_optional) * 10

    return base_priority + optional_bonus