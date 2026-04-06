# Azure Diagram Mode Planning

## Purpose

Define a new diagram mode for Azure solution architecture diagrams that:

- uses draw.io's existing Azure iconography instead of generic EA boxes
- stays YAML-driven and source-controlled like the rest of the EA workflow
- does not overload or destabilize the existing draw.io generators used for EA and landscape views

This is intended to support repeated use across modernization initiatives in an Azure-first organization.

## Problem Statement

The current diagram stack works well for:

- ArchiMate-grounded enterprise views
- application landscapes
- roadmaps
- relationship-driven EA diagrams

It is weaker for cloud solution communication. Once the audience expects a design showing:

- Azure Container Apps
- API Management
- Key Vault
- Service Bus
- Azure SQL
- App Insights
- Log Analytics
- Private Endpoints
- Entra ID

generic rounded rectangles stop being sufficient.

The repo already has enough diagram infrastructure to support a new solution-design mode, but the current `drawio_generator.py` is already carrying mixed responsibilities. Extending that file with Azure-specific rendering, icon mapping, boundary layout, and cloud conventions would increase maintenance risk.

## Design Position

We should add a new diagram mode:

- `type: "azure_diagram"`

And route that mode to a dedicated generator:

- `src/ea/drawio_azure_generator.py`

This is not a rewrite of the existing draw.io pipeline. It is a new specialized generator for a materially different rendering problem.

## Architectural Principles

### 1. One repo, two diagram languages

This repository should support two distinct but related architecture languages:

- **EA language**
  - application landscapes
  - capability maps
  - roadmaps
  - transition and dependency views
  - ArchiMate-grounded semantics

- **Cloud solution language**
  - Azure runtime architecture
  - Azure integration architecture
  - security and networking boundaries
  - delivery and observability topology
  - Azure-native iconography

Both should remain YAML-driven and regenerable from source.

### 2. Preserve existing generator behavior

Per the maintenance stance in [DRAWIO_GENERATOR_MAINTENANCE.md](C:/Users/yingkiat.gan/Documents/Work/azure-devops-pm-agent/docs/ea/DRAWIO_GENERATOR_MAINTENANCE.md):

- do not rewrite the existing generator
- do not push Azure-specific solution concerns into generic EA rendering paths
- keep behavior-preserving refactors separate from new capability work

### 3. Reuse draw.io Azure libraries

Do not recreate Azure icons manually.

Instead:

- use draw.io Azure shape libraries
- map semantic YAML service names to draw.io Azure styles
- keep raw draw.io style strings out of most YAML specs

### 4. Deterministic layout over AI layout

For Azure solution diagrams, deterministic layout is preferred over AI layout.

Reasons:

- reference architectures should be consistent across projects
- cloud platform diagrams benefit from repeatable zones and boundaries
- solution review packs need stable visual language
- icon-and-boundary layouts are easier to standardize than freeform storytelling layouts

## Scope of the New Mode

### In Scope

- Azure solution architecture diagrams
- Azure runtime diagrams
- Azure integration diagrams
- Azure security boundary diagrams
- side-by-side current vs target solution diagrams where needed
- Azure service icon rendering via draw.io
- Azure-specific containers and layout rules

### Out of Scope

- replacing existing EA diagram modes
- forcing ArchiMate views to render as Azure diagrams
- recreating Azure icons from scratch
- changing the existing diagram meaning of `freeform`, `hub_spoke`, `matrix`, or `flow_left_right`
- introducing a full multi-cloud abstraction at this stage

## Proposed Module Design

### Existing modules

- `src/ea/drawio_generator.py`
  - remains the generator for generic EA-oriented draw.io diagrams
- `src/ea/drawio_export.py`
  - remains the low-level XML writer
- `src/ea/diagram_generator.py`
  - remains the main orchestration entry point

### New modules

- `src/ea/drawio_azure_generator.py`
  - specialized renderer for `type: "azure_diagram"`
  - owns Azure-specific layout, container rules, and service rendering

- `src/ea/azure_shape_catalog.py`
  - semantic mapping from Azure service keys to draw.io style strings and default dimensions

