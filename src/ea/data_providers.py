"""
EA Data Providers - Abstract interface and concrete implementations for EA data sources.

Provides a unified interface for accessing EA data from various sources (CSV, JSON, database, etc.)
with automatic schema detection and field mapping capabilities.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
import csv

from .data_models import (
    EAData, Application, Capability, Domain, ApplicationCapability,
    EASchema, LifecycleStatus, StrategicImportance, FieldMapper
)


class EADataProvider(ABC):
    """Abstract interface for EA data sources."""

    @abstractmethod
    def get_ea_data(self) -> EAData:
        """Get unified EA data structure."""
        pass

    @abstractmethod
    def get_schema(self) -> EASchema:
        """Get the schema of the data source."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the data source is available."""
        pass


class CSVMatrixProvider(EADataProvider):
    """Provider for EA matrix CSV files."""

    # Required fields for basic functionality
    REQUIRED_FIELDS = ['app_name', 'capability', 'domain']

    # Optional fields that enhance diagram generation
    OPTIONAL_FIELDS = [
        'maturity', 'lifecycle_status', 'strategic_importance',
        'remaining_years', 'confidence', 'rationale', 'last_updated'
    ]

    def __init__(self, csv_path: str):
        self.csv_path = Path(csv_path)
        self._schema: Optional[EASchema] = None
        self._field_mapping: Optional[Dict[str, Optional[str]]] = None

    def is_available(self) -> bool:
        """Check if CSV file exists and is readable."""
        return self.csv_path.exists() and self.csv_path.is_file()

    def get_schema(self) -> EASchema:
        """Detect and return the schema of the CSV file."""
        if self._schema is None:
            self._schema = self._detect_schema()
        return self._schema

    def get_ea_data(self) -> EAData:
        """Load and parse CSV data into unified EA structure."""
        if not self.is_available():
            raise FileNotFoundError(f"EA matrix CSV not found: {self.csv_path}")

        df = pd.read_csv(self.csv_path)
        if df.empty:
            return self._create_empty_ea_data()

        schema = self.get_schema()
        field_mapping = self._get_field_mapping(list(df.columns))

        applications = self._extract_applications(df, field_mapping)
        capabilities = self._extract_capabilities(df, field_mapping)
        domains = self._extract_domains(applications)
        app_capabilities = self._create_app_capability_relationships(applications, capabilities)

        metadata = {
            'source_file': str(self.csv_path),
            'record_count': len(df),
            'application_count': len(applications),
            'capability_count': len(capabilities),
            'domain_count': len(domains),
            'field_mapping': field_mapping
        }

        return EAData(
            applications=applications,
            capabilities=capabilities,
            domains=domains,
            application_capabilities=app_capabilities,
            schema=schema,
            metadata=metadata
        )

    def _detect_schema(self) -> EASchema:
        """Detect the schema structure of the CSV file."""
        if not self.is_available():
            raise FileNotFoundError(f"EA matrix CSV not found: {self.csv_path}")

        # Read just the header to get column names
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            columns = next(reader, [])

        field_mapping = FieldMapper.create_field_mapping(self.REQUIRED_FIELDS, columns)

        # Determine which required fields are available
        available_required = [field for field, mapping in field_mapping.items() if mapping is not None]

        # Determine field types (simplified for now)
        field_types = {
            'app_name': str,
            'capability': str,
            'domain': str,
            'maturity': int,
            'lifecycle_status': str,
            'strategic_importance': str,
            'remaining_years': int,
            'confidence': float,
            'rationale': str,
            'last_updated': str
        }

        return EASchema(
            columns=columns,
            required_fields=self.REQUIRED_FIELDS,
            optional_fields=self.OPTIONAL_FIELDS,
            field_types=field_types,
            version="csv_matrix_1.0"
        )

    def _get_field_mapping(self, available_columns: List[str]) -> Dict[str, Optional[str]]:
        """Get field mapping from required fields to available columns."""
        if self._field_mapping is None:
            all_fields = self.REQUIRED_FIELDS + self.OPTIONAL_FIELDS
            self._field_mapping = FieldMapper.create_field_mapping(all_fields, available_columns)
        return self._field_mapping

    def _extract_applications(self, df: pd.DataFrame, field_mapping: Dict[str, Optional[str]]) -> List[Application]:
        """Extract unique applications from the matrix."""
        app_name_col = field_mapping.get('app_name')
        if not app_name_col:
            raise ValueError("Cannot find application name column in CSV")

        domain_col = field_mapping.get('domain', app_name_col)  # Fallback to app name if no domain

        # Get unique applications
        app_data = df[[app_name_col, domain_col]].drop_duplicates()

        applications = []
        for _, row in app_data.iterrows():
            app_name = str(row[app_name_col])
            domain = str(row[domain_col]) if domain_col in df.columns else "Unknown"

            # Extract optional fields for this application
            app_rows = df[df[app_name_col] == app_name]

            # Use the first occurrence for app-level attributes, or aggregate if needed
            first_row = app_rows.iloc[0]

            lifecycle_status = self._safe_get_enum_value(
                first_row, field_mapping.get('lifecycle_status'), LifecycleStatus, LifecycleStatus.STRATEGIC
            )

            strategic_importance = self._safe_get_enum_value(
                first_row, field_mapping.get('strategic_importance'), StrategicImportance, StrategicImportance.STANDARD
            )

            application = Application(
                name=app_name,
                domain=domain,
                lifecycle_status=lifecycle_status,
                strategic_importance=strategic_importance,
                maturity=self._safe_get_numeric(first_row, field_mapping.get('maturity')),
                remaining_years=self._safe_get_numeric(first_row, field_mapping.get('remaining_years')),
                confidence=self._safe_get_float(first_row, field_mapping.get('confidence')),
                rationale=self._safe_get_string(first_row, field_mapping.get('rationale')),
                last_updated=self._safe_get_string(first_row, field_mapping.get('last_updated'))
            )
            applications.append(application)

        return applications

    def _extract_capabilities(self, df: pd.DataFrame, field_mapping: Dict[str, Optional[str]]) -> List[Capability]:
        """Extract capabilities from the matrix."""
        app_name_col = field_mapping.get('app_name')
        capability_col = field_mapping.get('capability')
        domain_col = field_mapping.get('domain')

        if not all([app_name_col, capability_col]):
            raise ValueError("Cannot find required columns for capabilities")

        capabilities = []
        for _, row in df.iterrows():
            capability = Capability(
                name=str(row[capability_col]),
                application_name=str(row[app_name_col]),
                domain=str(row[domain_col]) if domain_col else "Unknown",
                maturity=self._safe_get_numeric(row, field_mapping.get('maturity')),
                confidence=self._safe_get_float(row, field_mapping.get('confidence')),
                rationale=self._safe_get_string(row, field_mapping.get('rationale'))
            )
            capabilities.append(capability)

        return capabilities

    def _extract_domains(self, applications: List[Application]) -> List[Domain]:
        """Extract domains from applications."""
        domain_apps = {}
        for app in applications:
            if app.domain not in domain_apps:
                domain_apps[app.domain] = []
            domain_apps[app.domain].append(app)

        return [Domain(name=domain, applications=apps) for domain, apps in domain_apps.items()]

    def _create_app_capability_relationships(self, applications: List[Application], capabilities: List[Capability]) -> List[ApplicationCapability]:
        """Create relationships between applications and capabilities."""
        app_by_name = {app.name: app for app in applications}
        relationships = []

        for capability in capabilities:
            if capability.application_name in app_by_name:
                app = app_by_name[capability.application_name]
                relationships.append(ApplicationCapability(application=app, capability=capability))

        return relationships

    def _safe_get_enum_value(self, row: pd.Series, column: Optional[str], enum_class, default_value):
        """Safely get enum value from row, with fallback to default."""
        if not column or column not in row.index:
            return default_value

        value = row[column]
        if pd.isna(value):
            return default_value

        # Try to match enum value
        try:
            return enum_class(str(value))
        except ValueError:
            # Try case-insensitive matching
            for enum_val in enum_class:
                if enum_val.value.lower() == str(value).lower():
                    return enum_val
            return default_value

    def _safe_get_numeric(self, row: pd.Series, column: Optional[str]) -> Optional[int]:
        """Safely get numeric value from row."""
        if not column or column not in row.index:
            return None
        value = row[column]
        if pd.isna(value):
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def _safe_get_float(self, row: pd.Series, column: Optional[str]) -> Optional[float]:
        """Safely get float value from row."""
        if not column or column not in row.index:
            return None
        value = row[column]
        if pd.isna(value):
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _safe_get_string(self, row: pd.Series, column: Optional[str]) -> Optional[str]:
        """Safely get string value from row."""
        if not column or column not in row.index:
            return None
        value = row[column]
        if pd.isna(value):
            return None
        return str(value)

    def _create_empty_ea_data(self) -> EAData:
        """Create empty EA data structure."""
        schema = EASchema(
            columns=[],
            required_fields=self.REQUIRED_FIELDS,
            optional_fields=self.OPTIONAL_FIELDS,
            field_types={},
            version="empty"
        )
        return EAData(
            applications=[],
            capabilities=[],
            domains=[],
            application_capabilities=[],
            schema=schema,
            metadata={'source_file': str(self.csv_path), 'record_count': 0}
        )


