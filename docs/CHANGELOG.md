# Changelog

All notable changes to the Azure DevOps PM Agent project are documented in this file.

## [2.0.0] - 2024-08-25 - Interactive Multi-Stage AI Workflow

### 🚀 **Major Features Added**

#### **Interactive Work Item Creation System**
- **NEW**: Multi-stage AI workflow with human approval gates for safe work item creation
- **NEW**: Dynamic work item type classification (Epic, Feature, User Story, Task, Bug, Issue)
- **NEW**: Repository intelligence engine with README analysis and smart assignment
- **NEW**: Interactive approval workflow with rich proposal formatting
- **NEW**: Hierarchical planning for complex requests with parent-child relationships

#### **Enhanced AI Intelligence**
- **NEW**: Smart intent routing - Query requests → Direct execution, Creation requests → Interactive approval
- **NEW**: Context-aware work item classification with confidence scoring
- **NEW**: Pattern learning system that remembers successful repository assignments
- **NEW**: Multi-model architecture optimized for different types of analysis

#### **Safety & Control Features**
- **NEW**: Explicit approval required for all work item creation (no accidental creation)
- **NEW**: Rich proposal previews with acceptance criteria and dependencies
- **NEW**: Cancellation support (Ctrl+C) and rejection options
- **NEW**: Edit workflow framework (extensible for future enhancements)

### **🏗️ Architecture Enhancements**

#### **New Components Added**
- `src/ai_orchestrator/work_item_classifier.py` - Dynamic work item type classification
- `src/ai_orchestrator/repository_intelligence.py` - Smart repository assignment (architecture ready)
- `src/ai_orchestrator/interactive_planner.py` - Multi-stage approval workflow
- `INTERACTIVE_WORKFLOW.md` - Comprehensive architecture documentation

#### **Enhanced Components**
- `src/ai_orchestrator/orchestrator.py` - Added smart routing logic and interactive creation handler
- `src/cli/ai_cli.py` - Enhanced output formatting and emoji cleanup for Windows compatibility
- `prompts/intent_classification.md` - Added CREATE intent detection with special handling
- `src/ai_orchestrator/context_manager.py` - Added preferred projects support

### **🎯 User Experience Improvements**

#### **Natural Language Interface**
```bash
# NEW: Creation with approval workflow
python -m src.cli.ai_cli ask "Create epic for user dashboard"
# → Analyzes → Proposes → Waits for approval → Creates only if approved

# IMPROVED: Direct query execution (unchanged UX)
python -m src.cli.ai_cli ask "Show me critical bugs"
# → Immediate results (no approval needed)
```

#### **Rich Interactive Experience**
- **NEW**: Detailed proposal formatting with effort estimates
- **NEW**: Repository assignment recommendations with confidence scores
- **NEW**: Preview mode for detailed inspection before approval
- **NEW**: Progress tracking during multi-stage workflow execution

### **🛡️ Safety Improvements**

#### **Approval Gates**
- All CREATE intents now require explicit human approval
- No work items can be created accidentally through conversational queries
- Clear proposal formatting shows exactly what will be created
- Multiple approval options: approve/reject/preview/edit

#### **Error Handling**
- Graceful fallback classification when AI is unavailable
- Pattern matching backup system for work item type detection
- Robust error recovery during multi-stage workflows
- Context preservation during approval interruptions

### **⚡ Performance Enhancements**

#### **Optimized AI Model Usage**
- Single AI call for intent classification with smart caching
- Fallback pattern matching for offline/low-latency scenarios
- Optimized prompts with context length management
- Parallel processing where applicable

#### **Windows Compatibility**
- Fixed Unicode/emoji encoding issues for Windows console
- Cleaned all non-ASCII characters from output streams
- Improved error handling for character encoding problems

### **📊 Technical Improvements**

#### **Code Quality**
- Comprehensive inline documentation added to all new components
- Type hints and dataclass usage throughout new modules
- Structured error handling with detailed error messages
- Consistent async/await patterns across all AI operations

#### **Configuration**
- Enhanced settings support for repository intelligence
- Context persistence with user preference learning
- Configurable project selection for work item creation
- OpenAI deployment configuration fixes

### **🧪 Testing & Development**

