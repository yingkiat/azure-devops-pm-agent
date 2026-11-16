# Azure DevOps PM/EA Agent

This is the canonical operating guide for GitHub Copilot CLI in this repository.
It covers ingestion, architecture artifacts and the EA Portal. Maintain shared
operating rules here; no separate Claude operating guide is required.

## Contents

- [Working rules](#working-rules)
- [Environment and tools](#environment-and-tools)
- [Repository and data boundaries](#repository-and-data-boundaries)
- [EA model ingestion](#ea-model-ingestion)
- [Project design ingestion](#project-design-ingestion)
- [Architecture diagrams and presentations](#architecture-diagrams-and-presentations)
- [Project process views](#project-process-views)
- [Portal sources and build](#portal-sources-and-build)
- [Verification and deployment](#verification-and-deployment)
- [Azure DevOps operations](#azure-devops-operations)

## Working rules

- Fix regenerable issues at their source: YAML, JSON, prompts, templates or generator
  code. Never patch `portal\dist\`, exported SVGs or generated draw.io files as the
  primary fix unless the user explicitly requests a one-off edit.
- Preserve unrelated worktree changes. Do not remove legacy code, caches, inputs,
  diagrams or registered views as incidental cleanup.
- Record scope and audience, reuse requirements already supplied, and obtain review
  before generating a newly proposed view. Use factual headings, not promotional
  slogans or repetitive disclaimers.
- Distinguish source statements, design intent, deployed facts, reported observations
  and verified completion. Do not silently reconcile contradictory evidence.
- Do not infer identity between similarly named CMDB applications, catalogue rows
  and project inventories. Do not transfer historical owners or status by name alone.
- Do not commit credentials, source-document copies or personal OneDrive paths.
  Source access does not authorize broader republication. A static portal does not
  inherit per-document SharePoint permissions, even when portal sign-in is enabled.

## Environment and tools

Run commands from the repository root. Use the existing virtual environment;
activate it before every Python command in a fresh shell. On Windows PowerShell:

```powershell
. .\.venv\Scripts\Activate.ps1
$env:PYTHONIOENCODING = 'utf-8'
```

See the [root README](README.md#setup) for installation, environment variables and
Copilot MCP setup. Prefer Python 3.11, matching the portal container build.

- Use the configured MCP tools for operational EA discovery/model generation and
  Azure DevOps queries or changes. Do not bypass them with scripts importing the
  application functions.
- Use Copilot CLI `/mcp` to inspect/configure servers and available tools. Tool
  names in this guide are short names, not a hardcoded client-specific prefix.
  If a required tool is unavailable, report it rather than claiming it ran.
- Skills supply instructions, not autonomous execution. Follow the relevant skill
  workflow and then execute its steps.
- Direct commands are appropriate for the documented deterministic portal build,
  tests, local preview and agent-guided source inspection. They are not a substitute
  for MCP discovery.
- The MCP server is a persistent Python process. After changing `src\mcp_server.py`,
  `src\core\file_monitor.py`, `src\ea\` or another imported module, restart that
  configured server; restart Copilot CLI if necessary. A portal rebuild is a new
  process and does not require restarting MCP.

## Repository and data boundaries

| Location | Role |
|---|---|
| `ea_inputs\01_company_context\` | Organization and business context |
| `ea_inputs\02_IT_systems\` | System descriptions, CMDB export and Application Catalogue workbook |
| `ea_inputs\03_global_standards\` | Cross-project standards and policies |
| `ea_inputs\04_projects\<domain>\<project>\<env>\` | Imported/generated project inventories and environment evidence |
| `ea_inputs\04_projects\<domain>\<project>\design\` | Curated design register, process YAML and source ticket CSV |
| `ea_inputs\04_projects\_schema\` | Inventory, architecture-decision and process contracts |
| `ea_inputs\views\` | Architecture diagram specs and optional project metadata specs |
| `archi_inputs\` | Generated canonical EA model: elements, relations, properties, views and model XML |
| `ea_diagrams\` | Diagram artifacts used by the portal |
| `ea_outputs\` | Discovery and presentation outputs |
| `prompts\` | Extraction and generation guidance |
| `portal\assets\` | Shared project-page HTML templates |
| `portal\backend\` | Portal builder, converters, validators and renderers |
| `portal\dist\` | Generated static site; never the authoring location |

Project evidence has two independent streams: machine-generated environment
inventories and human-authored DESIGN. Do not introduce a PLC/SDLC folder hierarchy
or use design intent to overwrite deployed inventories. Architecture Decisions and
Infrastructure Onboarding appear directly under a project, alongside environment
folders, not inside DEV/TEST/PROD.

## EA model ingestion

1. Read the relevant source material and existing `archi_inputs\elements.csv`,
   `properties.csv` and `relations.csv` before proposing model additions.
2. Choose the narrowest source directory that covers the request. Use
   `ea_discover_directory` for incremental directory ingestion or `ea_discover`
   for an explicitly supplied system description.
3. Use supported text, Markdown, CSV and Excel inputs. `.xlsx` is converted
   internally by `src\shared\file_converters.py`; do not pre-convert it manually.
   Do not send DOCX/PPTX directly to bulk discovery as though it parses them.
4. For architecture images/slides, use `ea_ingest_images`, inspect the extracted
   text, then discover the appropriate text directory. Use `ea_clear_image_cache`
   only when re-extraction is intended.
5. Inspect tool errors, processed/skipped files and the resulting model summary.
   Directory discovery uses file tracking and output validation; a cache hit must
   not be presented as a fresh semantic extraction. Do not promise perfect
   deduplication or fixed token savings.
6. Use `ea_import_catalogue` when deterministic catalogue-property import is
   requested. It matches application names and catalogue values win on conflict;
   it is not CMDB Asset ID identity resolution.
7. For Archi views, use `ea_generate_views_from_specs`, review its validation
   report, and use `ea_finalize_views` when finalization is required. Verify the
   resulting `views.csv` and `model.xml`; use `ea_get_data_summary` for model counts.

Bulk discovery excludes project `design\` folders. Keep curated decision registers,
process definitions and local source mappings out of generic discovery.

"Full ingestion" means directory discovery followed by the existing Archi view
workflow, not reset, document reconstruction or automatic portal deployment.
If asked to "generate a YAML", check whether the user means render an existing
spec rather than author a new one. `ea_reset_model` is destructive and requires
explicit approval; do not clear caches or models just to force a refresh.

The CMDB CSV is an imported snapshot, not live synchronization. Model discovery
and property normalization are implemented in code as well as prompts; consult
`src\ea\archi_export.py` before changing property-name handling.

## Project design ingestion

Follow [the extraction prompt](prompts/ea/architecture_decisions.md). This is
agent-guided extraction, separate from generic EA model discovery.

1. Keep the document in its Teams/SharePoint-backed OneDrive location. Associate
   it through Git-ignored `design\sources.local.yaml` using `folder` and an exact
   `files` list. Never scan all versions, choose "latest" from timestamps/filenames,
   or assume a file labelled FINAL is approved.
2. Resolve selected filenames inside the mapped folder; reject escaping paths.
   The current register represents one baseline document. If multiple files are
   selected, obtain the intended baseline rather than silently merging them.
3. Compute SHA-256 before parsing. Reuse an unchanged register unless extraction
   guidance changed or the user requests reprocessing. Do not claim an automatic
   semantic cache or OneDrive watcher exists; this is an agent-guided workflow.
4. Read body paragraphs and tables in order. Inspect figures actually referenced
   by the document body; orphaned packaged DOCX media is not evidence. Preserve
   section/table/figure references and report unreadable figures or conflicts.
5. Extract decisions, constraints and open questions, not a rewritten design
   document. Preserve stable entry IDs, affected systems and source sections.
   Record documented rationale only; use `null` when it is absent.
6. Preserve document approval separately from entry status. A stated choice is
   not necessarily approved or deployed; a detail defined elsewhere is not
   automatically an unresolved organizational question.
7. Write `design\architecture-decisions.json` against
   `ea_inputs\04_projects\_schema\architecture-decisions.schema.json`. Review claim
   fidelity and publication scope, then build the portal.

The portal validates and renders that register with
`portal\assets\architecture-decisions.html`. It does not access OneDrive, parse the
original document, call an LLM or update ArchiMate as part of this build.

## Architecture diagrams and presentations

- Invoke the available `create-diagram` skill for diagram/view creation and follow
  its intent, source audit, review, generation and output-verification gates.
  Use the presentation skill for decks and the catalogue skill for catalogues.
- Read relevant implementation/MVP documentation and a current working spec before
  introducing fields. Historical planning documents are not proof of implementation.
  Current examples live in domain folders under `ea_inputs\views\`.
- Structured diagrams select model elements. Prefer explicit names for curated
  views; confirm exact property values before using `where` filters.
- Use `matrix` for primary plus secondary grouping, `grid` for one grouping
  property, and `column` for ungrouped vertical stacking. `column` does not mean
  horizontal lanes. Use the skill's freeform workflow for explicit custom layouts.
- Keep view-specific overrides in the spec rather than modifying model facts to
  fit a presentation. Preserve intent and document feedback in `iterations`.
- Generate through the appropriate available MCP tool: `ea_generate_diagram`,
  `ea_generate_presentation_diagram`, or `ea_generate_mermaid`. Check the actual
  output against the spec and inspect layout, labels, clipping and relationships.
- Project process YAML uses a different schema and the existing portal renderer,
  not the ArchiMate diagram generator. Do not add process fields to an EA view spec.

## Project process views

### Source and rendering contract

| Artifact | Purpose |
|---|---|
| `portal\assets\process-view.html` | Shared HTML/CSS/JavaScript page template; reuse across projects |
| `ea_inputs\04_projects\<domain>\<project>\design\infrastructure-onboarding.yaml` | Project-specific content, maintained by the agent and user |
| `ea_inputs\04_projects\_schema\process-view.schema.json` | Required fields and allowed values |
| `portal\backend\process_views.py` | Schema/reference/dependency/timing validation and safe HTML rendering |
| `portal\backend\builder.py` | Automatic discovery, project metadata, output path and navigation registration |

No separate template directory or per-project HTML copy is needed. The filename
`infrastructure-onboarding.yaml` is currently fixed by the collector; changing
`view.name` changes its displayed title, not its output route. Other process
filenames or multiple process pages per project require an explicit code change.

The [portal authoring guide](portal/README.md#project-process-views) contains a
complete minimal YAML example and field reference. The
[PSS2 source](ea_inputs/04_projects/operations/PSS2/design/infrastructure-onboarding.yaml)
is a worked example, not a baseline to copy unchanged.

### Authoring workflow

1. Confirm the audience, process boundary and intended use: management understanding,
   knowledge transfer or repeatable execution. Do not infer historical completion.
2. Define project roles, supporting services, ordered phases and activities with
   stable IDs. Include owners/contributors, prerequisites, outputs, completion
   criteria and request references. Add smaller steps only where helpful.
3. Author phase and activity timing separately. Ranges use business days and
   `basis: assumption` until evidence supports `ticket_measurement`. A fixed
   estimate uses equal `min_days`/`max_days`. Ranges must be finite, nonnegative
   and ordered; do not sum parallel activities or invent timestamps.
4. Preserve supplied ticket tables as `design\ticket-history.csv`, with columns
   `Ticket No`, `Purpose`, `System`, `Request Type`, `Assigned To`. Set
   `project.ticket_history_file` to its path relative to `ea_inputs` and use
   `record.ticket_numbers` (strings) to associate activities. The build resolves
   the source rows without an LLM; do not duplicate CSV details in YAML. Inline
   `record.tickets` is supported for projects without a CSV, but cannot coexist
   with `ticket_numbers` in the same record. Keep actual ticket assignment distinct
   from process ownership; do not invent URLs, status, dates or completion.
5. Separate reusable process rules from project observations. Observations cite
   a source and classification; optional inventory bindings cite an existing
   infrastructure inventory file and actual artifact IDs. Retain its snapshot
   timestamp, not a later processing/report date.
6. Replace every copied project-specific name, ticket, observation, inventory
   binding and estimate. PSS2's six stages and 60-day estimate are not defaults.
7. Review with the user, record iterations, build and inspect the actual portal
   shell. Preserve dependency gates, especially approval before production release.

### Shared presentation conventions

- Three bands: **Who is involved**, **What happens**, **What supports the work**.
- Grey duration band immediately below **What happens**. Use **Indicative** for
  estimates and distinguish ticket measurements; role and timing colors differ.
- Collapsed stages form the default overview. Expansion keeps the selectable
  stage title and group duration above indented, slimmer child cards in both lanes.
- Scroll the expanded stage into view, retain keyboard focus and respect reduced
  motion. Keep role/service highlights, smaller steps and deep links working.
- Put detailed ticket records in the selection panel; the overview shows all
  tickets and a selection filters to relevant activities.
- Use neutral headings such as **Process overview** and **Process details**.
  Do not restore marketing subtitles, introductory draft banners, visible draft
  badges or the removed **Source, confidence & identity** section. Preserve source
  metadata without implying approval.

## Portal sources and build

The portal build is deterministic, not an ingestion job. Its browser-facing output
is a static Vue shell, SVGs, JSON indexes and project iframe pages.

| Change | Edit here |
|---|---|
| Navigation, shell or project registration | `portal\backend\builder.py` |
| Diagram conversion or cross-view indexes | `portal\backend\converter.py`, `portal\backend\indexes.py` |
| Infrastructure inventory presentation | `portal\assets\infra-portal.html` |
| Application inventory presentation | `portal\assets\app-inventory-portal.html` |
| Application architecture diagram generation | `portal\backend\app_diagram.py` |
| Architecture Decisions presentation | `portal\assets\architecture-decisions.html` |
| Process presentation/interaction | `portal\assets\process-view.html` |
| Project content | Its inventory JSON, decision JSON or process YAML, not shared HTML |

Environment inventories live below `<project>\<env>\` as
`infra-inventory.<env>.json` and `app-inventory.<env>.json`. Raw
`runtime-inventory\` snapshots are evidence, not automatically a rendered page.
Imported `how-it-works.html` and `how-it-works.story.js` remain owned by their
originating project repository; fix there and re-import with the source revision.

Optional `type: json_inventory` specs under `ea_inputs\views\` supply project name,
stable `project_key`, domain and region. See the portal guide before creating one;
the `inventory` field points at the project folder relative to `ea_inputs`.

Run after relevant source/template/model/catalogue changes:

```powershell
. .\.venv\Scripts\Activate.ps1
$env:PYTHONIOENCODING = 'utf-8'
python portal\build.py
```

Serve `portal\dist\` locally over HTTP, bound to loopback:

```powershell
python -m http.server 8080 --bind 127.0.0.1 --directory portal\dist
```

Use the existing preview if one is already running. Hard-refresh after rebuilding.
This unauthenticated local server is for local review only. The build does not
publish, resynchronize SharePoint or refresh upstream inventories.

## Verification and deployment

- Use focused existing tests for changed behavior; tests live in `tests\ea\`.
  See [tests\README.md](tests/README.md) for the current suite, not historical
  root-level script names. Documentation-only changes do not need a portal build.
- For process changes, run `python -m pytest tests\ea\test_process_views.py`.
  For design-register changes, run
  `python -m pytest tests\ea\test_architecture_decisions.py`.
- Run the portal build for source/template changes and read warnings as well as
  its exit status. Invalid process/decision sources fail validation; invalid
  infrastructure inventories can be reported and skipped, so check registration.
- Inspect the page inside the full portal shell, not just standalone HTML.
  Check all stages fit, expansion scrolls correctly, headers persist, ticket
  filtering and deep links work, and nothing implies unverified completion.
- Check schema-valid examples and local documentation links when updating guides.
  Keep the root and portal README tables of contents aligned with their headings.
- Deployment is handled by `azure-pipelines.yml`, the root `Dockerfile` and
  `nginx.conf`: ACR builds the site image and Container Apps serves it with nginx.
  Production access is protected by platform EasyAuth; this is separate from
  source-document authorization.
- There is no local Docker engine in the current workflow. Do not require a local
  Docker check, trigger Azure DevOps, deploy, push or commit without authorization.
  A successful local build is not a deployment. Main-branch changes may trigger CI.

## Azure DevOps operations

Use the tools actually exposed by the configured server. PM implementations are
in `src\pm\tools\mcp_server.py`; do not assume all are registered by the unified
entry point without checking `/mcp`.

- Queries: `get_work_items`, `get_pull_requests`, `get_projects`,
  `get_repositories`, `get_readme`.
- Batch analysis: `batch_project_overview`, `batch_work_item_queries`,
  `batch_pull_requests`; use when scope genuinely covers multiple queries/projects.
- Writes: `create_work_item`, `update_work_item`; confirm intended project, type,
  fields and user authorization before changing remote data.
- Extract requested time ranges, filters and environments. Report actual tool
  failures or missing permissions; do not substitute invented findings.
