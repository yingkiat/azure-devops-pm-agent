# EA Portal Territory Expansion Plan

## Purpose

The EA portal currently works well for APAC because the application catalogue, ArchiMate model, diagrams, and portfolio analytics all describe the same maintained architecture scope.

The next requirement is to expand the portal to show additional territories, starting with EMEA and potentially Canada, without clouding or corrupting the working APAC dataset.

This document records the proposed approach.

## Current State

The main maintained datasource is:

```text
ea_inputs/02_IT_systems/Application Catalogue.xlsx
```

The workbook currently contains:

| Sheet | Role | Current Use |
| --- | --- | --- |
| `Catalogue` | APAC application catalogue | Main APAC catalogue source |
| `Validation` | APAC validation lists | Supporting workbook validation |
| `EMEA Catalogue` | EMEA application catalogue | New catalogue-only territory source |
| `EMEA Validation` | EMEA validation lists | Supporting workbook validation |

The current APAC model-backed dataset is generated into:

```text
archi_inputs/elements.csv
archi_inputs/properties.csv
archi_inputs/relations.csv
archi_inputs/model.xml
```

The current portal build also generates disposable frontend data into:

```text
portal/dist/data/catalogue.json
portal/dist/data/analytics.json
```

## Design Principle

Multi-territory catalogue data can power portfolio views, but only explicitly model-backed territories are allowed to mutate the EA model.

For now:

| Territory | Catalogue-backed | Model-backed | Diagram-maintained |
| --- | --- | --- | --- |
| APAC | Yes | Yes | Yes |
| EMEA | Yes | No | No |
| Canada | Future | No by default | No by default |

This preserves APAC as the trusted architecture dataset while still enabling portfolio visibility for EMEA and future territories.

## Source of Truth

The maintained EMEA source of truth should remain the workbook sheet:

```text
Application Catalogue.xlsx / EMEA Catalogue
```

EMEA data should not be written into these files by default:

```text
archi_inputs/elements.csv
archi_inputs/properties.csv
archi_inputs/relations.csv
archi_inputs/model.xml
ea_inputs/views/**/*.yaml
ea_diagrams/**/*.drawio
```

Instead, EMEA should appear only in generated portal data artifacts:

```text
portal/dist/data/catalogue.json
portal/dist/data/analytics.json
```

Those files are build outputs and can be regenerated from the workbook.

## Proposed Data Flow

```text
Application Catalogue.xlsx
  Catalogue        -> APAC catalogue rows -> portal catalogue/analytics + APAC model enrichment
  EMEA Catalogue   -> EMEA catalogue rows -> portal catalogue/analytics only
  CANADA Catalogue -> Canada catalogue rows -> portal catalogue/analytics only, when added
  Validation tabs  -> ignored as application rows
```

The portal build should read catalogue sheets using an explicit sheet mapping:

| Sheet Pattern | Territory |
| --- | --- |
| `Catalogue` | `APAC` |
| `EMEA Catalogue` | `EMEA` |
| `CANADA Catalogue` | `CANADA` |

Validation sheets should not be treated as application datasets.

## Normalized Catalogue Record

The generated portal catalogue record should include common fields across territories:

```text
territory
source_sheet
model_backed
model_element_id
domain
region
sub_domain
it_owner
name
description
tech_standard
hosting_type
sensitive_data
vendor_support
risk_level
business_criticality
administrator_team
disaster_recovery_tier
application_short_code
GXP
Validated
roadmap_disposition
planning_horizon
```

Example EMEA generated row:

```json
{
  "territory": "EMEA",
  "source_sheet": "EMEA Catalogue",
  "model_backed": false,
  "model_element_id": null,
  "name": "Active Directory Europe",
  "domain": "Technical Services",
  "region": "Europe"
}
```

Example APAC generated row:

```json
{
  "territory": "APAC",
  "source_sheet": "Catalogue",
  "model_backed": true,
  "model_element_id": "id-...",
  "name": "Microsoft Dynamics",
  "domain": "Commercial",
  "region": "ANZ"
}
```

## Portal UX Proposal

The Application Catalogue and Portfolio Analytics pages should become territory-scoped views rather than separate hardcoded APAC and EMEA pages.

Recommended selector:

```text
Scope: [APAC]
```

Options:

```text
APAC
EMEA
CANADA
All International
```

The default should remain `APAC` to preserve the current portal experience.

## Application Catalogue Page

When `APAC` is selected:

