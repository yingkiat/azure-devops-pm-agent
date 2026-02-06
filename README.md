# Azure DevOps PM/EA Agent

**Natural language interface for Azure DevOps project management and enterprise architecture**

Transform Azure DevOps workflows with AI-powered natural language interaction via Claude Code. Discover architecture, manage work items, and analyze project health—all through conversation.

---

## ✨ Key Features

### 🏗️ Enterprise Architecture Discovery
- **Context-Aware Discovery** - Incremental model building with entity resolution (no duplicates)
- **Batch Processing** - Process entire directories with smart batching (70-90% token savings)
- **Archi Tool Integration** - Direct import via Open Group ArchiMate Model Exchange XML
- **Visual Diagrams** - Mermaid code and Gemini-powered PNG images
- **Zero Maintenance** - No hardcoded mappings, pure prompt-driven analysis
- **Enterprise Scale** - Validated for 10,000+ files with granular caching

### 📊 Project Management Intelligence
- **Natural Language Queries** - "Show critical bugs" → Automatic WIQL generation
- **Batch Analytics** - Multi-project health analysis with 55% performance improvement
- **Work Item Management** - Create epics, features, stories from conversation
- **Repository Intelligence** - AI-powered work item routing to correct repos

### 🤖 Claude Code MCP Integration
- **15 Available Tools** - PM operations + EA discovery seamlessly integrated
- **No Command Syntax** - Pure natural language interaction
- **Context Awareness** - Claude Code selects appropriate tools automatically
- **Interactive Approvals** - Safety gates for work item creation

---

## Quick Start

### 1. Install
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

### 2. Configure `.env`
```bash
# Azure DevOps
AZDO_ORG_URL=https://dev.azure.com/your-org
AZDO_PROJECT=your-project
AZDO_PAT=your-token
AZDO_WIKI_NAME=your-wiki

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com
AZURE_OPENAI_KEY=your-key
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Gemini (optional - for visual diagrams)
GEMINI_API_KEY=your-key
```

### ⚠️ CRITICAL: MCP Server Restart Required for Code Changes

The MCP server runs as a **persistent stdio process** that caches Python modules on startup. Any code changes will **NOT take effect** until you restart the process.

**To Apply Code Changes:**
1. Close Claude Code completely (exit the CLI)
2. Reopen Claude Code to restart the MCP server
3. Re-run your discovery/processing commands

This applies to changes in:
- `src/core/file_monitor.py` (file detection patterns)
- `src/ea/ea_discovery.py` (discovery logic)
- `src/mcp_server.py` (processing pipelines)
- Any shared modules

Skipping this step will execute old cached code.

### 3. Register MCP Server

**Option A: Global Registration (Recommended)**
```bash
# From project root directory
claude mcp add --transport stdio pm-ea-agent --env PYTHONPATH=. -- .venv/Scripts/python.exe -m src.mcp_server
```

**Option B: Local Project Configuration**
Create `.claude_mcp.json` in project root:
```json
{
  "mcpServers": {
    "pm-ea-agent": {
      "command": ".venv/Scripts/python.exe",
      "args": ["-m", "src.mcp_server"],
      "env": {"PYTHONPATH": "."}
    }
  }
}
```

**How MCP Works:**
- MCP servers communicate via **stdio** (stdin/stdout)
- Claude Code spawns your command (e.g., `.venv/Scripts/python.exe -m src.mcp_server`)
- That Python process runs continuously and communicates with Claude Code
- Claude Code manages starting/stopping automatically

**Global vs Local:**
- **Global** (`~/.claude.json`) - Available in all projects, easier to manage
- **Local** (`.claude_mcp.json`) - Project-specific, committed to repo

**Verify Registration:**
```bash
claude mcp list  # Should show "pm-ea-agent"
```

### 4. Start Using
Open Claude Code in this directory. All 15 tools are now available via natural language!

---

## Usage Examples

### Enterprise Architecture - Single Discovery
```
You: "Microsoft Dynamics CRM integrates with QAD EE for purchase order automation"

Claude Code: [Uses ea_discover tool]
✓ Discovered: 2 applications, 1 capability, 1 relationship
✓ Generated ArchiMate model: archi_inputs/model.xml
✓ Ready for Archi tool import
```

