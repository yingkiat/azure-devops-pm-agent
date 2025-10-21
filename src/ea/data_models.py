"""
EA Data Models - Core data structures for EA artifact generation.

Defines the common data models that all EA data providers must supply.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


class LifecycleStatus(Enum):
    """Application lifecycle status."""
    STRATEGIC = "Strategic"
    MATURE = "Mature"
    MAINTENANCE = "Maintenance"
    SUNSET = "Sunset"
    RETIRED = "Retired"


class StrategicImportance(Enum):
    """Strategic importance levels."""
    CRITICAL = "Critical"
    IMPORTANT = "Important"
    STANDARD = "Standard"
    LOW = "Low"


@dataclass
class Application:
    """Represents an EA application/system."""
    name: str
    domain: str
    lifecycle_status: LifecycleStatus
    strategic_importance: StrategicImportance
    maturity: Optional[int] = None
    remaining_years: Optional[int] = None
    confidence: Optional[float] = None
    rationale: Optional[str] = None
    last_updated: Optional[str] = None

    @property
    def display_name(self) -> str:
        """Get display-friendly name."""
        return self.name.replace("_", " ").title()


@dataclass
class Capability:
    """Represents a business capability provided by an application."""
    name: str
    application_name: str
    domain: str
    maturity: Optional[int] = None
    confidence: Optional[float] = None
    rationale: Optional[str] = None

    @property
    def display_name(self) -> str:
        """Get display-friendly name."""
        return self.name.replace("_", " ").title()


@dataclass
class ApplicationCapability:
    """Represents the relationship between an application and its capabilities."""
    application: Application
    capability: Capability


@dataclass
class Domain:
    """Represents a business domain."""
    name: str
    applications: List[Application]

    @property
    def display_name(self) -> str:
        """Get display-friendly name."""
        return self.name.replace("_", " ").title()


@dataclass
class EASchema:
    """Represents the schema structure of EA data."""
    columns: List[str]
    required_fields: List[str]
    optional_fields: List[str]
    field_types: Dict[str, type]
    version: str = "1.0"

    def has_field(self, field_name: str) -> bool:
        """Check if schema contains a specific field."""
        return field_name in self.columns

    def get_missing_required_fields(self, available_fields: List[str]) -> List[str]:
        """Get list of missing required fields."""
        return [field for field in self.required_fields if field not in available_fields]

    def is_compatible(self, available_fields: List[str]) -> bool:
        """Check if available fields are compatible with this schema."""
        missing = self.get_missing_required_fields(available_fields)
        return len(missing) == 0


@dataclass
class EAData:
    """Unified EA data structure."""
    applications: List[Application]
    capabilities: List[Capability]
    domains: List[Domain]
    application_capabilities: List[ApplicationCapability]
    schema: EASchema
    metadata: Dict[str, Any]

    def get_applications_by_domain(self, domain_name: str) -> List[Application]:
        """Get all applications in a specific domain."""
        return [app for app in self.applications if app.domain == domain_name]

    def get_capabilities_by_application(self, app_name: str) -> List[Capability]:
        """Get all capabilities for a specific application."""
        return [cap for cap in self.capabilities if cap.application_name == app_name]

    def get_domains_list(self) -> List[str]:
        """Get unique list of domain names."""
        return list(set(app.domain for app in self.applications))

    def get_strategic_applications(self) -> List[Application]:
        """Get applications with strategic importance Critical or Important."""
        return [app for app in self.applications
                if app.strategic_importance in [StrategicImportance.CRITICAL, StrategicImportance.IMPORTANT]]

    def get_sunset_applications(self) -> List[Application]:
        """Get applications in sunset or maintenance phase."""
        return [app for app in self.applications
                if app.lifecycle_status in [LifecycleStatus.SUNSET, LifecycleStatus.MAINTENANCE]]


class FieldMapper:
    """Maps field names between different schema versions."""

    COMMON_MAPPINGS = {
        # Common field name variations
        'app_name': 'application_name',
        'application_name': 'app_name',
        'capability': 'capability_name',
        'capability_name': 'capability',
        'strategic_importance': 'importance',
        'importance': 'strategic_importance',
        'lifecycle_status': 'status',
        'status': 'lifecycle_status',
    }

    @classmethod
    def map_field_name(cls, field_name: str, available_fields: List[str]) -> Optional[str]:
        """Map a field name to an available field, handling common variations."""
        # Exact match first
        if field_name in available_fields:
            return field_name

        # Try common mappings
        if field_name in cls.COMMON_MAPPINGS:
            mapped_name = cls.COMMON_MAPPINGS[field_name]
            if mapped_name in available_fields:
                return mapped_name

        # Try case variations
        for available_field in available_fields:
            if field_name.lower() == available_field.lower():
                return available_field

        return None

    @classmethod
    def create_field_mapping(cls, required_fields: List[str], available_fields: List[str]) -> Dict[str, Optional[str]]:
        """Create a mapping from required fields to available fields."""
        mapping = {}
        for required_field in required_fields:
            mapping[required_field] = cls.map_field_name(required_field, available_fields)
        return mapping