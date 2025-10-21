# File Structure Documentation

This document explains the purpose and status of every Python file in the project.

## 🆕 NEW ARCHITECTURE (Phase 1 Complete)

### Core Infrastructure (`src/core/`)
**Status: ✅ Complete - Ready for Production**

| File | Purpose | Status |
|------|---------|--------|
| `src/core/__init__.py` | Core module exports | ✅ Complete |
| `src/core/interfaces/__init__.py` | Interface exports | ✅ Complete |
| `src/core/interfaces/orchestrator_interface.py` | Common contract for PM/EA orchestrators | ✅ Complete |
| `src/core/interfaces/tool_interface.py` | Common contract for tools | ✅ Complete |
| `src/core/base_orchestrator.py` | Base functionality for orchestrators | ✅ Complete |
| `src/core/persona_detector.py` | Detects PM vs EA requests | ✅ Complete |

### Shared Components (`src/shared/`)
**Status: ✅ Complete - Ready for Production**

| File | Purpose | Status |
|------|---------|--------|
| `src/shared/__init__.py` | Shared module exports | ✅ Complete |
| `src/shared/common_models.py` | Cross-persona data models | ✅ Complete |

## 🔄 LEGACY ARCHITECTURE (To Be Migrated)

### AI Orchestrator (`src/ai_orchestrator/`)
**Status: 📋 To be migrated to PM module**

| File | Purpose | Migration Plan |
|------|---------|----------------|
| `src/ai_orchestrator/__init__.py` | Legacy exports | 🔄 Move to `src/pm/` |
| `src/ai_orchestrator/orchestrator.py` | Main AI orchestrator | 🔄 Becomes `src/pm/orchestrator.py` |
| `src/ai_orchestrator/context_manager.py` | Session memory | 🔄 Move to `src/pm/context/` |
| `src/ai_orchestrator/insights_engine.py` | Business intelligence | 🔄 Move to `src/pm/tools/` |
| `src/ai_orchestrator/query_builder.py` | Smart WIQL generation | 🔄 Move to `src/pm/tools/` |
| `src/ai_orchestrator/wiki_reporter.py` | Wiki integration | 🔄 Move to `src/pm/context/` |
| `src/ai_orchestrator/work_item_classifier.py` | Work item classification | 🔄 Move to `src/pm/tools/` |
| `src/ai_orchestrator/interactive_planner.py` | Interactive planning | 🔄 Move to `src/pm/tools/` |
| `src/ai_orchestrator/repository_intelligence.py` | Repo analysis | 🔄 Move to `src/shared/` |
| `src/ai_orchestrator/repository_cache.py` | Repo caching | 🔄 Move to `src/shared/` |

### MCP Server (`src/mcp_server/`)
**Status: 📋 To be migrated to PM module**

| File | Purpose | Migration Plan |
|------|---------|----------------|
| `src/mcp_server/__init__.py` | MCP exports | 🔄 Move to `src/pm/tools/` |
| `src/mcp_server/server.py` | Azure DevOps MCP server | 🔄 Move to `src/pm/tools/mcp_server.py` |
| `src/mcp_server/batch_operations.py` | Batch API operations | 🔄 Move to `src/pm/tools/` |

### CLI (`src/cli/`)
**Status: 🔄 Partially migrated, needs updates**

| File | Purpose | Migration Status |
|------|---------|------------------|
| `src/cli/main.py` | Legacy CLI commands | 🔄 Keep for plan generation |
| `src/cli/ai_cli.py` | Natural language CLI | 🔄 Update to use persona router |

## ✅ STABLE COMPONENTS (No Migration Needed)

### Agent (`src/agent/`)
**Status: ✅ Keep as-is for plan generation**

| File | Purpose | Status |
|------|---------|--------|
| `src/agent/__init__.py` | Agent exports | ✅ Keep |
| `src/agent/agent.py` | LLM plan generation | ✅ Keep |
| `src/agent/plan_schema.py` | Plan data structures | ✅ Keep |
| `src/agent/sync_engine.py` | Azure DevOps sync | ✅ Keep |
| `src/agent/id_mapping.py` | External key management | ✅ Keep |

### DevOps Gateway (`src/devops_gateway/`)
**Status: ✅ Keep as-is - shared infrastructure**

| File | Purpose | Status |
|------|---------|--------|
| `src/devops_gateway/__init__.py` | Gateway exports | ✅ Keep |
| `src/devops_gateway/connection.py` | Azure DevOps connection | ✅ Keep |
| `src/devops_gateway/work_items.py` | Work item operations | ✅ Keep |
| `src/devops_gateway/wiki.py` | Wiki operations | ✅ Keep |
| `src/devops_gateway/wiki_setup.py` | Wiki setup utilities | ✅ Keep |

### Utils (`src/utils/`)
**Status: ✅ Keep as-is - shared utilities**

| File | Purpose | Status |
|------|---------|--------|
| `src/utils/openai_client.py` | OpenAI client setup | ✅ Keep |
| `src/utils/json_fence.py` | JSON extraction utility | ✅ Keep |
| `src/utils/settings.py` | Environment configuration | ✅ Keep |
| `src/utils/config.py` | Path configuration | ✅ Keep |

## 🧪 TEST FILES

### Tests (`tests/`)
**Status: 📋 To be reorganized**

| File | Purpose | Migration Plan |
|------|---------|----------------|
| `tests/test_ai_orchestrator.py` | AI orchestrator tests | 🔄 Move to `tests/pm/` |
| `tests/test_smart_queries.py` | Query builder tests | 🔄 Move to `tests/pm/` |
| `tests/test_batch_operations.py` | Batch operations tests | 🔄 Move to `tests/pm/` |
| `tests/test_insights_engine.py` | Business intelligence tests | 🔄 Move to `tests/pm/` |
| `tests/test_context_persistence.py` | Context manager tests | 🔄 Move to `tests/pm/` |
| `tests/test_repository_intelligence.py` | Repository analysis tests | 🔄 Move to `tests/shared/` |
| `tests/test_ai_system.py` | End-to-end tests | ✅ Keep - system tests |
| `tests/demo_wiki_flow.py` | Demo workflow | ✅ Keep - demo |
| `tests/test_manual_wiki.py` | Manual wiki tests | ✅ Keep - manual testing |
| `tests/cleanup_automation.py` | Cleanup utilities | ✅ Keep - utilities |

## 📁 TARGET STRUCTURE (After Migration)

```
src/
├── core/                    # ✅ Complete
├── shared/                  # ✅ Complete
├── pm/                      # 🔄 Next phase
│   ├── orchestrator.py     # From ai_orchestrator/orchestrator.py
│   ├── tools/              # From mcp_server/ + ai_orchestrator tools
│   └── context/            # From ai_orchestrator context files
├── ea/                      # 🆕 Future phase
│   ├── orchestrator.py
│   └── tools/
├── cli/                     # 🔄 Update to use persona router
├── agent/                   # ✅ Keep as-is
├── devops_gateway/          # ✅ Keep as-is
└── utils/                   # ✅ Keep as-is
```

## 🚀 MIGRATION PRIORITY

1. **Phase 2** (Next): Migrate PM module (`src/ai_orchestrator/` → `src/pm/`)
2. **Phase 3**: Update CLI to use persona routing
3. **Phase 4**: Create EA module structure
4. **Phase 5**: Reorganize tests to match new structure