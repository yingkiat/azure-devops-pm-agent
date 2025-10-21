# Testing Guide - Azure DevOps PM/EA Agent

## Current Architecture (MCP-Based)

**Integration Model:** Claude Code MCP interface (not CLI)
**Primary Interface:** Claude Code conversations
**Test Strategy:** Validate MCP tools and underlying logic

---

## Test Organization

### Root Level Tests (Quick Validation)

**Active Tests:**
```bash
# MCP server validation
python test_mcp_server.py

# ArchiMate data provider
python test_archimate_provider.py

# EA batch discovery with smart caching
python test_batch_discovery.py

# Gemini visual diagrams
python test_gemini_diagrams.py

# MVP6 reference implementation (correct architecture)
python test_mvp6_simplified.py
```

**Obsolete Tests (Removed):**
- ~~`test_mvp4_conversational.py`~~ - Old MVP4 architecture
- ~~`test_mvp5_context_aware.py`~~ - Old MVP5 test
- ~~`test_mvp6_views.py`~~ - Wrong architecture (hardcoded parsing)
- ~~`test_csv_discovery.py`~~ - Redundant
- ~~`test_single_csv.py`~~ - Redundant

### tests/ Directory (Component Tests)

**Core System Tests (Pytest):**
```bash
# High-priority test suite
pytest -m high_priority

# Specific component tests
pytest tests/test_mcp_integration.py
pytest tests/test_ai_orchestrator.py
pytest tests/test_context_persistence.py
pytest tests/test_insights_engine.py
```

**EA Tests:**
```bash
pytest tests/ea/test_ea_discovery.py
pytest tests/ea/test_integration.py
pytest tests/ea/test_storage.py
pytest tests/ea/test_matrix_scenarios.py
```

---

## Quick Start Testing

### 1. MCP Server Health Check
```bash
source .venv/Scripts/activate  # Windows: .venv/Scripts/activate
python test_mcp_server.py
```

**Expected Output:**
- ✅ All imports successful
- ✅ Unified server initialized
- ✅ PM tools registered (~10 tools)
- ✅ EA tools registered (~4 tools)
- ✅ Configuration valid

### 2. MVP6 Reference (Simplified Architecture)
```bash
python test_mvp6_simplified.py
```

**Validates:**
- ✅ Claude Code lists available elements (MCP tool)
- ✅ Claude Code writes YAML specs **directly** (no MCP tool)
- ✅ Claude Code edits YAML specs **directly** (no MCP tool)
- ✅ Claude Code generates views.csv (MCP tool)

**Key Principle:** No hardcoded parsing - LLM has full control over YAML content.

### 3. EA Batch Discovery
```bash
python test_batch_discovery.py
```

**Features:**
- Smart caching (skips unchanged files)
- Batch processing (reduces LLM calls)
- Content validation (ensures outputs match inputs)
- Incremental discovery (processes only new/modified files)

---

## Environment Setup

### Required Environment Variables (.env)

```bash
# Azure DevOps (Required for PM tools)
AZDO_ORG_URL=https://dev.azure.com/your-org
AZDO_PROJECT=your-project
AZDO_PAT=your-personal-access-token
AZDO_WIKI_NAME=your-wiki

# Azure OpenAI (Required for AI features)
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com
AZURE_OPENAI_KEY=your-key
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Gemini (Optional - for visual diagrams)
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-2.5-flash-image-preview
GEMINI_DISABLE_SSL_VERIFY=true  # For corporate firewalls
```

### Installation
```bash
python -m venv .venv
source .venv/Scripts/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

---

## Usage Workflows

### EA Discovery Workflow

**1. Batch Discovery from Directory:**
```bash
python test_batch_discovery.py
```
- Processes all files in `ea_inputs/`
- Smart caching (only processes new/modified files)
- Outputs to `archi_inputs/`

**2. Single File Discovery:**
```python
from src.mcp_server import UnifiedMCPServer
server = UnifiedMCPServer()
result = await server._ea_discover("Microsoft Dynamics integrates with QAD EE")
```

**3. Generate ArchiMate Files:**
```python
result = await server._ea_generate_archi()
# Creates: archi_inputs/elements.csv, relations.csv, properties.csv, model.xml
```

**4. Import to Archi Tool:**
```
File → Open → Model from File → archi_inputs/model.xml
```

### View Generation Workflow (MVP6)

**1. Claude Code lists available elements:**
```python
result = await server._ea_list_available_elements()
# Returns: List of applications, capabilities from archi_inputs/
```

**2. Claude Code writes YAML spec directly:**
```python
import yaml
spec = {
    'view': {'name': 'CRM Integration', ...},
    'elements': {'include': [{'name': 'Microsoft Dynamics (ANZ)'}, ...]},
    ...
}
with open('ea_inputs/views/crm_integration.yaml', 'w') as f:
    yaml.dump(spec, f)
