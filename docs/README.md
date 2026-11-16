# Azure DevOps PM Agent Documentation

This directory contains comprehensive documentation for the Azure DevOps PM Agent project.

## 📁 Documentation Structure

### 🏗️ Core Architecture
- **[Architecture Overview](architecture-overview.md)** - High-level system architecture and design patterns
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Detailed technical architecture documentation
- **[File Structure](file-structure.md)** - Detailed explanation of project organization

### 📈 Project Status & Progress
- **[Migration Status](migration-status.md)** - Historical migration progress
- **[Current Status](current_status.md)** - ✅ **Latest: On-Demand MCP Server Implementation COMPLETED**
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and feature updates

### 🧪 Testing & Workflows
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Comprehensive testing documentation
- **[INTERACTIVE_WORKFLOW.md](INTERACTIVE_WORKFLOW.md)** - Interactive planning and execution workflows

### 📝 Development & Feedback
- **[FEEDBACK.md](FEEDBACK.md)** - User feedback and improvement suggestions

### 🔗 Quick Reference
- See the main [README.md](../README.md) for project overview and quick start
- Check [AGENTS.md](../AGENTS.md) for current Copilot ingestion and portal instructions

## 🚀 Recent Major Achievements

The project has completed significant architectural improvements:

### ✅ **On-Demand MCP Server Implementation (COMPLETED)**
- **Resource Efficiency**: Server only runs when needed (2.82s execution time)
- **Process Isolation**: Failures don't crash the orchestrator
- **Official MCP Protocol**: Fully compliant with MCP v1.14.0 standards
- **10 Azure DevOps Tools**: All working perfectly with comprehensive testing

### ✅ **Two-Layer Architecture**
- **LLM Reasoning Layer**: Intelligent planning and analysis
- **Deterministic Sync Layer**: Reliable Azure DevOps operations
- **Prompt-Driven Intelligence**: Externalized prompts for easy iteration

### ✅ **Enhanced PM Workflows**
- **Business Intelligence**: Automated project health scoring and insights
- **Interactive Planning**: Context-aware work item creation with approval gates
- **Repository Intelligence**: AI-powered repository assignment and capability analysis

## 🧪 Testing

### Comprehensive Test Suite
```bash
# Run complete MCP integration tests
python tests/test_mcp_integration.py

# Run AI system tests
python tests/test_ai_system.py

# Run cleanup automation
python tests/cleanup_automation.py --type=standard --live
```

### Test Coverage
- **MCP Integration**: OnDemandMCPClient, official MCP library, direct protocol validation
- **AI System**: Repository intelligence, context management, workflow orchestration
- **Azure DevOps**: Work items, pull requests, projects, repositories (10 tools)

## 🏗️ Architecture Summary

```
PM Orchestrator → OnDemandMCPClient → FastMCP Server (subprocess)
                        ↓
                Official MCP Library v1.14.0
                        ↓
            Automatic Session Management
                        ↓
           Azure DevOps Tool Execution (10 tools)
```

## 📊 Key Metrics

- **🛠️ Tools Available**: 10 Azure DevOps tools
- **⚡ Performance**: 2.82s average execution time
- **📈 Success Rate**: 100% test pass rate
- **🔄 Protocol**: MCP v1.14.0 compliant
- **🏢 Projects**: Successfully tested with 12 Azure DevOps projects

## 🎯 Current Usage

### Business Intelligence (Main Use Case)
```bash
# 1. Setup PM-Agent page template
python -m src.cli.main setup-pm-page

# 2. PM manually edits /PM-Agent page with requests
# 3. Execute intelligent business analysis
python -m src.cli.main execute-requests
```

### AI-Powered Natural Language Interface
```bash
# Interactive chat mode
python -m src.cli.ai_cli chat

# One-shot commands
python -m src.cli.ai_cli ask "What's the health of our data platform project?"
python -m src.cli.ai_cli ask "Show me critical bugs assigned to John"
python -m src.cli.ai_cli ask "Push this analysis to wiki for the executive meeting"
```

### Plan Generation (Two-Layer Architecture)
```bash
# Generate structured plan (LLM reasoning layer)
python -m src.cli.main plan-new "Business goal"

# Preview changes (deterministic sync layer)
python -m src.cli.main preview outputs/PLAN-*.json

# Apply with approval
python -m src.cli.main sync outputs/PLAN-*.json --approve
```

## 🎯 Navigation

- **[↑ Back to Project Root](../README.md)**
- **[📁 Source Code](../src/)**
- **[🧪 Tests](../tests/)**
- **[🤖 Prompts](../prompts/)**
- **[⚙️ Configuration](../README.md#setup)**

## 🤝 Development Status

### ✅ Production Ready Components
- **OnDemandMCPClient**: Official MCP library integration
- **FastMCP Server**: 10 Azure DevOps tools
- **Business Intelligence**: Automated project insights
- **Natural Language Interface**: Chat and one-shot commands
- **Plan Generation**: LLM reasoning + deterministic sync

### 🔧 Architecture Benefits Achieved
- **Resource Efficiency**: On-demand server spawning
- **Process Isolation**: Failure containment
- **Official Protocols**: MCP v1.14.0 compliance
- **Session Management**: Automatic cleanup
- **Error Handling**: Robust failure recovery
- **Type Safety**: Strong contracts and data models

## 📊 Quick Health Check

To verify the system state:

```bash
# Test MCP integration
python tests/test_mcp_integration.py

# Test AI system
python tests/test_ai_system.py

# Test existing functionality
python -m src.cli.ai_cli ask "What projects do we have?"
```

All tests should pass with 100% success rate if the system is healthy.