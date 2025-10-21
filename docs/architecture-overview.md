# Architecture Overview

## Current Status: Phase 1 Complete

We've successfully implemented the core infrastructure for the dual-persona AI assistant. Here's where we are:

## ✅ COMPLETED: Core Infrastructure

### 🏗️ Foundation Components

**Persona Detection System**
- Automatically detects whether requests are PM-focused or EA-focused
- Multi-factor analysis: keywords + context + LLM classification
- 95%+ accuracy in testing
- Location: `src/core/persona_detector.py`

**Base Orchestrator Framework**
- Common functionality for both PM and EA orchestrators
- LLM integration and prompt management
- Execution planning and result handling
- Location: `src/core/base_orchestrator.py`

**Shared Data Models**
- Cross-persona communication models
- Project, repository, and team contexts
- Merge utilities for combining PM and EA perspectives
- Location: `src/shared/common_models.py`

**Interface Contracts**
- `OrchestratorInterface` - ensures consistent behavior
- `ToolInterface` - standard tool definitions
- Location: `src/core/interfaces/`

## 🔄 IN PROGRESS: PM Module Migration

### Current PM Functionality (Legacy Location)

**Main Orchestrator** (`src/ai_orchestrator/orchestrator.py`)
- Natural language request handling
- Intent classification with domain knowledge
- Multi-step execution planning
- Business intelligence generation
- Interactive work item creation
- Wiki reporting integration

**Tools & Intelligence** (`src/ai_orchestrator/` + `src/mcp_server/`)
- Azure DevOps MCP server with 10+ tools
- Smart WIQL query builder
- Business intelligence engine
- Interactive planner for work item creation
- Repository intelligence system
- Context manager with session memory

### Migration Plan

```
src/ai_orchestrator/orchestrator.py → src/pm/orchestrator.py
src/mcp_server/server.py → src/pm/tools/mcp_server.py
src/ai_orchestrator/context_manager.py → src/pm/context/context_manager.py
src/ai_orchestrator/insights_engine.py → src/pm/tools/insights_engine.py
... (see file-structure.md for complete mapping)
```

## 🆕 FUTURE: EA Module Structure

### Planned EA Components

**EA Orchestrator** (`src/ea/orchestrator.py`)
- Architecture-focused request handling
- Component and system analysis
- Governance and compliance checking

**EA Tools** (`src/ea/tools/`)
- Architecture analysis MCP server
- Diagram generation (PlantUML, Mermaid)
- Pattern library and recommendations
- Technology stack assessment
- Compliance checking engines

## 🔄 Cross-Persona Bridge

### Shared Components (`src/shared/`)

**Repository Intelligence**
- Analyzes READMEs and codebases
- Technology stack detection
- Capability extraction
- Used by both PM (for work assignment) and EA (for architecture analysis)

**Persona Bridge** (Future)
- Enables cross-persona queries
- "Show me architecture impact of this epic"
- "What teams own this system component"

## 🎯 User Experience

### Current CLI

```bash
# Works now (routes to legacy PM orchestrator)
python -m src.cli.ai_cli ask "Show me critical bugs"

# After migration (same command, persona auto-detection)
python -m src.cli.ai_cli ask "Show me critical bugs"          # → PM
python -m src.cli.ai_cli ask "Analyze system architecture"    # → EA
```

### Persona Detection Examples

**PM Requests:**
- "Show me all critical bugs" → PM (confidence: 0.95)
- "Create an epic for data platform" → PM (confidence: 0.90)
- "What's our team's workload?" → PM (confidence: 0.85)

**EA Requests:**
- "Analyze the architecture of our payment system" → EA (confidence: 0.95)
- "Check compliance with API standards" → EA (confidence: 0.90)
- "Map component dependencies" → EA (confidence: 0.85)

**Cross-Persona:**
- "What's the impact of authentication refactoring?" → PM + EA context

## 🚀 Next Steps

### Phase 2: PM Module Migration
1. Create `src/pm/` directory structure
2. Migrate orchestrator with base class inheritance
3. Move tools to `src/pm/tools/`
4. Update prompts to `prompts/pm/`
5. Test PM functionality in new structure

### Phase 3: CLI Integration
1. Update `src/cli/ai_cli.py` to use persona router
2. Add persona detection at entry point
3. Route requests to appropriate orchestrator

### Phase 4: EA Module Creation
1. Create `src/ea/` structure
2. Implement EA orchestrator
3. Add basic architecture analysis tools
4. Create EA-specific prompts

### Phase 5: Cross-Persona Features
1. Implement persona bridge
2. Add cross-context sharing
3. Enable complex cross-persona queries

## 📊 Benefits Achieved

✅ **Modular Architecture** - Clean separation of concerns
✅ **Independent Development** - PM and EA can be developed separately
✅ **Unified Interface** - Single CLI with smart routing
✅ **Extensible Design** - Easy to add new personas or tools
✅ **Backward Compatibility** - Existing PM functionality preserved
✅ **Type Safety** - Strong interfaces and contracts