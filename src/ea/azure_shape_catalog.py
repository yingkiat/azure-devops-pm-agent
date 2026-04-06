"""
Azure draw.io shape catalog.

Maps semantic Azure service keys to draw.io style strings and default sizing.
The styles use draw.io's built-in image library paths where available and keep
the YAML schema free of raw draw.io style details.

Design boundary:
- drawio generation stays aligned to draw.io's native Azure library references
- portal publishing for `azure_diagram` is PNG-first and does not reinterpret
  these icon paths
- this keeps Azure diagram generation and portal delivery loosely coupled
"""

from typing import Dict, Any


def _azure_image_style(image_path: str) -> str:
    return (
        "shape=image;html=1;aspect=fixed;imageAspect=0;"
        "verticalLabelPosition=bottom;verticalAlign=top;align=center;"
        "fontSize=11;fontFamily=Verdana;spacingTop=6;strokeColor=none;"
        f"image={image_path};"
    )


AZURE_SHAPES: Dict[str, Dict[str, Any]] = {
    "entra_id": {
        "style": _azure_image_style("img/lib/azure2/identity/Azure_Active_Directory.svg"),
        "width": 82,
        "height": 82,
    },
    "key_vault": {
        "style": _azure_image_style("img/lib/azure2/security/Key_Vaults.svg"),
        "width": 78,
        "height": 78,
    },
    "container_registry": {
        "style": _azure_image_style("img/lib/azure2/containers/Container_Registries.svg"),
        "width": 78,
        "height": 78,
    },
    "virtual_network": {
        "style": _azure_image_style("img/lib/azure2/networking/Virtual_Networks.svg"),
        "width": 84,
        "height": 84,
    },
    "private_endpoint": {
        "style": _azure_image_style("img/lib/azure2/networking/Private_Endpoint.svg"),
        "width": 78,
        "height": 78,
    },
    "api_management": {
        "style": _azure_image_style("img/lib/azure2/app_services/API_Management_Services.svg"),
        "width": 84,
        "height": 84,
    },
    "container_apps_environment": {
        "style": _azure_image_style("img/lib/azure2/other/Container_App_Environments.svg"),
        "width": 84,
        "height": 84,
    },
    "container_apps": {
        "style": _azure_image_style("img/lib/azure2/containers/Container_Instances.svg"),
        "width": 90,
        "height": 90,
    },
    "azure_sql": {
        "style": _azure_image_style("img/lib/azure2/databases/Azure_SQL.svg"),
        "width": 82,
        "height": 82,
    },
    "service_bus": {
        "style": _azure_image_style("img/lib/azure2/integration/Service_Bus.svg"),
        "width": 82,
        "height": 82,
    },
    "application_insights": {
        "style": _azure_image_style("img/lib/azure2/management_governance/Application_Insights.svg"),
        "width": 78,
        "height": 78,
    },
    "log_analytics": {
        "style": _azure_image_style("img/lib/azure2/analytics/Log_Analytics_Workspaces.svg"),
        "width": 82,
        "height": 82,
    },
}


GENERIC_AZURE_RENDERERS: Dict[str, Dict[str, Any]] = {
    "user": {
        "style": (
            "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;"
            "html=1;fontSize=11;fontFamily=Verdana;"
        ),
        "width": 46,
        "height": 72,
    },
    "external_system": {
        "style": (
            "rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#9E9E9E;"
            "fontSize=11;fontFamily=Verdana;arcSize=10;"
        ),
        "width": 150,
        "height": 64,
    },
    "devops_pipeline": {
        "style": (
            "shape=hexagon;perimeter=hexagonPerimeter2;whiteSpace=wrap;html=1;"
            "fillColor=#E3F2FD;strokeColor=#1565C0;fontSize=11;fontFamily=Verdana;"
        ),
        "width": 158,
        "height": 72,
    },
    "legacy_server": {
        "style": (
            "shape=cube;whiteSpace=wrap;html=1;boundedLbl=1;fillColor=#FBE9E7;"
            "strokeColor=#8D6E63;fontSize=11;fontFamily=Verdana;opacity=70;"
        ),
        "width": 132,
        "height": 82,
    },
    "legacy_database_server": {
        "style": (
            "shape=cylinder;whiteSpace=wrap;html=1;boundedLbl=1;fillColor=#F3E5F5;"
            "strokeColor=#8E24AA;fontSize=11;fontFamily=Verdana;opacity=70;"
        ),
        "width": 124,
        "height": 82,
    },
}


def get_azure_shape(service_key: str) -> Dict[str, Any]:
    return AZURE_SHAPES.get(service_key, {})


def get_renderer_shape(renderer_key: str) -> Dict[str, Any]:
    return GENERIC_AZURE_RENDERERS.get(renderer_key, {})
