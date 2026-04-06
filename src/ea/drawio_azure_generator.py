"""
Azure-specific draw.io generator.

This renderer owns `type: azure_diagram` specs and keeps Azure solution
diagramming concerns separate from the existing EA-oriented draw.io generator.
"""

from math import ceil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from .drawio_generator import DrawIOGenerator
from .drawio_export import DrawIOExporter, DrawIOElement, DrawIOContainer, DrawIOEdge
from .azure_shape_catalog import get_azure_shape, get_renderer_shape


class DrawIOAzureGenerator(DrawIOGenerator):
    """Deterministic draw.io generator for Azure solution diagrams."""

    RESOURCE_GROUP_SUBGROUPS = {
        'Ingress': ['api_management'],
        'Compute': ['container_apps_environment', 'container_apps'],
        'Data': ['azure_sql'],
        'Messaging': ['service_bus', 'event_grid'],
    }
    LANE_HEADER = 24
    LANE_TOP_PADDING = 28
    LANE_BOTTOM_PADDING = 18
    ICON_ROW_HEIGHT = 100
    OUTER_CONTAINER_BOTTOM_PADDING = 40

    def generate(self, spec_path: str) -> Dict[str, Any]:
        spec = self._load_spec(spec_path)
        if not spec:
            return {'error': f'Failed to load spec: {spec_path}'}

        view_name = spec.get('view', {}).get('name', 'Azure Diagram')
        elements_config = spec.get('elements', {})
        relationships_config = spec.get('relationships', {})
        annotations_config = spec.get('annotations', [])
        presentation_config = spec.get('presentation', {})
        visual_config = spec.get('visual', {})
        intent_config = spec.get('intent', {})

        selected_element_ids = self.selector.select_elements(elements_config)
        selected_elements = [
            self.selector.element_by_id[eid]
            for eid in selected_element_ids
            if eid in self.selector.element_by_id
        ]

        if not selected_elements:
            return {'error': 'No elements selected by spec'}

        selected_relations = self._filter_relations(selected_elements, relationships_config)
        enriched_elements = self._enrich_elements(selected_elements, presentation_config, visual_config)
        enriched_elements = self._apply_azure_metadata(enriched_elements, elements_config)

        self._write_diagram_elements(enriched_elements)

        drawio_xml = self._generate_azure_drawio(
            view_name=view_name,
            elements=enriched_elements,
            relations=selected_relations,
            spec=spec,
            annotations=annotations_config,
            intent=intent_config,
        )

        output_path = self._write_output(spec_path, drawio_xml, 'drawio')

        return {
            'view_name': view_name,
            'element_count': len(enriched_elements),
            'relationship_count': len(selected_relations),
            'output_files': [str(output_path)],
        }

    def _apply_azure_metadata(self, elements: List[Dict[str, Any]], elements_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Merge Azure-specific metadata from YAML element include rules."""
        metadata_by_name: Dict[str, Dict[str, Any]] = {}
        for rule in elements_config.get('include', []):
            if 'name' in rule:
                metadata_by_name[rule['name'].strip().lower()] = rule

        enriched: List[Dict[str, Any]] = []
        for elem in elements:
            rule = metadata_by_name.get(elem['name'].strip().lower(), {})
            props = dict(elem.get('properties', {}))
            for key in ['azure_service', 'render_as', 'container', 'role']:
                if key in rule:
                    props[key] = rule[key]

            enriched.append({
                **elem,
                'azure_service': rule.get('azure_service'),
                'render_as': rule.get('render_as'),
                'container_name': rule.get('container'),
                'role': rule.get('role', ''),
                'properties': props,
            })

        return enriched

    def _generate_azure_drawio(
        self,
        view_name: str,
        elements: List[Dict[str, Any]],
        relations: List[Dict[str, Any]],
        spec: Dict[str, Any],
        annotations: Optional[List[Dict[str, Any]]] = None,
        intent: Optional[Dict[str, Any]] = None,
    ) -> str:
        exporter = DrawIOExporter()
        container_defs = self._build_azure_containers(spec, elements)
        drawio_containers = [c['container'] for c in container_defs.values()]
        drawio_elements, elem_positions, element_container_map = self._build_azure_elements(elements, container_defs)

        elements_by_id = {e['id']: e for e in elements}
        drawio_edges: List[DrawIOEdge] = []
        seen_edges = set()
        for rel in relations:
            source_id = rel.get('source')
            target_id = rel.get('target')
            if not source_id or not target_id:
                continue
            display_source_id, display_target_id = self._resolve_edge_endpoints(
                source_id=source_id,
                target_id=target_id,
                element_container_map=element_container_map,
                container_defs=container_defs,
            )
            edge_key = (display_source_id, display_target_id, rel.get('type', ''), rel.get('label', ''))
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)
            waypoints = self._route_edge_via_containers(
                source_id=source_id,
                target_id=target_id,
                element_positions=elem_positions,
                element_container_map=element_container_map,
                container_defs=container_defs,
            )
            drawio_edges.append(DrawIOEdge(
                from_id=display_source_id,
                to_id=display_target_id,
                label=self._edge_label(rel, elements_by_id),
                edge_type=rel.get('type', 'Flow'),
                waypoints=waypoints,
            ))

        xml_output = exporter.export(
            elements=drawio_elements,
            edges=drawio_edges,
            containers=drawio_containers,
            view_name=view_name,
        )

        if annotations:
            xml_output = self._embed_annotations_in_drawio(xml_output, annotations, elem_positions)

        bottom_y = max(
            [pos['y'] + pos.get('height', 80) for pos in elem_positions.values()] + [980]
        )
        narrative = self._generate_narrative(view_name, elements, [], relations, intent)
        return self._embed_narrative_in_drawio(xml_output, narrative, bottom_y)

    def _build_azure_containers(self, spec: Dict[str, Any], elements: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Create deterministic Azure container layout."""
        layout = spec.get('layout', {})
        pattern = layout.get('pattern', 'solution_runtime')
        if pattern not in ['solution_runtime', 'current_vs_target']:
            pattern = 'solution_runtime'

        defs: Dict[str, Dict[str, Any]] = {}
        lane_counts = self._count_elements_by_default_container(elements)

        subgroup_height = self._service_lane_height(max(
            lane_counts.get('Ingress', 0),
            lane_counts.get('Messaging', 0),
            lane_counts.get('Compute', 0),
            lane_counts.get('Data', 0),
        ), columns=2)
        delivery_height = self._service_lane_height(lane_counts.get('Delivery', 0), columns=3)
        observability_height = self._service_lane_height(lane_counts.get('Observability', 0), columns=3)
        network_height = self._service_lane_height(max(1, lane_counts.get('Network Boundary', 0)), columns=3)
        resource_group_height = 255 + subgroup_height + 35

        if pattern == 'solution_runtime':
            defs = {
                'Users and Upstream Systems': self._container_record('cnt-ext', 'Users and Upstream Systems', 40, 170, 230, 560, 'external'),
                'Azure Tenant': self._container_record('cnt-tenant', 'Azure Tenant', 300, 40, 1540, 900, 'tenant'),
                'Shared Platform Services': self._container_record('cnt-platform', 'Shared Platform Services', 30, 80, 300, 260, 'platform', parent='cnt-tenant'),
                'PSS 2.0 Subscription': self._container_record('cnt-sub', 'PSS 2.0 Subscription', 360, 70, 1130, 690, 'subscription', parent='cnt-tenant'),
                'PSS 2.0 Resource Group': self._container_record('cnt-rg', 'PSS 2.0 Resource Group', 30, 90, 920, resource_group_height, 'resource_group', parent='cnt-sub'),
                'Network Boundary': self._container_record('cnt-net', 'Network Boundary', 25, 65, 770, network_height, 'network', parent='cnt-rg'),
                'Ingress': self._container_record('cnt-rg-ingress', 'Ingress', 25, 255, 180, subgroup_height, 'subgroup', parent='cnt-rg'),
                'Messaging': self._container_record('cnt-rg-msg', 'Messaging', 235, 255, 180, subgroup_height, 'subgroup', parent='cnt-rg'),
                'Compute': self._container_record('cnt-rg-compute', 'Compute', 440, 255, 260, subgroup_height, 'subgroup', parent='cnt-rg'),
                'Data': self._container_record('cnt-rg-data', 'Data', 725, 255, 160, subgroup_height, 'subgroup', parent='cnt-rg'),
                'Observability': self._container_record('cnt-obs', 'Observability', 360, 790, 500, observability_height, 'observability', parent='cnt-tenant'),
                'Delivery': self._container_record('cnt-dev', 'Delivery', 890, 790, 600, delivery_height, 'devops', parent='cnt-tenant'),
            }
        else:
            defs = {
                'Legacy Hosting Pattern': self._container_record('cnt-legacy', 'Legacy Hosting Pattern', 40, 150, 250, 460, 'current_state'),
                'Users and Upstream Systems': self._container_record('cnt-ext', 'Users and Upstream Systems', 320, 150, 230, 460, 'external'),
                'Azure Tenant': self._container_record('cnt-tenant', 'Azure Tenant', 580, 40, 1260, 900, 'tenant'),
                'Shared Platform Services': self._container_record('cnt-platform', 'Shared Platform Services', 30, 80, 300, 260, 'platform', parent='cnt-tenant'),
                'PSS 2.0 Subscription': self._container_record('cnt-sub', 'PSS 2.0 Subscription', 360, 70, 860, 690, 'subscription', parent='cnt-tenant'),
                'PSS 2.0 Resource Group': self._container_record('cnt-rg', 'PSS 2.0 Resource Group', 30, 90, 760, 420, 'resource_group', parent='cnt-sub'),
                'Network Boundary': self._container_record('cnt-net', 'Network Boundary', 20, 60, 720, 150, 'network', parent='cnt-rg'),
                'Observability': self._container_record('cnt-obs', 'Observability', 360, 790, 360, 110, 'observability', parent='cnt-tenant'),
                'Delivery': self._container_record('cnt-dev', 'Delivery', 760, 790, 460, 110, 'devops', parent='cnt-tenant'),
            }

        for declared in spec.get('containers', []):
            name = declared.get('name')
            if name not in defs:
                next_x = 300 + (len(defs) * 40)
                defs[name] = self._container_record(
                    f"cnt-extra-{len(defs)}",
                    name,
                    next_x,
                    120,
                    280,
                    180,
                    declared.get('kind', 'custom'),
                )

        self._fit_parent_container_heights(defs)
        return defs

    def _container_record(
        self,
        container_id: str,
        label: str,
        x: int,
        y: int,
        width: int,
        height: int,
        kind: str,
        parent: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            'container': DrawIOContainer(
                id=container_id,
                label=label,
                x=x,
                y=y,
                width=width,
                height=height,
                parent_id=parent,
                style=self._container_style(kind),
            ),
            'kind': kind,
            'x': x,
            'y': y,
            'width': width,
            'height': height,
            'parent': parent,
        }

    def _container_style(self, kind: str) -> str:
        styles = {
            'tenant': "swimlane;startSize=36;fillColor=#F8FBFF;strokeColor=#1565C0;fontStyle=1;strokeWidth=2;",
            'subscription': "swimlane;startSize=30;fillColor=#FDFEFF;strokeColor=#64B5F6;fontStyle=1;",
            'resource_group': "swimlane;startSize=28;fillColor=#F9FCFF;strokeColor=#90CAF9;fontStyle=1;",
            'platform': "swimlane;startSize=28;fillColor=#F6FBFF;strokeColor=#42A5F5;fontStyle=1;",
            'observability': "swimlane;startSize=28;fillColor=#FFF8E1;strokeColor=#FFB300;fontStyle=1;",
            'devops': "swimlane;startSize=28;fillColor=#F3E5F5;strokeColor=#8E24AA;fontStyle=1;",
            'network': "swimlane;startSize=24;fillColor=#F5F5F5;strokeColor=#78909C;dashed=1;fontStyle=1;",
            'subgroup': "swimlane;startSize=24;fillColor=#EAF4FF;strokeColor=#90CAF9;fontStyle=1;",
            'external': "swimlane;startSize=30;fillColor=#FAFAFA;strokeColor=#9E9E9E;fontStyle=1;",
            'current_state': "swimlane;startSize=30;fillColor=#FFF3E0;strokeColor=#FB8C00;fontStyle=1;",
            'custom': "swimlane;startSize=28;fillColor=#FAFAFA;strokeColor=#BDBDBD;fontStyle=1;",
        }
        return styles.get(kind, styles['custom'])

    def _service_lane_height(self, element_count: int, columns: int) -> int:
        """Compute container height from the number of horizontal icon rows."""
        rows = max(1, ceil(max(element_count, 1) / columns))
        return self.LANE_HEADER + self.LANE_TOP_PADDING + (rows * self.ICON_ROW_HEIGHT) + self.LANE_BOTTOM_PADDING

    def _fit_parent_container_heights(self, container_defs: Dict[str, Dict[str, Any]]) -> None:
        """Expand parent containers so they fully encompass their children plus bottom padding."""
        for record in container_defs.values():
            parent_id = record.get('parent')
            if not parent_id:
                continue

            parent_record = next(
                (item for item in container_defs.values() if item['container'].id == parent_id),
                None,
            )
            if not parent_record:
                continue

            required_height = int(record['y'] + record['height'] + self.OUTER_CONTAINER_BOTTOM_PADDING)
            if required_height > parent_record['height']:
                parent_record['height'] = required_height
                parent_record['container'].height = required_height

    def _count_elements_by_default_container(self, elements: List[Dict[str, Any]]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for elem in elements:
            container_name = self._resolve_default_container(elem)
            counts[container_name] = counts.get(container_name, 0) + 1
        return counts

    def _build_azure_elements(
        self,
        elements: List[Dict[str, Any]],
        container_defs: Dict[str, Dict[str, Any]],
    ) -> tuple[List[DrawIOElement], Dict[str, Dict[str, int]], Dict[str, str]]:
        drawio_elements: List[DrawIOElement] = []
        elem_positions: Dict[str, Dict[str, int]] = {}
        element_container_map: Dict[str, str] = {}

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for elem in elements:
            container_name = self._resolve_default_container(elem)
            grouped.setdefault(container_name, []).append(elem)

        for container_name, elems in grouped.items():
            container_def = container_defs.get(container_name)
            if not container_def:
                continue

            positions = self._container_slots(container_name, container_def, elems)
            for elem in elems:
                pos = positions.get(elem['id'], {'x': 40, 'y': 60})
                shape = get_azure_shape(elem.get('azure_service') or '')
                if not shape:
                    shape = get_renderer_shape(elem.get('render_as') or 'external_system')
                width = shape.get('width', elem.get('width', 140))
                height = shape.get('height', elem.get('height', 70))
                display_name = elem.get('display_name') or elem['name']

                drawio_elements.append(DrawIOElement(
                    id=elem['id'],
                    name=display_name,
                    x=pos['x'],
                    y=pos['y'],
                    width=width,
                    height=height,
                    elem_type=elem['type'],
                    parent_id=container_def['container'].id,
                    color=elem.get('color', '#B5D4E8'),
                    emphasis=elem.get('emphasis', 'normal'),
                    style=shape.get('style'),
                ))

                abs_pos = self._absolute_position(container_def, container_defs, pos['x'], pos['y'], width, height)
                abs_pos['id'] = elem['id']
                elem_positions[elem['name'].lower()] = abs_pos
                elem_positions[display_name.lower()] = abs_pos
                elem_positions[elem['id']] = abs_pos
                element_container_map[elem['id']] = container_name

        return drawio_elements, elem_positions, element_container_map

    def _container_slots(
        self,
        container_name: str,
        container_def: Dict[str, Any],
        elems: List[Dict[str, Any]],
    ) -> Dict[str, Dict[str, int]]:
        kind = container_def['kind']

        if kind == 'external':
            return self._vertical_slots(elems, start_x=40, start_y=60, gap_y=110)
        if kind == 'platform':
            return self._grid_slots(elems, start_x=40, start_y=60, gap_x=130, gap_y=120, columns=2)
        if kind == 'observability':
            return self._grid_slots(elems, start_x=50, start_y=56, gap_x=180, gap_y=100, columns=3)
        if kind == 'devops':
            return self._grid_slots(elems, start_x=50, start_y=56, gap_x=210, gap_y=100, columns=3)
        if kind == 'network':
            return self._grid_slots(elems, start_x=60, start_y=48, gap_x=180, gap_y=90, columns=3)
        if kind == 'subgroup':
            return self._grid_slots(elems, start_x=45, start_y=52, gap_x=120, gap_y=100, columns=2)
        if kind == 'current_state':
            return self._vertical_slots(elems, start_x=55, start_y=80, gap_y=120)

        if kind == 'resource_group':
            ordered = sorted(elems, key=self._resource_group_sort_key)
            slots = {}
            slot_map = [
                (40, 235),
                (260, 60),
                (270, 220),
                (500, 225),
                (265, 325),
                (500, 60),
            ]
            for idx, elem in enumerate(ordered):
                x, y = slot_map[idx] if idx < len(slot_map) else (40 + (idx % 3) * 220, 235 + (idx // 3) * 110)
                slots[elem['id']] = {'x': x, 'y': y}
            return slots

        return self._grid_slots(elems, start_x=40, start_y=60, gap_x=180, gap_y=100, columns=3)

    def _resource_group_sort_key(self, elem: Dict[str, Any]) -> int:
        order = {
            'api_management': 1,
            'container_apps_environment': 2,
            'container_apps': 3,
            'azure_sql': 4,
            'service_bus': 5,
        }
        return order.get(elem.get('azure_service') or '', 99)

    def _vertical_slots(self, elems: List[Dict[str, Any]], start_x: int, start_y: int, gap_y: int) -> Dict[str, Dict[str, int]]:
        return {
            elem['id']: {'x': start_x, 'y': start_y + (idx * gap_y)}
            for idx, elem in enumerate(elems)
        }

    def _grid_slots(
        self,
        elems: List[Dict[str, Any]],
        start_x: int,
        start_y: int,
        gap_x: int,
        gap_y: int,
        columns: int,
    ) -> Dict[str, Dict[str, int]]:
        slots: Dict[str, Dict[str, int]] = {}
        for idx, elem in enumerate(elems):
            row = idx // columns
            col = idx % columns
            slots[elem['id']] = {'x': start_x + (col * gap_x), 'y': start_y + (row * gap_y)}
        return slots

    def _absolute_position(
        self,
        container_def: Dict[str, Any],
        container_defs: Dict[str, Dict[str, Any]],
        rel_x: int,
        rel_y: int,
        width: int,
        height: int,
    ) -> Dict[str, int]:
        origin_x, origin_y = self._container_absolute_origin(container_def, container_defs)
        abs_x = rel_x + origin_x
        abs_y = rel_y + origin_y
        return {
            'x': abs_x,
            'y': abs_y,
            'width': width,
            'height': height,
        }

    def _container_absolute_origin(
        self,
        container_def: Dict[str, Any],
        container_defs: Dict[str, Dict[str, Any]],
    ) -> Tuple[int, int]:
        """Resolve absolute x/y by walking parent container ids."""
        x = int(container_def['x'])
        y = int(container_def['y'])
        parent_id = container_def.get('parent')

        while parent_id:
            parent_def = next(
                (item for item in container_defs.values() if item['container'].id == parent_id),
                None,
            )
            if not parent_def:
                break
            x += int(parent_def['x'])
            y += int(parent_def['y'])
            parent_id = parent_def.get('parent')

        return x, y

    def _resolve_default_container(self, elem: Dict[str, Any]) -> str:
        explicit = elem.get('container_name')
        if explicit and explicit != 'PSS 2.0 Resource Group':
            return explicit

        azure_service = elem.get('azure_service') or ''
        for subgroup_name, services in self.RESOURCE_GROUP_SUBGROUPS.items():
            if azure_service in services:
                return subgroup_name

        return explicit or 'PSS 2.0 Resource Group'

    def _resolve_edge_endpoints(
        self,
        source_id: str,
        target_id: str,
        element_container_map: Dict[str, str],
        container_defs: Dict[str, Dict[str, Any]],
    ) -> Tuple[str, str]:
        """
        In Azure mode, cross-container edges should connect container-to-container,
        not icon-to-icon. Same-container edges remain icon-to-icon.
        """
        source_container = element_container_map.get(source_id)
        target_container = element_container_map.get(target_id)

        if not source_container or not target_container or source_container == target_container:
            return source_id, target_id

        source_def = container_defs.get(source_container)
        target_def = container_defs.get(target_container)
        if not source_def or not target_def:
            return source_id, target_id

        return source_def['container'].id, target_def['container'].id

    def _route_edge_via_containers(
        self,
        source_id: str,
        target_id: str,
        element_positions: Dict[str, Dict[str, int]],
        element_container_map: Dict[str, str],
        container_defs: Dict[str, Dict[str, Any]],
    ) -> Optional[List[Tuple[int, int]]]:
        """Route edges by subgroup/container lanes instead of direct icon-to-icon lines."""
        source_container = element_container_map.get(source_id)
        target_container = element_container_map.get(target_id)
        if not source_container or not target_container or source_container == target_container:
            return None

        source_pos = element_positions.get(source_id)
        target_pos = element_positions.get(target_id)
        source_def = container_defs.get(source_container)
        target_def = container_defs.get(target_container)
        if not source_pos or not target_pos or not source_def or not target_def:
            return None

        source_origin_x, source_origin_y = self._container_absolute_origin(source_def, container_defs)
        target_origin_x, target_origin_y = self._container_absolute_origin(target_def, container_defs)

        source_left = int(source_origin_x)
        source_right = int(source_origin_x + source_def['width'])
        source_top = int(source_origin_y)
        source_bottom = int(source_origin_y + source_def['height'])
        source_mid_x = int(source_left + (source_def['width'] / 2))
        source_mid_y = int(source_top + (source_def['height'] / 2))

        target_left = int(target_origin_x)
        target_right = int(target_origin_x + target_def['width'])
        target_top = int(target_origin_y)
        target_bottom = int(target_origin_y + target_def['height'])
        target_mid_x = int(target_left + (target_def['width'] / 2))
        target_mid_y = int(target_top + (target_def['height'] / 2))

        lane_gap = 12

        # Standard left-right sequencing between container lanes.
        if source_right <= target_left:
            return [
                (source_right + lane_gap, source_mid_y),
                (target_left - lane_gap, target_mid_y),
            ]

        if target_right <= source_left:
            return [
                (source_left - lane_gap, source_mid_y),
                (target_right + lane_gap, target_mid_y),
            ]

        # Top-down sequencing when horizontal overlap exists.
        if source_bottom <= target_top:
            return [
                (source_mid_x, source_bottom + lane_gap),
                (target_mid_x, target_top - lane_gap),
            ]

        if target_bottom <= source_top:
            return [
                (source_mid_x, source_top - lane_gap),
                (target_mid_x, target_bottom + lane_gap),
            ]

        # Fallback: route through a neutral midpoint between containers.
        mid_x = int((source_mid_x + target_mid_x) / 2)
        return [
            (mid_x, source_mid_y),
            (mid_x, target_mid_y),
        ]


def generate_diagram(spec_path: str) -> Dict[str, Any]:
    generator = DrawIOAzureGenerator()
    return generator.generate(spec_path)