### Enterprise Architecture - Batch Discovery
```
You: "Process all system descriptions in ea_inputs/"

Claude Code: [Uses ea_discover_directory tool]
✅ Created 1 batches from 8 files
   OpenAI calls: 1 (vs 8 without batching)
   Savings: 7 calls (88%)

✓ Discovered: 8 applications, 10 capabilities, 10 relationships
✓ Smart batching: 70-90% token savings
✓ Incremental context: No duplicates across files
```

### Project Management
```
You: "What's blocking our data platform release?"

Claude Code: [Uses get_work_items + batch_project_overview]
Found 3 critical blockers:
1. Auth timeout bug (unassigned) - 8 days old
2. API sync failure - assigned to Bob Smith
3. Memory leak in data processor - needs investigation
```

### Diagram Generation
```
You: "Generate capability matrix diagram from our EA data"

Claude Code: [Uses ea_generate_mermaid]
✓ Generated: ea_diagrams/capability_matrix.mermaid
```

---

## View Specification Workflow

YAML view specs are **iterative storyboards** - expect to refine through generate-review-refine cycles.

### Three Core Principles

| Principle | Description |
|-----------|-------------|
| **1. Iterative Storyboard** | v1 → v1.1 → v2 is normal. Document iterations. Don't aim for perfection on first draft. |
| **2. Explicit > Query** | Prefer `name:` with explicit elements over `where:` property filters. Queries are fragile. |
| **3. View = Interpretation** | Data is truth; view spec interprets it. Use `override:` to align grouping with narrative. |

### Example - Property Override

When data says H2 but story needs H1:

```yaml
elements:
  include:
    - name: "SPT Applications"
      override:
        Horizon: "H1"    # Override: legacy chain belongs in AS-IS
```

See [docs/ea/VIEW_SPEC_WORKFLOW.md](docs/ea/VIEW_SPEC_WORKFLOW.md) for full documentation.

---

## Available MCP Tools

### EA Tools (6)
- `ea_discover` - Extract apps, capabilities, relationships from text
- `ea_discover_directory` - Batch process entire directories with smart batching
- `ea_generate_archi` - Generate ArchiMate CSV/XML for Archi tool
- `ea_generate_presentation_diagram` - Generate slide-ready diagrams from YAML view specs
- `ea_generate_mermaid` - Create technical documentation diagrams
- `ea_get_data_summary` - Get EA knowledge base overview

### PM Tools (10)
- `get_work_items` - Execute WIQL queries
- `create_work_item` - Create epics, features, stories, tasks
- `update_work_item` - Update work item fields
- `get_pull_requests` - Query PRs across repositories
- `get_projects` - List accessible projects
- `get_repositories` - List repos in a project
- `get_readme` - Fetch repository README
- `batch_project_overview` - Multi-project analysis
- `batch_work_item_queries` - Parallel query execution
- `batch_pull_requests` - Bulk PR queries

**Total: 16 MCP Tools**

---

## Architecture

### EA CMDB (Configuration Management Database)

The system maintains a clean **input → process → output** flow:

**INPUTS:**
- `ea_inputs/` - System descriptions (Markdown, CSV, Excel) maintained by users
  - `01_company_context/` - Organizational information
  - `02_IT_systems/` - System descriptions by domain
  - `03_global_standards/` - Enterprise policies and standards
  - `views/` - YAML view specifications for diagrams

**CMDB (Single Source of Truth):**
- `archi_inputs/` - Canonical ArchiMate model (auto-generated, read-only)
  - `elements.csv` - Applications, capabilities, processes
  - `relations.csv` - Serving, Flow, Composition relationships
  - `properties.csv` - Criticality, maturity, strategic importance, domain, lifecycle
  - `model.xml` - Open Group ArchiMate 3.0 Model Exchange
  - `views.csv` - View definitions
  - `property_schema.yaml` - Property definitions

**OUTPUTS:**
- `ea_diagrams/` - Presentation-ready diagrams (auto-generated)
  - `.drawio` files - Open in draw.io, export to PNG/PDF for slides

**Workflow:**
```
ea_inputs/*              (User describes systems)
  ↓ ea_discover_directory()
archi_inputs/*           (Canonical model)
  ↓ ea_generate_presentation_diagram()
ea_diagrams/*.drawio     (Presentation diagrams)
  ↓ (refinement in draw.io)
*.png/*.pdf              (Final deliverables)
```

