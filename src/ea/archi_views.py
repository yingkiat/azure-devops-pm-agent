"""
Archi View Generation

Creates ArchiMate views from EA discovery data.
Supports 7 view types: Overview, Business Process, Application, Data, Infrastructure, Security, Integration.
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import hashlib


@dataclass
class ViewDefinition:
    """Definition of an Archi view"""
    id: str
    type: str
    name: str
    documentation: str
    elements: List[str]  # Element IDs to include
    relations: List[str]  # Relationship IDs to include
    grouping: Dict[str, Any] = None  # MVP6: Grouping configuration
    layout: Dict[str, Any] = None    # MVP6: Layout configuration


class ViewGenerator:
    """Generates ArchiMate views from EA discovery data"""

    VIEW_TYPES = {
        'overview': 'Application Landscape',
        'business': 'Business Process Flow',
        'application': 'Application Cooperation',
        'data': 'Information Structure',
        'infrastructure': 'Technology Architecture',
        'security': 'Security Architecture',
        'integration': 'Integration View'
    }

    def __init__(self):
        pass

    def generate_all_views(self, ea_analysis: Dict[str, Any],
                          elements: List[Dict[str, Any]],
                          relations: List[Dict[str, Any]]) -> List[ViewDefinition]:
        """Generate all relevant views based on EA analysis content"""

        views = []

        # Always generate overview
        views.append(self.generate_overview_view(ea_analysis, elements, relations))

        # Generate layer-specific views if content exists
        if self._has_business_content(ea_analysis):
            views.append(self.generate_business_view(ea_analysis, elements, relations))

        if self._has_application_content(ea_analysis):
            views.append(self.generate_application_view(ea_analysis, elements, relations))

        if self._has_data_content(ea_analysis):
            views.append(self.generate_data_view(ea_analysis, elements, relations))

        if self._has_infrastructure_content(ea_analysis):
            views.append(self.generate_infrastructure_view(ea_analysis, elements, relations))

        if self._has_security_content(ea_analysis):
            views.append(self.generate_security_view(ea_analysis, elements, relations))

        # Generate integration view if there are multiple applications
        if len(self._filter_by_type(elements, 'Application')) > 1:
            views.append(self.generate_integration_view(ea_analysis, elements, relations))

        return views

    def generate_overview_view(self, ea_analysis: Dict[str, Any],
                               elements: List[Dict[str, Any]],
                               relations: List[Dict[str, Any]]) -> ViewDefinition:
        """Generate high-level overview showing key elements from all layers"""

        # Select representative elements from each layer
        selected_elements = []

        # Business: processes and key capabilities
        business_elements = self._filter_by_layer(elements, 'business')[:3]
        selected_elements.extend(business_elements)

        # Application: main applications
        app_elements = self._filter_by_layer(elements, 'application')[:5]
        selected_elements.extend(app_elements)

        # Data: key data entities
        data_elements = self._filter_by_layer(elements, 'data')[:3]
        selected_elements.extend(data_elements)

        # Infrastructure: critical infrastructure
        infra_elements = self._filter_by_layer(elements, 'infrastructure')[:2]
        selected_elements.extend(infra_elements)

        element_ids = [e['id'] for e in selected_elements]

        # Include relationships between selected elements
        relevant_relations = [
            r for r in relations
            if r.get('source_id') in element_ids and r.get('target_id') in element_ids
        ]

        return ViewDefinition(
            id=self._generate_id('view-overview'),
            type='archimate-diagram-model',
            name='Application Landscape Overview',
            documentation='High-level overview of the enterprise architecture showing key elements across all layers',
            elements=element_ids,
            relations=[r['id'] for r in relevant_relations]
        )

    def generate_business_view(self, ea_analysis: Dict[str, Any],
                               elements: List[Dict[str, Any]],
                               relations: List[Dict[str, Any]]) -> ViewDefinition:
        """Generate business process view"""

        # Select business layer elements
        business_elements = self._filter_by_layer(elements, 'business')

        # Include applications that serve business processes
        app_elements = self._filter_by_type(elements, 'Application')

        selected_elements = business_elements + app_elements
        element_ids = [e['id'] for e in selected_elements]

        # Include serving and realization relationships
        relevant_relations = [
            r for r in relations
            if r.get('source_id') in element_ids and r.get('target_id') in element_ids
            and r.get('relationship_type') in ['Serving', 'Realization', 'Triggering']
        ]

        return ViewDefinition(
            id=self._generate_id('view-business'),
            type='archimate-diagram-model',
            name='Business Process Flow',
            documentation='Business processes, capabilities, and supporting applications',
            elements=element_ids,
            relations=[r['id'] for r in relevant_relations]
        )

    def generate_application_view(self, ea_analysis: Dict[str, Any],
                                  elements: List[Dict[str, Any]],
                                  relations: List[Dict[str, Any]]) -> ViewDefinition:
        """Generate application cooperation view"""

        # Select application layer elements
        app_elements = self._filter_by_layer(elements, 'application')

        element_ids = [e['id'] for e in app_elements]

        # Include all relationships between applications
        relevant_relations = [
            r for r in relations
            if r.get('source_id') in element_ids and r.get('target_id') in element_ids
        ]

        return ViewDefinition(
            id=self._generate_id('view-application'),
            type='archimate-diagram-model',
            name='Application Cooperation',
            documentation='Application components, services, and their interactions',
            elements=element_ids,
            relations=[r['id'] for r in relevant_relations]
        )

    def generate_data_view(self, ea_analysis: Dict[str, Any],
                           elements: List[Dict[str, Any]],
                           relations: List[Dict[str, Any]]) -> ViewDefinition:
        """Generate data architecture view"""

        # Select data layer elements
        data_elements = self._filter_by_layer(elements, 'data')

        # Include applications that access data
        app_elements = self._filter_by_type(elements, 'Application')

        selected_elements = data_elements + app_elements
        element_ids = [e['id'] for e in selected_elements]

        # Include access and flow relationships
        relevant_relations = [
            r for r in relations
            if r.get('source_id') in element_ids and r.get('target_id') in element_ids
            and r.get('relationship_type') in ['Access', 'Flow', 'Association']
        ]

        return ViewDefinition(
            id=self._generate_id('view-data'),
            type='archimate-diagram-model',
            name='Information Structure',
            documentation='Data entities, datastores, and data flows',
            elements=element_ids,
            relations=[r['id'] for r in relevant_relations]
        )

    def generate_infrastructure_view(self, ea_analysis: Dict[str, Any],
                                     elements: List[Dict[str, Any]],
                                     relations: List[Dict[str, Any]]) -> ViewDefinition:
        """Generate infrastructure view"""

        # Select infrastructure layer elements
        infra_elements = self._filter_by_layer(elements, 'infrastructure')

        # Include applications deployed on infrastructure
        app_elements = self._filter_by_type(elements, 'Application')

        selected_elements = infra_elements + app_elements
        element_ids = [e['id'] for e in selected_elements]

        # Include composition and assignment relationships
        relevant_relations = [
            r for r in relations
            if r.get('source_id') in element_ids and r.get('target_id') in element_ids
            and r.get('relationship_type') in ['Composition', 'Assignment', 'Association']
        ]

        return ViewDefinition(
            id=self._generate_id('view-infrastructure'),
            type='archimate-diagram-model',
            name='Technology Architecture',
            documentation='Infrastructure components, servers, networks, and deployments',
            elements=element_ids,
            relations=[r['id'] for r in relevant_relations]
        )

    def generate_security_view(self, ea_analysis: Dict[str, Any],
                               elements: List[Dict[str, Any]],
                               relations: List[Dict[str, Any]]) -> ViewDefinition:
        """Generate security architecture view"""

        # Select security elements
        security_elements = self._filter_by_layer(elements, 'security')

        # Include applications and data protected by security controls
        app_elements = self._filter_by_type(elements, 'Application')
        data_elements = self._filter_by_type(elements, 'Data-Object')

        selected_elements = security_elements + app_elements + data_elements
        element_ids = [e['id'] for e in selected_elements]

        # Include all relationships involving security elements
        relevant_relations = [
            r for r in relations
            if (r.get('source_id') in element_ids and r.get('target_id') in element_ids) and
            (r.get('source_id') in [s['id'] for s in security_elements] or
             r.get('target_id') in [s['id'] for s in security_elements])
        ]

        return ViewDefinition(
            id=self._generate_id('view-security'),
            type='archimate-diagram-model',
            name='Security Architecture',
            documentation='Security controls, threats, and protected assets',
            elements=element_ids,
            relations=[r['id'] for r in relevant_relations]
        )

    def generate_integration_view(self, ea_analysis: Dict[str, Any],
                                  elements: List[Dict[str, Any]],
                                  relations: List[Dict[str, Any]]) -> ViewDefinition:
        """Generate integration view showing application interfaces"""

        # Select applications and interfaces
        app_elements = self._filter_by_type(elements, 'Application')
        interface_elements = self._filter_by_type(elements, 'Interface')
        service_elements = self._filter_by_type(elements, 'Service')

        selected_elements = app_elements + interface_elements + service_elements
        element_ids = [e['id'] for e in selected_elements]

        # Include flow and serving relationships
        relevant_relations = [
            r for r in relations
            if r.get('source_id') in element_ids and r.get('target_id') in element_ids
            and r.get('relationship_type') in ['Flow', 'Serving', 'Access']
        ]

        return ViewDefinition(
            id=self._generate_id('view-integration'),
            type='archimate-diagram-model',
            name='Integration View',
            documentation='Application interfaces, APIs, and data integration flows',
            elements=element_ids,
            relations=[r['id'] for r in relevant_relations]
        )

    def _filter_by_layer(self, elements: List[Dict[str, Any]], layer: str) -> List[Dict[str, Any]]:
        """Filter elements by EA layer"""
        return [e for e in elements if e.get('layer', '').lower() == layer.lower()]

    def _filter_by_type(self, elements: List[Dict[str, Any]], type_name: str) -> List[Dict[str, Any]]:
        """Filter elements by ArchiMate type"""
        return [e for e in elements if type_name.lower() in e.get('type', '').lower()]

    def _has_business_content(self, ea_analysis: Dict[str, Any]) -> bool:
        """Check if EA analysis has business layer content"""
        business = ea_analysis.get('business', {})
        return bool(business.get('processes') or business.get('capabilities'))

    def _has_application_content(self, ea_analysis: Dict[str, Any]) -> bool:
        """Check if EA analysis has application layer content"""
        application = ea_analysis.get('application', {})
        return bool(application.get('applications'))

    def _has_data_content(self, ea_analysis: Dict[str, Any]) -> bool:
        """Check if EA analysis has data layer content"""
        data = ea_analysis.get('data', {})
        return bool(data.get('entities') or data.get('datastores'))

    def _has_infrastructure_content(self, ea_analysis: Dict[str, Any]) -> bool:
        """Check if EA analysis has infrastructure layer content"""
        infrastructure = ea_analysis.get('infrastructure', {})
        return bool(infrastructure.get('components'))

    def _has_security_content(self, ea_analysis: Dict[str, Any]) -> bool:
        """Check if EA analysis has security layer content"""
        security = ea_analysis.get('security', {})
        return bool(security.get('controls') or security.get('threats'))

    def _generate_id(self, prefix: str) -> str:
        """Generate unique ID for view"""
        hash_input = f"{prefix}-{id(self)}"
        return f"{prefix}-{hashlib.md5(hash_input.encode()).hexdigest()[:8]}"