- optionally later: `src/ea/azure_layouts.py`
  - extracted deterministic layout helpers if `drawio_azure_generator.py` grows substantially

## Responsibility Split

### `diagram_generator.py`

Should:

- load the YAML spec
- detect the diagram mode
- route to the correct renderer
- keep output writing behavior consistent with current flows

Pseudo-routing:

```python
if spec.get("type") == "azure_diagram":
    return DrawIOAzureGenerator(...).generate(...)
else:
    return DrawIOGenerator(...).generate(...)
```

### `drawio_azure_generator.py`

Should:

- interpret Azure-specific YAML schema
- build containers and positioned resources
- resolve `azure_service` to draw.io style definitions
- create edges with Azure-friendly routing defaults
- output draw.io XML through the shared exporter

It should not:

- handle ArchiMate view semantics
- take over existing matrix, hub-spoke, or roadmap generation

### `drawio_export.py`

Should remain a shared XML primitive layer.

It may need small capability additions such as:

- explicit style override on elements
- explicit style override on containers
- support for non-rounded shapes without falling back to generic box rules

It should not understand Azure semantics directly.

## Proposed YAML Contract

### Top-level mode declaration

```yaml
type: "azure_diagram"

view:
  name: "PSS 2.0 Azure Reference Architecture"
  documentation: "Target Azure solution architecture for PSS 2.0"
```

### Layout declaration

```yaml
layout:
  algorithm: "azure_reference"
  pattern: "solution_runtime"
```

Suggested initial patterns:

- `solution_runtime`
- `integration_runtime`
- `current_vs_target`

### Containers

```yaml
containers:
  - name: "Users and Upstream Systems"
    kind: "external"

  - name: "Azure Subscription"
    kind: "subscription"

  - name: "Shared Platform Services"
    kind: "platform"

  - name: "PSS 2.0 Resource Group"
    kind: "resource_group"

  - name: "Observability"
    kind: "observability"

  - name: "Delivery"
    kind: "devops"
```

### Azure resources

```yaml
elements:
  include:
    - name: "Microsoft Entra ID"
      azure_service: "entra_id"
      container: "Shared Platform Services"
      role: "Authentication"

    - name: "Azure API Management"
      azure_service: "api_management"
      container: "PSS 2.0 Resource Group"
      role: "API gateway"

    - name: "PSS 2.0 Runtime"
      azure_service: "container_apps"
      container: "PSS 2.0 Resource Group"
      role: "Application runtime"

    - name: "Azure SQL"
      azure_service: "azure_sql"
      container: "PSS 2.0 Resource Group"
      role: "Operational data store"

    - name: "Azure Key Vault"
      azure_service: "key_vault"
      container: "Shared Platform Services"
      role: "Secrets and certificates"

    - name: "Azure Service Bus"
      azure_service: "service_bus"
      container: "PSS 2.0 Resource Group"
      role: "Asynchronous integration"

    - name: "Application Insights"
      azure_service: "application_insights"
      container: "Observability"
      role: "Telemetry"

    - name: "Log Analytics"
      azure_service: "log_analytics"
      container: "Observability"
      role: "Central logging"
```

### External or non-Azure actors/systems

```yaml
    - name: "QAD SE 11"
      type: "ApplicationComponent"
      render_as: "external_system"
      container: "Users and Upstream Systems"

    - name: "Corporate Users"
      type: "Actor"
      render_as: "user"
      container: "Users and Upstream Systems"
```

### Relationships

```yaml
relationships:
  include:
    - type: "Flow"
      source_name: "Corporate Users"
      target_name: "Azure API Management"
      label: "HTTPS"

    - type: "Serving"
      source_name: "Microsoft Entra ID"
      target_name: "PSS 2.0 Runtime"
      label: "OIDC / token validation"

    - type: "Serving"
      source_name: "Azure Key Vault"
      target_name: "PSS 2.0 Runtime"
      label: "Secrets"

    - type: "Flow"
      source_name: "PSS 2.0 Runtime"
      target_name: "Azure SQL"
      label: "Read / Write"
```

## Azure Shape Catalog