#### **Testing Infrastructure**
- Created test framework for interactive workflow components
- Added fallback testing for offline scenarios
- Comprehensive error case testing for approval workflows
- Pattern matching validation tests

#### **Developer Experience**
- Complete architecture documentation in `INTERACTIVE_WORKFLOW.md`
- Updated `CLAUDE.md` with sprint progress and feature documentation
- Enhanced `README.md` with new workflow examples
- Inline code documentation for all new components

---

## [1.5.0] - Previous Releases

### **AI Orchestration System**
- Complete AI orchestration system with natural language understanding
- MCP server foundation with 55% performance improvements through batch operations
- Business intelligence engine with automated insights generation
- Context persistence and session memory across conversations
- Wiki reporting system with diary-style entries

### **Core Features**
- Natural language CLI interface with rich output formatting
- Comprehensive Azure DevOps integration (projects, work items, PRs, repositories)
- Business intelligence scoring with health metrics
- Team workload analysis and bottleneck detection
- Strategic recommendations with cross-project pattern recognition

---

## Migration Guide

### For Existing Users

#### **Query Workflows** (No Changes)
Your existing query commands work exactly the same:
```bash
python -m src.cli.ai_cli ask "Show me projects" # ✅ Same as before
python -m src.cli.ai_cli chat                   # ✅ Same as before
```

#### **Work Item Creation** (New Interactive Flow)
Previously direct creation commands now trigger interactive approval:
```bash
# Before (if it worked): Direct creation
# Now: Interactive approval workflow
python -m src.cli.ai_cli ask "Create epic for dashboard"
# → Shows proposal → Asks for approval → Creates only if approved
```

#### **Legacy Planning Commands** (Still Available)
All existing planning commands remain unchanged:
```bash
python -m src.cli.main plan-new "Business goal"  # ✅ Still works
python -m src.cli.main preview outputs/PLAN-*.json  # ✅ Still works
```

### Benefits of Migration
1. **Safety**: No accidental work item creation
2. **Intelligence**: Smart work item type detection and repository assignment
3. **Transparency**: Clear proposals with effort estimates and reasoning
4. **Control**: Explicit approval for all creation operations
5. **Learning**: System learns from your patterns for better future suggestions

---

## Breaking Changes

### None for End Users
- All existing CLI commands continue to work
- Query workflows unchanged
- Legacy planning workflows preserved
- Only work item creation now requires approval (safety improvement)

### For Developers/Integrators
- `CREATE` intent now routes to interactive workflow instead of direct execution
- New required components: `WorkItemClassifier`, `InteractivePlanner`
- Enhanced context manager with preference support
- OpenAI model configuration consistency required across all components

---

## Configuration Updates

### Required Environment Variables (Unchanged)
```bash
AZDO_ORG_URL=https://dev.azure.com/your-org/
AZDO_PROJECT=Your-Primary-Project
AZDO_PAT=your-personal-access-token
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o  # Must be consistent across all components
```

### New Optional Configuration
```bash
AZDO_PROJECTS=Project1,Project2  # Multiple projects for repository intelligence
```

---

## Known Issues

### Resolved in This Release
- ✅ Unicode/emoji encoding issues on Windows console
- ✅ Inconsistent OpenAI model configuration across components  
- ✅ Missing context manager methods for preferred projects
- ✅ `step_result` undefined variable error in orchestrator execution

### Current Limitations
- Repository intelligence engine architecture is ready but full implementation pending
- Edit mode in approval workflow is framework-only (not fully implemented)
- Preview mode shows basic information (detailed acceptance criteria pending full implementation)

---

## Future Roadmap

### Next Phase (v2.1.0)
- Complete repository intelligence implementation with full README analysis
- Enhanced edit mode with proposal modification capabilities
- Advanced repository pattern learning from historical work item assignments
- Cross-project dependency detection for complex planning

### Long Term (v3.0.0)
- Multi-repository epic planning with automatic dependency management
- Advanced team capacity planning with workload optimization
- Integration with existing business intelligence workflow
- Custom work item type support beyond Agile process template

---

*For detailed technical documentation, see `INTERACTIVE_WORKFLOW.md`*
*For current operating guidance, see [AGENTS.md](../AGENTS.md) and [README.md](../README.md). Historical entries retain the guide names used at the time.*