# Azure DevOps PM/EA Agent

Enterprise architecture discovery, Azure DevOps project intelligence and a static
EA Portal, operated through GitHub Copilot CLI.

The repository combines an ArchiMate model, project inventories, architectural
decision registers and interactive project process views. Ingestion and portal
rendering are separate operations.

## Contents

- [Documentation](#documentation)
- [Repository structure](#repository-structure)
- [Setup](#setup)
- [Ingestion workflows](#ingestion-workflows)
- [Diagrams and project views](#diagrams-and-project-views)
- [Build and preview the portal](#build-and-preview-the-portal)
- [Development and deployment](#development-and-deployment)

## Documentation

| Guide | Purpose |
|---|---|
| [AGENTS.md](AGENTS.md) | Canonical Copilot operating rules for ingestion, design parsing, diagrams and portal work |
| [Portal README](portal/README.md) | HTML templates, project YAML/JSON authoring, navigation, build and deployment |
| [Decision extraction prompt](prompts/ea/architecture_decisions.md) | Source selection, document parsing and architectural-point extraction |
| [Tests README](tests/README.md#current-suite) | Current tests and execution |
| [EA implementation notes](docs/ea/) | Feature history and implementation references; consult current code/schema for supported behavior |

## Repository structure

```text
ea_inputs\
  01_company_context\         Business context
  02_IT_systems\              System descriptions, CMDB export, Application Catalogue
  03_global_standards\        Enterprise standards
  04_projects\
    _schema\                 Project data contracts
    <domain>\<project>\
      design\                Architecture decisions and process YAML
      <env>\                 Machine-generated/imported inventories
  views\                     Diagram specs and project metadata overrides
archi_inputs\                Generated canonical ArchiMate CSV/XML
ea_diagrams\                 Diagram artifacts
ea_outputs\                  Discovery and presentation outputs
prompts\                     Extraction/generation guidance
portal\assets\               Shared project-page HTML templates
portal\backend\              Static-site build and rendering
portal\dist\                 Generated site
src\                        MCP server, EA, PM and shared modules
tests\                      Automated tests
```

The CMDB export, catalogue and project inventories are distinct evidence sources.
Similar names do not prove they describe the same application or deployment.

## Setup

### Python environment

Use Python 3.11 to match the portal build image. From the repository root in
Windows PowerShell:

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
$env:PYTHONIOENCODING = 'utf-8'
python -m pip install -e ".[test]"
```

Reactivate the existing environment in each new shell; do not recreate or reinstall
it for every task. Dependencies are declared in `pyproject.toml`.

### Service configuration

The MCP application loads settings from a local, Git-ignored `.env`:

```dotenv
AZDO_ORG_URL=https://dev.azure.com/your-org
AZDO_PROJECT=your-project
AZDO_PAT=your-token
AZDO_WIKI_NAME=your-wiki
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_KEY=your-key
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_OPENAI_DEPLOYMENT=your-deployment
GEMINI_API_KEY=your-key
```

Azure DevOps tools use the PAT; EA discovery uses Azure OpenAI. Gemini is used by
image features. The current shared settings class requires `GEMINI_API_KEY` at
MCP startup even if those features are not requested. See `src\utils\settings.py`
for additional settings. Do not disable TLS verification as a default workaround.

The static portal build does not need these service credentials.

### Copilot CLI and MCP

Start GitHub Copilot CLI in the repository root. `AGENTS.md` supplies the operating
instructions. Use `/mcp` to add or inspect the local stdio server:

| Setting | Value |
|---|---|
| Name | `pm-ea-agent` |
| Command | Absolute path to this repository's `.venv\Scripts\python.exe` |
| Arguments | `-m src.mcp_server` |
| Launch directory | Repository root; launch Copilot there |
| Python path, if needed | Set `PYTHONPATH` to the absolute repository `src` directory and repository root, separated by `;` on Windows |

Use the tools actually shown by the configured server, not a fixed tool count or
an old client's naming prefix. EA declarations are in `src\mcp_server.py`; PM tools
are implemented in `src\pm\tools\mcp_server.py`. Verify PM exposure rather than
assuming every implementation is registered by the unified server.

After changing server modules, restart the configured MCP process, or restart
Copilot CLI. Python imports are cached by that persistent process.

## Ingestion workflows

| Input and objective | Workflow | Maintained result |
|---|---|---|
| System descriptions: text, Markdown, CSV, Excel | MCP `ea_discover_directory`; inspect processed/skipped files and errors | `archi_inputs\` model, discovery outputs and local tracking |
| A supplied system description | MCP `ea_discover` | Incremental model update when requested |
| Architecture images/slides | MCP `ea_ingest_images`, review extracted text, then directory discovery | Text evidence and model updates |
| Application Catalogue properties | MCP `ea_import_catalogue` | Name-matched model properties; catalogue values win on conflict |
| Selected project design document | Agent-guided extraction using the decision prompt | `<project>\design\architecture-decisions.json` |
| Supplied project ticket table | Save `design\ticket-history.csv`; map numbers in process YAML | CSV-backed ticket history resolved during portal build, without an LLM |
| Project deployment/build output | Import the project's inventory contract and provenance | `<project>\<env>\` inventories, independently rendered by the portal |

Directory discovery handles `.xlsx` conversion internally. Do not pre-convert
Excel or assume bulk discovery parses DOCX/PPTX files. Narrow the source directory
to the requested scope; do not reset the model or caches to force an update.

Design documents remain in their Teams/SharePoint-backed OneDrive folder. A local
`design\sources.local.yaml` selects the exact folder and baseline file. Compare
its SHA-256 before parsing; unchanged content can reuse the existing register.
This is agent-guided, not an automatic synchronization or semantic-cache service.

The architectural output is decisions, constraints and open questions with source
references, not a rewritten document. Generic discovery excludes project `design`
folders. See [AGENTS.md](AGENTS.md#project-design-ingestion) for the complete workflow.

For Archi views, use `ea_generate_views_from_specs`, review validation, and finalize
with `ea_finalize_views` when required. Import `archi_inputs\model.xml` into Archi.
Use `ea_get_data_summary` to inspect the model.

## Diagrams and project views

Architecture diagrams use model data and YAML specs under `ea_inputs\views\`.
Follow the `create-diagram` skill to establish intent, review the spec, generate
and inspect the result. Use explicit selections and view-specific overrides
without changing source-model facts to fit the presentation.

Project views use independent content and shared HTML templates:

| View | Project source | Shared page template |
|---|---|---|
| Architecture Decisions | `design\architecture-decisions.json` | `portal\assets\architecture-decisions.html` |
| Infrastructure Onboarding | `design\infrastructure-onboarding.yaml` | `portal\assets\process-view.html` |
| Infrastructure Inventory | `<env>\infra-inventory.<env>.json` | `portal\assets\infra-portal.html` |
| Application Inventory | `<env>\app-inventory.<env>.json` | `portal\assets\app-inventory-portal.html` |

For the process format, each project authors its roles, stages, activities,
durations and tickets in YAML; it does not copy or customize the HTML.
The [portal guide](portal/README.md#project-process-views) explains the contract
and includes a complete minimal example.

## Build and preview the portal

With the virtual environment activated:

```powershell
python portal\build.py
python -m http.server 8080 --bind 127.0.0.1 --directory portal\dist
```

Open <http://127.0.0.1:8080/>. Rebuild and hard-refresh after source changes.
The local server has no authentication; keep it bound to loopback.

The build reads curated sources, diagrams, model files and the Application
Catalogue workbook. It does not call an LLM, ingest documents, refresh remote
inventories or deploy the site. Never edit generated `portal\dist\` files.

## Development and deployment

Run the smallest relevant test set, for example:

```powershell
python -m pytest tests\ea\test_process_views.py tests\ea\test_architecture_decisions.py
```

Use `python -m pytest` for the default suite when broader verification is needed.
Some legacy integration tests are skipped; they do not prove live MCP coverage.

Deployment is through [azure-pipelines.yml](azure-pipelines.yml), the root
[Dockerfile](Dockerfile) and [nginx.conf](nginx.conf). Azure Container Registry
builds the image and Azure Container Apps serves the static site behind EasyAuth.
No local Docker engine is required. Do not trigger deployment as part of a local
preview. See the [portal deployment guide](portal/README.md#deployment).