- Show the current APAC catalogue behavior.
- Use APAC rows from the `Catalogue` sheet.
- Enrich matched rows from the APAC ArchiMate model where available.

When `EMEA` is selected:

- Show rows from `EMEA Catalogue`.
- Do not require matching ArchiMate elements.
- Display `model_backed: false` status where useful.

When `All International` is selected:

- Show APAC, EMEA, and future Canada rows together.
- Include `territory` as a visible/filterable column.

## Portfolio Analytics Page

The Portfolio Analytics page should use the same territory scope selector.

### APAC Scope

APAC should remain the detailed operational analytics view.

Keep the current analytics layout where possible:

- Total Applications
- Legacy percentage
- SaaS percentage
- Tech Standard Approved
- In Progress
- Application Type Breakdown
- Business Criticality
- Applications by Domain or Sub-Domain
- Region Distribution
- Planning Horizon
- Roadmap Disposition
- Legacy by Domain or Sub-Domain
- Disposition by Planning Horizon matrix

Data basis should be labelled as:

```text
APAC: model-backed + catalogue-backed
```

### EMEA Scope

EMEA should be treated as catalogue-backed only.

Use workbook fields directly:

- Total Applications
- Tech Standard
- Hosting Type
- Sensitive Data
- Risk Level
- Business Criticality
- Domain and Sub-Domain
- Region

Only show roadmap analytics if `roadmap_disposition` and `planning_horizon` are populated.

Data basis should be labelled as:

```text
EMEA: catalogue-backed only
```

### All International Scope

The consolidated view should be management-oriented and comparative.

Recommended cards and charts:

- Total Applications
- Territories in Scope
- Applications by Territory
- Legacy count and rate by Territory
- SaaS rate by Territory
- High Risk Applications by Territory
- Tech Standard by Territory
- Hosting Type by Territory
- Business Criticality by Territory
- Domain Mix by Territory
- Sensitive Data by Territory, where available

The consolidated view should avoid implying that all territories have the same architecture maturity. APAC is model-backed; EMEA and future Canada may be catalogue-only.

## Guardrails

Implementation should enforce the following:

1. Do not automatically import EMEA or Canada rows into `archi_inputs`.
2. Do not create ArchiMate elements for EMEA or Canada unless explicitly requested.
3. Do not enrich EMEA rows from APAC model properties by name alone.
4. Do not use workbook active sheet behavior for multi-territory portal data.
5. Use an explicit sheet-to-territory mapping.
6. Ignore validation sheets as application rows.
7. Default portal scope to APAC.
8. Include provenance fields such as `territory`, `source_sheet`, and `model_backed`.
9. Warn during build if a catalogue sheet lacks required fields such as `name`, `domain`, or `region`.

## Identity and Matching Risk

Application names may repeat across territories. The same product name can represent different ownership, lifecycle, hosting, risk, and roadmap positions.

Avoid using application name alone as a global identity.

Preferred future key:

```text
application_id
```

Interim key:

```text
territory + application_short_code
```

Fallback key:

```text
territory + normalized_name
```

APAC model matching can continue to use name matching within APAC scope, but cross-territory matching should be avoided unless a stable global identifier exists.

## Future Promotion to Model-Backed Territory

If EMEA or Canada later needs maintained architecture objects and diagrams, promote that territory deliberately.

Promotion should include:

- A territory-specific ingestion plan.
- Agreement on stable application identifiers.
- ArchiMate element creation rules.
- Relationship and diagram maintenance ownership.
- Portal labels updated from catalogue-only to model-backed.
- Regression checks proving APAC views and analytics remain unchanged.

Until that decision is made, non-APAC territories should remain catalogue-backed only.

## Implementation Phases

### Phase 1: Portal-Only Multi-Territory Catalogue

- Read all explicitly mapped catalogue sheets.
- Generate combined `catalogue.json`.
- Add `territory`, `source_sheet`, and `model_backed`.
- Default UI scope to APAC.
- Keep EMEA out of `archi_inputs`.

### Phase 2: Territory-Scoped Analytics

- Filter analytics by selected territory.
- Preserve current APAC analytics behavior.
- Add catalogue-only analytics for EMEA.
- Add consolidated All International analytics.

### Phase 3: Canada Readiness

- Support `CANADA Catalogue` by convention.
- Keep Canada catalogue-only by default.
- Reuse the same selector and analytics logic.

### Phase 4: Optional Model-Backed Expansion

- Only if a territory needs maintained diagrams and EA objects.
- Treat this as a separate architecture decision, not a portal build side effect.

