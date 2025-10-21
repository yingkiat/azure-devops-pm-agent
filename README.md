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

## Available MCP Tools

### EA Tools (5)
- `ea_discover` - Extract apps, capabilities, relationships from text
- `ea_discover_directory` - Batch process entire directories with smart batching
- `ea_generate_archi` - Generate ArchiMate CSV/XML for Archi tool
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

**Total: 15 MCP Tools**

---

## Architecture

### Single Source of Truth: `archi_inputs/`
All EA data stored in ArchiMate format:
- `elements.csv` - Applications, capabilities, processes
- `relations.csv` - Serving, Flow, Composition relationships
- `properties.csv` - Criticality, maturity, strategic importance
- `model.xml` - Open Group ArchiMate 3.0 Model Exchange

**Import to Archi:** File → Open → Model from File → `archi_inputs/model.xml`

### Prompt-Driven Intelligence
Business logic externalized to `prompts/` directory:
- `prompts/ea/ea_discovery.md` - EA extraction logic
- `prompts/pm/classify_business_request.md` - PM classification

Easy iteration without code changes.

### Data Flow
```
Natural Language → Claude Code MCP → Unified Server → PM/EA Modules → Azure DevOps/ArchiMate
```

---

## Development

### Testing
```bash
python test_mcp_server.py         # Verify MCP integration
python test_archimate_provider.py  # Test ArchiMate data loading
```

### File Structure
```
src/
├── mcp_server.py           # Unified MCP server
├── pm/                     # Project management modules
├── ea/                     # Enterprise architecture modules
└── shared/                 # Shared utilities

prompts/
├── ea/                     # EA discovery prompts
└── pm/                     # PM classification prompts

archi_inputs/               # ArchiMate model (single source of truth)
├── elements.csv
├── relations.csv
├── properties.csv
└── model.xml
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
- **[.claude_mcp.json](.claude_mcp.json)** - MCP configuration example
- **[MVP5 Implementation](docs/ea/MVP5_Implementation_Complete.md)** - Context-aware discovery + smart batching
- **[EA Documentation](docs/ea/)** - Full EA implementation details

---

## Legacy CLI

Original CLI commands preserved in `src/cli/main.py` for backward compatibility, but Claude Code MCP interface is now the recommended approach.

---

## License

MIT
