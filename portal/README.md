# EA Portal

Static portal for architecture diagrams, application and infrastructure inventories,
architectural decisions and project processes.

## Contents

- [Build and local preview](#build-and-local-preview)
- [Sources, templates and generated output](#sources-templates-and-generated-output)
- [Project folders and navigation](#project-folders-and-navigation)
- [Project process views](#project-process-views)
- [Ticket history CSV](#ticket-history-csv)
- [Architecture Decisions](#architecture-decisions)
- [Environment inventory views](#environment-inventory-views)
- [Architecture diagrams and catalogue](#architecture-diagrams-and-catalogue)
- [Verification and troubleshooting](#verification-and-troubleshooting)
- [Deployment](#deployment)

## Build and local preview

Use the repository's existing virtual environment, preferably Python 3.11. See
the [root setup guide](../README.md#setup) for initial installation.
From the repository root in Windows PowerShell:

```powershell
. .\.venv\Scripts\Activate.ps1
$env:PYTHONIOENCODING = 'utf-8'
python portal\build.py
python -m http.server 8080 --bind 127.0.0.1 --directory portal\dist
```

Open <http://127.0.0.1:8080/>. Reuse an existing preview server if available.
Rebuild after source changes and hard-refresh the browser.

Build dependencies include pandas, openpyxl, PyYAML, jsonschema and lxml; versions
are declared in `pyproject.toml`. This is not a standard-library-only build.
It does not require Azure DevOps/OpenAI credentials, parse original design
documents, call an LLM or synchronize remote systems.

The local preview has no authentication. Keep it bound to loopback; do not treat
it as a shared production server.

## Sources, templates and generated output

`portal\assets\` is the shared project-page template directory. Each project's
YAML/JSON provides content; do not copy the HTML into each project.

| Page/component | Maintained source/template | Renderer or build code |
|---|---|---|
| Main portal shell and sidebar | HTML/Vue template inside `portal\backend\builder.py` | `portal\backend\builder.py` |
| Project process | `portal\assets\process-view.html` plus project process YAML | `portal\backend\process_views.py` |
| Architecture Decisions | `portal\assets\architecture-decisions.html` plus project register JSON | `portal\backend\architecture_decisions.py` |
| Infrastructure Inventory | `portal\assets\infra-portal.html` plus environment inventory JSON | `portal\backend\builder.py` |
| Application Inventory | `portal\assets\app-inventory-portal.html` plus environment inventory JSON | `portal\backend\builder.py` |
| Application Architecture | Environment application inventory JSON | `portal\backend\app_diagram.py` |
| Diagram SVG and cross-view navigation | draw.io artifacts and ArchiMate CSVs | `portal\backend\converter.py`, `portal\backend\indexes.py` |
| How It Works | Imported project-owned HTML and story JavaScript | `portal\backend\builder.py` |

Generated files live under:

```text
portal\dist\
  index.html                 Main portal shell
  data\                      View registry, element and relationship indexes
  diagrams\                  Generated SVG diagrams
  projects\<project_key>\    Project-level and environment iframe pages
```

The builder registers views in `data\view_registry.json`. The shell displays
diagrams or opens project pages through `iframe_src`; no per-project sidebar
coding is needed for supported input layouts.

Edit content in the project's YAML/JSON, shared presentation in the corresponding
template, and discovery/navigation rules in the builder. Never edit `dist` as a fix.

## Project folders and navigation

```text
ea_inputs\04_projects\<domain>\<project>\
  design\
    infrastructure-onboarding.yaml
    ticket-history.csv
    architecture-decisions.json
    sources.local.yaml              Local-only source-document mapping
  <env>\
    infra-inventory.<env>.json
    app-inventory.<env>.json
    how-it-works.html
    how-it-works.story.js
    runtime-inventory\              Raw evidence, not directly rendered
```

Only supply artifacts relevant to the project; none of these pages requires
creating empty files for the other types. Standard environment ordering is dev,
test, uat, prod. Project-level design/process pages sit alongside these folders.

By default, the project display name comes from its folder and `project_key` is
the lowercase slug. To set a stable key, display name, domain or region, add a
`type: json_inventory` metadata spec under `ea_inputs\views\`, for example
`ea_inputs\views\operations\example_inventory.yaml`:

```yaml
type: json_inventory
inventory: "04_projects/operations/Example"
metadata:
  project_key: example
  project: "Example Project"
  domain: Operations
  region: ANZ
```

The project folder must exist. `inventory` points to that folder relative to
`ea_inputs`, not to an individual inventory file. This metadata also applies to
process and decision pages, including projects with no environment inventories.
Use a unique project key across the portal.

Filesystem examples use Windows separators. Contract fields such as `inventory`,
`ticket_history_file` and inventory bindings use `/` in their stored relative
paths, as required by the builder/schema.

## Project process views

### YAML to HTML

The reusable page template is **`portal\assets\process-view.html`**.
The project-specific input is:

`ea_inputs\04_projects\<domain>\<project>\design\infrastructure-onboarding.yaml`

The build:

1. Discovers that exact filename under each project.
2. Validates against `ea_inputs\04_projects\_schema\process-view.schema.json`.
3. Checks IDs, references, dependency cycles, phase order, timing ranges and
   referenced inventory artifacts. Resolves CSV-backed ticket references.
4. Embeds the validated content into the shared HTML template.
5. Writes `portal\dist\projects\<project_key>\infrastructure-onboarding\index.html`
   and registers `project_<project_key>_infrastructure_onboarding`.

The template's `$project` and `$process_data` placeholders are filled by
`portal\backend\process_views.py` using `string.Template`. For template changes,
avoid JavaScript `${...}` template literals unless escaped for that substitution.
Keep embedded JSON escaped and user/source text rendered with `textContent`.

The filename and output route are currently fixed. `view.name` changes the display
title, not the route. Arbitrary process filenames or several process pages per
project are not implemented.

### Author another project

Create the project's `design` folder and author its YAML using the example below.
Alternatively, adapt the
[PSS2 worked example](../ea_inputs/04_projects/operations/PSS2/design/infrastructure-onboarding.yaml),
replacing its project-specific roles, services, stages, dependencies, ticket
references, observations, inventory bindings and estimates. PSS2's six stages
and 60-day estimate are not enterprise defaults.

No separate starter file is installed or auto-copied. The following is a complete,
schema-valid minimal example, with illustrative content and durations:

```yaml
schema_version: "1.0"
intent:
  question: "Who reviews the project design?"
  audience: "Management and project owners"
  decision: "Prepare the design review"
  key_message: "EA reviews the design before infrastructure work begins."
view:
  name: "Infrastructure Onboarding"
  subtitle: "Project process and request history"
  status: draft
  notice: "Illustrative example; estimates require confirmation."
roles:
  - id: ea
    name: EA
    description: "Reviews the project design."
services:
  - id: emails-meetings
    name: Emails/Meetings
    description: "Design review and recorded approval."
    provider: "Project collaboration tools"
    usage: setup
phases:
  - id: ea-review
    name: EA Review
    summary: "Review the proposed project design."
    timing:
      basis: assumption
      min_days: 2
      max_days: 5
      note: "Illustrative business-day allowance."
activities:
  - id: approve-design
    name: Approve the project design
    phase: ea-review
    owner: ea
    contributors: []
    depends_on: []
    services: [emails-meetings]
    purpose: "Confirm the design and record conditions."
    inputs: ["Project scope and design"]
    outputs: ["Recorded design review outcome"]
    completion: ["EA approval and conditions are recorded."]
    record:
      label: "Design review email / meeting record"
      url: null
      state: "Record not supplied"
    timing:
      basis: assumption
      min_days: 2
      max_days: 5
      note: "Illustrative estimate, not measured elapsed time."
    subprocesses: []
project:
  identity_note: "No CMDB identity match has been established."
  sources:
    - id: workshop
      label: "Process workshop"
      reference: "Replace with the actual source and review date."
  observations: []
layout:
  phase_order: [ea-review]
  role_order: [ea]
  service_order: [emails-meetings]
iterations: []
```

Review the content with its process owner, record meaningful changes in
`iterations`, build, and inspect the new view in the full portal shell.

### YAML field reference

| Section | Required content and conventions |
|---|---|
| `schema_version` | `"1.0"` |
| `intent` | Question, audience, decision and key message |
| `view` | Name, subtitle, status (`draft`/`reviewed`) and notice. Subtitle/status/notice remain metadata rather than visible introductory banners |
| `roles` | Stable ID, name and description for each business role |
| `services` | ID, name, description, provider and usage (`setup`, `runtime`, `setup_and_runtime`) |
| `phases` | ID, name, summary and independently authored group timing |
| `activities` | ID, name, phase, owner, contributors, dependencies, services, purpose, inputs, outputs, completion, record, timing and subprocesses |
| `project` | Source list, observations and identity note; optional `ticket_history_file` |
| `layout` | Phase, role and service ordering; list each corresponding ID once |
| `iterations` | Version, date, feedback and change for each recorded iteration; may start empty |

IDs use lowercase letters, digits and hyphens, starting with a letter. Preserve
them when renaming labels so selection links remain stable.

Each `timing` requires `basis`, `min_days`, `max_days`, `note`. Ranges are finite,
nonnegative business days, with minimum no greater than maximum. Equal values
display one duration, such as `60 days`. Use `assumption` for estimates, displayed
as **Indicative**. Use `ticket_measurement` only with supporting evidence. Optional
`queue_days`/`work_days` are not shown as separate right-panel cards. Group ranges
are maintained separately, not calculated by summing parallel activities.

Each `record` requires `label`, `url` (HTTP/S or `null`) and `state`. Link tickets
through [the CSV workflow](#ticket-history-csv), or supply optional inline
`tickets` objects containing `number`, `purpose`, `system`, `request_type`,
`assigned_to`; do not provide both `tickets` and `ticket_numbers`.

Each subprocess requires an ID, name, purpose, outputs and completion criteria;
inputs are optional. A subprocess shares its parent activity's timing.

Observations require an ID, activity references, source ID, classification,
date (`YYYY-MM-DD` or `null`) and text. Classifications are
`reported_observation`, `inventory_reference` and `unverified`. Optional `inventory`
bindings specify `file` relative to `ea_inputs` and actual `artifact_ids`.
Keep snapshot dates distinct from workshop/report dates.

The schema is the exact field contract; do not invent extra YAML sections.
The entire validated payload is embedded in the page: hidden UI metadata is
not confidential storage.

### Shared presentation

- **Who is involved**, **What happens**, **What supports the work** form three bands.
- The grey duration band sits beneath **What happens**. Expanded stages retain
  the parent title and duration, with slimmer, indented activity cards underneath
  in both lanes. Expansion scrolls into view and preserves keyboard focus.
- Selection opens details and highlights related roles, services and dependencies.
  Ticket history shows all linked tickets in the overview and relevant tickets
  for a selected stage, activity, role or service.
- Use neutral headings. Do not reintroduce slogans, the introductory draft banner,
  visible draft badges or the removed **Source, confidence & identity** section.
- Inventory existence and ticket closure do not prove readiness. Keep actual
  production release dependent on its required approval.

### Selection links

Standalone links use the generated page's fragment:

```text
http://127.0.0.1:8080/projects/pss2/infrastructure-onboarding/#phase=connect
http://127.0.0.1:8080/projects/pss2/infrastructure-onboarding/#activity=configure-dns
http://127.0.0.1:8080/projects/pss2/infrastructure-onboarding/#subprocess=authorize-workloads%2Fgraph-consent
```

Role and service links use `#role=<id>` and `#service=<id>`. The main portal route
is `/?view=project_<project_key>_infrastructure_onboarding&expandProjects=1`.
Use **Copy selection link** inside the page for a specific selection.

## Ticket history CSV

Keep the supplied ticket table as an input file in the project's `design` folder,
not solely as pasted prose or duplicate YAML. PSS2's source is:

`ea_inputs\04_projects\operations\PSS2\design\ticket-history.csv`

Required columns:

```csv
Ticket No,Purpose,System,Request Type,Assigned To
```

Use UTF-8 (a BOM is accepted), unique numeric ticket numbers and nonempty fields.
Quote fields containing commas or newlines using normal CSV rules.
In the process YAML, point to the source under `project`:

```yaml
project:
  ticket_history_file: "04_projects/operations/PSS2/design/ticket-history.csv"
```

This is a fragment to add to the existing `project` section, not a complete file.
Link the relevant numbers from each activity's existing record:

```yaml
record:
  label: "API and UI application registrations"
  url: null
  state: "Ticket references supplied; dates and status not supplied"
  ticket_numbers: ["7408177", "7408178"]
```

At build time, the renderer resolves the selected rows into the embedded page
data. Missing references, malformed rows, duplicate numbers or conflicting inline
ticket copies fail validation. CSV details remain the authoritative ticket input;
the YAML maps tickets to process activities.

An unreferenced row is not automatically associated with an activity or displayed.
Add its mapping deliberately. No LLM is needed to import or update these records.
Keeping the file in `design` excludes it from generic EA model discovery.

Assigned teams are the supplied ticket assignments, not automatic replacements
for accountable process roles. Numbers and descriptions alone do not establish
status, start/end timestamps, measured waits or completion.

## Architecture Decisions

Author `design\architecture-decisions.json` against
`ea_inputs\04_projects\_schema\architecture-decisions.schema.json`. The build
renders it through `portal\assets\architecture-decisions.html`, at:

`portal\dist\projects\<project_key>\architecture-decisions\index.html`

This project-level page supports search and filters for source-referenced
decisions, constraints and open questions. Each entry retains its stable ID,
affected systems, source sections, position and documented rationale (`null`
when absent). Document approval is separate from individual entry status.

Source extraction follows [the decision prompt](../prompts/ea/architecture_decisions.md)
and [AGENTS.md](../AGENTS.md#project-design-ingestion). A Git-ignored
`sources.local.yaml` selects the exact OneDrive baseline. Compare hashes before
parsing; read tables and only body-referenced figures, not orphaned DOCX media.
Review fidelity and publication scope before building.

The portal does not perform that extraction or update the ArchiMate model.
Invalid registers fail validation rather than silently hiding the page.

## Environment inventory views

### Infrastructure

`infra-inventory.<env>.json` is validated against
`ea_inputs\04_projects\_schema\infra-inventory.schema.json`. The builder embeds it
in the shared infrastructure template and registers
`project_<project_key>_infra_<env>` under the environment.

Output: `portal\dist\projects\<project_key>\<env>\index.html`.
Validation errors are reported and that inventory view is skipped; check build
logs and the registry, not only the final exit code. Catalogue-name joining is a
name-based warning/check, not guaranteed CMDB identity resolution.

### Application

`app-inventory.<env>.json` produces two views:

| View | Output |
|---|---|
| Application Architecture | `portal\dist\diagrams\projects\<project_key>\app-architecture.<env>.svg` |
| Application Inventory | `portal\dist\projects\<project_key>\<env>\app-inventory\index.html` |

The inventory page embeds `window.APP_INVENTORY_DATA`. It starts at the detail
drilldown with Components, Frontend Paths and API Surface; selecting a row opens
a closeable detail modal. It is not a second architecture overview.

The portal build generates the architecture diagram from the application inventory.
For an explicitly requested standalone draw.io export, with the environment active:

```powershell
python -m portal.backend.app_diagram "ea_inputs\04_projects\<domain>\<project>\<env>\app-inventory.<env>.json" "ea_diagrams\projects\<project_key>\app-architecture.<env>.drawio"
```

Replace placeholders before running. Fix upstream inventory generation where
possible rather than making recurrent edits to imported output.

### How It Works

A `how-it-works.html` with sibling `how-it-works.story.js` produces
`projects\<project_key>\<env>\how-it-works\index.html`. The builder inlines the
story and registers `project_<project_key>_how_it_works_<env>`.

Both files are owned by the originating project repository. Fix there, re-import
the pair and record the source revision. Do not edit the imported engine here.

Inventory/process pages embed their data at build time rather than retrieving
the original input files or upstream services at browser runtime.

## Architecture diagrams and catalogue

Architecture diagrams come from maintained specs and generated draw.io artifacts.
The builder converts diagrams to SVG and combines model and view information into
`view_registry.json`, `element_index.json` and `relationship_graph.json`.
Element selection supports properties, relationships and cross-view appearances.

Use the `create-diagram` workflow for new diagrams and source-first changes.
Consult a current spec under `ea_inputs\views\` and the applicable schema/code,
not a historical planning example alone.

The Application Catalogue workbook at
`ea_inputs\02_IT_systems\Application Catalogue.xlsx` separately supplies portfolio
navigation and analytics. Rebuild after catalogue, model, spec or diagram changes.
Do not treat the catalogue, CMDB export and project inventory IDs as interchangeable.

## Verification and troubleshooting

| Symptom/change | Check |
|---|---|
| Source/template edited but page unchanged | Rebuild, confirm output path, hard-refresh |
| New process page missing | Exact filename/location, schema errors, project metadata and registry |
| Ticket omitted or build fails | CSV headers/rows, quoted fields and activity `ticket_numbers` |
| Inventory view missing | Validation report; infrastructure errors can skip a view |
| Unexpected project grouping | Stable unique `project_key`, metadata spec and project-relative `inventory` path |
| Process timing misleading | Explicit phase/activity estimates, correct basis and source timestamps |
| Content clipped in a standalone success case | Inspect inside the actual portal shell at the target screen size |

For code/template changes, run the smallest applicable tests with the venv active:

```powershell
python -m pytest tests\ea\test_process_views.py
python -m pytest tests\ea\test_architecture_decisions.py
python -m pytest tests\ea\test_app_inventory_drawio_metadata.py
```

Then build and review affected pages. For process interaction changes, exercise
stage/subprocess expansion, retained parent headers, scrolling/focus, selection,
duration toggling, ticket filtering and stable links. Read build warnings.
Documentation-only edits do not require a build; YAML examples should validate.

See [AGENTS.md](../AGENTS.md#verification-and-deployment) for operating safeguards
and [the current test guide](../tests/README.md#current-suite).

## Deployment

The supported deployment route is the root
[Azure DevOps pipeline](../azure-pipelines.yml), not a local Docker workflow.
There is no required local Docker engine.

The root [Dockerfile](../Dockerfile) builds the portal with Python 3.11 and the
five portal dependencies selected from `pyproject.toml`, then copies `dist` into
an nginx image. [nginx.conf](../nginx.conf) configures static serving on port 80.
Azure Container Registry builds the image; the pipeline updates the existing
Container App and checks revision health and anonymous access rejection.

Production sign-in is enforced by platform EasyAuth, not by the static HTML.
It does not reproduce source SharePoint ACLs; review publication scope before
including design extracts, ticket details or other internal evidence.

A local build/preview does not publish. Pushes to the pipeline's configured
main-branch paths can trigger deployment; do not trigger, push or deploy without
authorization. Use the actual pipeline stages and approvals rather than assuming
a parameter labelled staging provides a separate staging deployment.