```

**3. Claude Code generates views.csv:**
```python
result = await server._ea_generate_views_from_specs()
# Creates: archi_inputs/views.csv (deterministic)
```

### PM Workflow

**Using MCP tools via Claude Code:**
- User: "What's blocking our release?"
- Claude Code calls: `get_work_items(wiql="...")`
- Claude Code analyzes and responds

**Available PM Tools:**
- `get_work_items` - Execute WIQL queries
- `create_work_item` - Create epics, features, stories
- `update_work_item` - Update work item fields
- `get_pull_requests` - Query PRs
- `batch_project_overview` - Multi-project analysis
- `batch_work_item_queries` - Parallel WIQL execution

---

## Testing Strategy

### Level 1: Tool Registration (No API calls)
```bash
python test_mcp_server.py
```
- Validates: Tool registration, configuration, imports

### Level 2: Component Logic (Minimal API calls)
```bash
pytest tests/ea/test_ea_discovery.py
```
- Validates: Discovery logic, ArchiMate export, data providers

### Level 3: Integration (Real API calls)
```bash
python test_batch_discovery.py
pytest -m high_priority
```
- Validates: End-to-end workflows, Azure DevOps integration

### Level 4: MCP Integration (Via Claude Code)
- Manual testing via Claude Code conversations
- Validates: Natural language → tool selection → execution

---

## Troubleshooting

### MCP Server Issues

**"ImportError: cannot import name 'UnifiedMCPServer'"**
```bash
# Check Python path
export PYTHONPATH=.  # Linux/Mac
set PYTHONPATH=.     # Windows CMD
```

**"Tool not registered"**
```bash
# Verify in test_mcp_server.py output
# Tools are registered via @mcp.tool() decorators
```

### EA Discovery Issues

**"No elements discovered"**
- Check `prompts/ea/ea_discovery.md` for discovery instructions
- Verify Azure OpenAI credentials
- Check input file format (text or CSV)

**"CSV attributes not preserved"**
- ✅ Fixed in MVP5: LLM now preserves ALL CSV columns
- Verify in `archi_inputs/properties.csv`

### View Generation Issues

**"No elements selected for view"**
- YAML spec has empty `elements.include` list
- Claude Code should add element names to YAML directly

**"Views.csv not deterministic"**
- ✅ Fixed in MVP6: YAML specs ensure deterministic output
- Same YAML spec always produces same views.csv

---

## Success Metrics

After testing, you should see:

**EA Discovery:**
- ✅ Elements extracted from text/CSV inputs
- ✅ ALL CSV columns preserved in properties.csv
- ✅ ArchiMate model.xml ready for Archi import
- ✅ Smart caching reduces redundant LLM calls

**View Generation:**
- ✅ YAML specs created in ea_inputs/views/
- ✅ Deterministic views.csv output
- ✅ Claude Code has full control (no hardcoded parsing)

**PM Tools:**
- ✅ MCP tools registered and callable
- ✅ Azure DevOps API integration working
- ✅ Batch operations performant (<5s)

---

## Documentation

- `docs/MVP6_STATUS.md` - MVP6 implementation status
- `docs/CLEANUP_GUIDE.md` - Cleanup automation
- `docs/current_status.md` - System status
- `docs/ARCHITECTURE.md` - Architecture overview
- `CLAUDE.md` - Claude Code integration guide (root)

---

## Next Steps

1. **Test MCP Integration:** Verify all tools via `test_mcp_server.py`
2. **Test EA Discovery:** Run `test_batch_discovery.py` on sample data
3. **Test MVP6 Workflow:** Run `test_mvp6_simplified.py` for reference
4. **Use with Claude Code:** Test natural language workflows
5. **Import to Archi:** Validate ArchiMate model.xml import