### Prompt-Driven Intelligence
Business logic externalized to `prompts/` directory:
- `prompts/ea/ea_discovery.md` - EA extraction logic
- `prompts/pm/classify_business_request.md` - PM classification

Easy iteration without code changes.

### Property Normalization (Frequently Modified)

Source data uses inconsistent property names. The `PROPERTY_NORMALIZATION` mapping in `src/ea/archi_export.py:25` standardizes them:

```python
PROPERTY_NORMALIZATION = {
    'Business Unit(s)': 'Domain',
    'Business Unit': 'Domain',
    'Dept': 'Domain',
    'Location': 'Region',
    'Geography': 'Region',
    'Status': 'Lifecycle Status',
    'Activity Status': 'Lifecycle Status',
    # ... add your mappings here
}
```

**When to modify:** Add entries when source data uses different terminology than your YAML view specs expect. For example, if your Excel says "Dept" but your views filter by `Domain`, add the mapping.

**After modifying:** Restart Claude Code (MCP server caches modules on startup).

### Data Flow
```
Natural Language → Claude Code MCP → Unified Server → PM/EA Modules → Azure DevOps/ArchiMate
```

---

## Development

### Testing

**Enterprise Architecture Tests** (5 test modules in `tests/ea/`)
- `test_ea_discovery.py` - EA Discovery engine validation
- `test_storage.py` - CMDB storage layer (CSV/XML)
- `test_matrix_scenarios.py` - EA matrix filtering and scenarios
- `test_integration.py` - End-to-end discovery → CMDB workflow
- `test_runner.py` - Test orchestration

**Run Tests:**
```bash
pytest tests/ea/                         # Run all EA tests
pytest tests/ea/test_ea_discovery.py     # Run specific test
```

**PM/Integration Testing:**
- Test MCP tools directly via Claude Code
- No separate test suites (Claude Code is the test interface)

### File Structure
```
ea_inputs/                      # INPUT: System descriptions (user-maintained)
├── 01_company_context/
├── 02_IT_systems/
├── 03_global_standards/
└── views/                       # YAML view specifications

archi_inputs/                   # CMDB: Canonical ArchiMate model (auto-generated)
├── elements.csv
├── relations.csv
├── properties.csv
├── model.xml
├── views.csv
└── property_schema.yaml

ea_diagrams/                    # OUTPUT: Presentation diagrams (auto-generated)
└── *.drawio                     # Open in draw.io, export to PNG/PDF

src/
├── mcp_server.py               # Unified MCP server
├── pm/                         # Project management modules
├── ea/                         # Enterprise architecture modules
│   ├── ea_discovery.py         # Discovery engine
│   ├── archi_export.py         # ArchiMate generation
│   ├── presentation_diagram_generator.py  # Slide-ready diagrams
│   ├── drawio_export.py        # Draw.io XML generation
│   └── view_builder.py         # YAML view processing
└── shared/                     # Shared utilities

prompts/
├── ea/                         # EA discovery prompts
└── pm/                         # PM classification prompts

tests/
├── ea/                         # Enterprise architecture tests
└── ...                         # Other test modules
```

---

## Key Design Principles

1. **Natural Language First** - No command syntax or WIQL knowledge required
2. **Prompt-Driven** - Intelligence in prompts, not hardcoded rules
3. **Context-Aware** - Entity resolution and incremental model building across sessions
4. **ArchiMate Native** - Industry standard EA modeling with full relationship support
5. **Two-Layer Architecture** - LLM reasoning + deterministic execution
6. **Enterprise Scale** - Smart batching and granular caching for 10,000+ files
7. **Cost Optimized** - 70-90% token reduction through intelligent batching
8. **Zero Maintenance** - Pure AI analysis, no manual mapping maintenance

---

## Documentation

- **[CLAUDE.md](CLAUDE.md)** - Complete Claude Code integration guide
- **[View Spec Workflow](docs/ea/VIEW_SPEC_WORKFLOW.md)** - Iterative diagram creation principles
- **[.claude_mcp.json](.claude_mcp.json)** - MCP configuration example
- **[MVP5 Implementation](docs/ea/MVP5_Implementation_Complete.md)** - Context-aware discovery + smart batching
- **[EA Documentation](docs/ea/)** - Full EA implementation details

---

## Legacy CLI

Original CLI commands preserved in `src/cli/main.py` for backward compatibility, but Claude Code MCP interface is now the recommended approach.

---

## License

MIT