class ArchiMateCSVProvider(EADataProvider):
    """Provider for ArchiMate-format CSV files (elements.csv, relations.csv, properties.csv)"""

    def __init__(self, archi_dir: str = "archi_inputs"):
        self.archi_dir = Path(archi_dir)
        self.elements_file = self.archi_dir / "elements.csv"
        self.relations_file = self.archi_dir / "relations.csv"
        self.properties_file = self.archi_dir / "properties.csv"
        self._schema: Optional[EASchema] = None

    def is_available(self) -> bool:
        """Check if ArchiMate CSV files exist."""
        return (self.archi_dir.exists() and
                self.elements_file.exists() and
                self.relations_file.exists())

    def get_schema(self) -> EASchema:
        """Return ArchiMate schema with logical field names for compatibility."""
        if self._schema is None:
            # Return logical field names that match what the EAData structure provides
            # This enables compatibility with Mermaid diagram generators
            self._schema = EASchema(
                columns=[
                    'app_name',           # From ApplicationComponent.name
                    'capability',         # From Capability.name
                    'domain',             # From ApplicationComponent domain property
                    'strategic_importance',  # From Criticality property mapping
                    'lifecycle_status',   # Always available (default values)
                    'maturity'            # From Maturity property
                ],
                required_fields=['app_name', 'capability', 'domain'],
                optional_fields=['strategic_importance', 'lifecycle_status', 'maturity'],
                field_types={
                    'app_name': str,
                    'capability': str,
                    'domain': str,
                    'strategic_importance': str,
                    'lifecycle_status': str,
                    'maturity': int
                },
                version="archimate_3.0"
            )
        return self._schema

    def get_ea_data(self) -> EAData:
        """Load ArchiMate CSV files and convert to EA data structure."""
        if not self.is_available():
            return self._create_empty_ea_data()

        # Load CSV files
        elements_df = pd.read_csv(self.elements_file)
        relations_df = pd.read_csv(self.relations_file)

        # Load properties if available
        properties_df = None
        if self.properties_file.exists():
            properties_df = pd.read_csv(self.properties_file)

        # Extract applications from ApplicationComponent elements
        applications = self._extract_applications(elements_df, properties_df)

        # Extract capabilities from Capability elements
        capabilities = self._extract_capabilities(elements_df, properties_df)

        # Create app-capability relationships from Serving relationships
        app_capabilities = self._extract_app_capability_relationships(
            relations_df, applications, capabilities
        )

        # Extract domains
        domains = self._extract_domains(applications, capabilities)

        metadata = {
            'source_directory': str(self.archi_dir),
            'element_count': len(elements_df),
            'relationship_count': len(relations_df),
            'application_count': len(applications),
            'capability_count': len(capabilities),
            'domain_count': len(domains),
            'format': 'ArchiMate 3.0 CSV'
        }

        return EAData(
            applications=applications,
            capabilities=capabilities,
            domains=domains,
            application_capabilities=app_capabilities,
            schema=self.get_schema(),
            metadata=metadata
        )

    def _extract_applications(self, elements_df: pd.DataFrame,
                             properties_df: Optional[pd.DataFrame]) -> List[Application]:
        """Extract applications from ApplicationComponent elements."""
        app_elements = elements_df[elements_df['Type'] == 'ApplicationComponent']

        applications = []
        for _, row in app_elements.iterrows():
            elem_id = row['ID']
            name = row['Name']

            # Get properties for this element
            props = self._get_properties(elem_id, properties_df)

            # Map Criticality to strategic importance
            criticality = props.get('Criticality', '')
            strategic_importance = self._map_criticality_to_importance(criticality)

            # Infer domain from capabilities (will be set later) - default to "Operations"
            domain = props.get('Domain', 'Operations')

            application = Application(
                name=name,
                domain=domain,
                lifecycle_status=LifecycleStatus.STRATEGIC,  # Default
                strategic_importance=strategic_importance,
                maturity=self._safe_int(props.get('Maturity')),
                remaining_years=None,
                confidence=None,
                rationale=row.get('Documentation', ''),
                last_updated=None
            )
            applications.append(application)

        return applications

    def _extract_capabilities(self, elements_df: pd.DataFrame,
                             properties_df: Optional[pd.DataFrame]) -> List[Capability]:
        """Extract capabilities from Capability elements."""
        cap_elements = elements_df[elements_df['Type'] == 'Capability']

        capabilities = []
        for _, row in cap_elements.iterrows():
            name = row['Name']

            # Capabilities aren't directly tied to apps yet - will be linked via relationships
            capability = Capability(
                name=name,
                application_name='',  # Will be filled by relationships
                domain='',  # Will be inferred
                maturity=None,
                confidence=None,
                rationale=row.get('Documentation', '')
            )
            capabilities.append(capability)

        return capabilities

    def _extract_app_capability_relationships(self, relations_df: pd.DataFrame,
                                              applications: List[Application],
                                              capabilities: List[Capability]) -> List[ApplicationCapability]:
        """Extract app-capability mappings from Serving relationships."""

        # Create lookup maps
        app_by_id = {}
        cap_by_id = {}

        # We need to map back element IDs - let's reload elements for this
        if not self.elements_file.exists():
            return []  # No elements file yet, return empty relationships

        elements_df = pd.read_csv(self.elements_file)

        for _, row in elements_df.iterrows():
            if row['Type'] == 'ApplicationComponent':
                app = next((a for a in applications if a.name == row['Name']), None)
                if app:
                    app_by_id[row['ID']] = app
            elif row['Type'] == 'Capability':
                cap = next((c for c in capabilities if c.name == row['Name']), None)
                if cap:
                    cap_by_id[row['ID']] = cap

        # Extract Serving relationships (app serves capability)
        serving_rels = relations_df[relations_df['Type'] == 'Serving']

        relationships = []
        for _, row in serving_rels.iterrows():
            source_id = row['Source']
            target_id = row['Target']

            app = app_by_id.get(source_id)
            cap = cap_by_id.get(target_id)

            if app and cap:
                # Update capability's application reference
                cap.application_name = app.name
                cap.domain = app.domain

                relationships.append(ApplicationCapability(
                    application=app,
                    capability=cap
                ))

        return relationships

    def _extract_domains(self, applications: List[Application],
                        capabilities: List[Capability]) -> List[Domain]:
        """Extract domains from applications."""
        domain_apps = {}
        for app in applications:
            if app.domain not in domain_apps:
                domain_apps[app.domain] = []
            domain_apps[app.domain].append(app)

        return [Domain(name=domain, applications=apps)
                for domain, apps in domain_apps.items()]

    def _get_properties(self, element_id: str,
                       properties_df: Optional[pd.DataFrame]) -> Dict[str, str]:
        """Get properties for an element ID."""
        if properties_df is None or properties_df.empty:
            return {}

        elem_props = properties_df[properties_df['ID'] == element_id]
        return {row['Key']: row['Value'] for _, row in elem_props.iterrows()}

    def _map_criticality_to_importance(self, criticality: str) -> StrategicImportance:
        """Map ArchiMate Criticality property to StrategicImportance enum."""
        criticality_lower = criticality.lower()

        if 'critical' in criticality_lower:
            return StrategicImportance.CRITICAL
        elif 'important' in criticality_lower or 'high' in criticality_lower:
            return StrategicImportance.IMPORTANT
        elif 'standard' in criticality_lower or 'medium' in criticality_lower:
            return StrategicImportance.STANDARD
        else:
            return StrategicImportance.STANDARD

    def _safe_int(self, value: Any) -> Optional[int]:
        """Safely convert value to int."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def _create_empty_ea_data(self) -> EAData:
        """Create empty EA data structure."""
        return EAData(
            applications=[],
            capabilities=[],
            domains=[],
            application_capabilities=[],
            schema=self.get_schema(),
            metadata={
                'source_directory': str(self.archi_dir),
                'element_count': 0,
                'format': 'ArchiMate 3.0 CSV'
            }
        )


class DataProviderFactory:
    """Factory for creating appropriate data providers."""

    @staticmethod
    def create_provider(source_path: str) -> EADataProvider:
        """Create the appropriate provider based on file extension or directory."""
        path = Path(source_path)

        if not path.exists():
            raise FileNotFoundError(f"Data source not found: {source_path}")

        # If it's a directory, assume ArchiMate format
        if path.is_dir():
            return ArchiMateCSVProvider(str(path))
        # If it's a CSV file, use legacy matrix provider
        elif path.suffix.lower() == '.csv':
            return CSVMatrixProvider(source_path)
        else:
            raise ValueError(f"Unsupported data source format: {path.suffix}")

    @staticmethod
    def get_default_provider() -> EADataProvider:
        """Get the default EA data provider (ArchiMate format)."""
        # NEW DEFAULT: ArchiMate CSV files in archi_inputs/
        default_path = Path("archi_inputs")
        return ArchiMateCSVProvider(str(default_path))