The YAML should use semantic service keys. The style mapping should live in code.

Initial catalog entries:

- `container_apps`
- `api_management`
- `azure_sql`
- `key_vault`
- `service_bus`
- `event_grid`
- `application_insights`
- `log_analytics`
- `front_door`
- `application_gateway`
- `entra_id`
- `container_registry`
- `virtual_network`
- `private_endpoint`
- `storage_account`
- `functions`

Each catalog entry should define:

- draw.io style string
- default width
- default height
- label placement rules if needed

## Azure Layout Model

Initial layout should be deterministic and zone-based.

### Recommended default reading order

1. users and external systems on the left
2. identity and ingress at the upper-left or top
3. application runtime in the center
4. data and messaging to the right or lower-right
5. observability at the bottom
6. delivery and registry at the lower-left or bottom band

### Supported boundary types

- external
- tenant
- subscription
- resource_group
- vnet
- subnet
- platform
- observability
- devops

### Recommended initial layout patterns

#### `solution_runtime`

Best for:

- application runtime on Azure
- core ingress, runtime, data, observability

#### `integration_runtime`

Best for:

- API-led and event-driven integrations
- upstream and downstream system connectivity

#### `current_vs_target`

Best for:

- modernization comparisons
- traditional .NET + DB server vs Azure-native target

## Initial Use Case: PSS 2.0

The first intended use case is a target Azure reference architecture for PSS 2.0 that makes visible the move from a traditional hosting pattern toward a managed Azure runtime.

Expected content:

- current pattern: traditional .NET app and DB server
- target pattern: Azure Container Apps with supporting managed services
- identity, secrets, observability, and integration shown explicitly

This use case is important because the technical debt removal is not well communicated by an application landscape view alone.

## Implementation Plan

### Phase 1: Documentation and schema agreement

- define `azure_diagram` as a first-class spec mode
- document the YAML contract
- agree the initial Azure service catalog
- agree the initial deterministic layout patterns

### Phase 2: Minimal renderer

- add mode routing in `diagram_generator.py`
- create `drawio_azure_generator.py`
- add style override support in `drawio_export.py` if needed
- implement `azure_shape_catalog.py`
- support one stable layout pattern: `solution_runtime`

Success criteria:

- one generated PSS 2.0 Azure diagram
- Azure icons render correctly in draw.io
- no regressions to existing EA diagram modes

### Phase 3: Reusable patterns

- add `integration_runtime`
- add `current_vs_target`
- add standard boundary and legend behavior
- add platform service conventions

### Phase 4: Hardening

- example specs under `ea_inputs/views/infrastructure/`
- tests for catalog resolution and layout output invariants
- documentation updates in `docs/ea/README.md`

## Risks and Controls

### Risk: Azure mode leaks into generic generator behavior

Control:

- route `azure_diagram` to a dedicated module
- keep changes to the shared exporter minimal and generic

### Risk: YAML becomes raw draw.io styling in disguise

Control:

- keep raw draw.io style strings inside the Azure catalog, not in most view specs
- use semantic keys like `azure_service: "container_apps"`

### Risk: Existing maintenance stance is violated by accidental rewrite

Control:

- do not refactor `drawio_generator.py` as part of the first Azure implementation
- introduce the new path beside the existing generator

### Risk: Diagrams look Azure-branded but semantically inconsistent

Control:

- define standard layout patterns up front
- use a small curated service catalog first
- validate against one real reference use case before broadening

## Open Questions

1. Should Azure diagrams live under the existing `ea_generate_diagram` tool with mode auto-detection, or eventually get a dedicated MCP entry point?
2. Do we want a strict schema for allowed `azure_service` values, or a soft catalog with warnings?
3. Should the first version support network containers like `vnet` and `subnet`, or defer them until after `solution_runtime` works?
4. Do we want optional side legends that distinguish shared platform services from app-local services?

## Recommended Next Step

Draft and review the first concrete spec:

- `ea_inputs/views/infrastructure/pss2_azure_reference_architecture.yaml`

That spec should be the design anchor for implementing the first `azure_diagram` renderer.
