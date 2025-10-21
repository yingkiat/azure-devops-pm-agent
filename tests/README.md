# Azure DevOps PM Agent - Test Suite

## Overview

This directory contains tests for the Azure DevOps PM Agent system. The system uses a two-layer architecture with PM and EA modules, real MCP integration, and AI-powered orchestration for project management workflows.

## Test Coverage Requirements

### Core System Components

#### 1. **MCP Integration** ✅ COMPLETE
- **File**: `test_mcp_integration.py`
- **Status**: ✅ Working and current
- **Coverage**: Real MCP server integration, tool calls, Azure DevOps API integration

#### 2. **AI Orchestration** 🔄 NEEDS UPDATE
- **File**: `test_ai_orchestrator.py`
- **Purpose**: Test core orchestration pipeline
- **Coverage Needed**:
  - Intent classification (natural language → structured intents)
  - Execution planning (multi-step API orchestration)
  - Tool execution coordination
  - Error handling and fallback mechanisms

#### 3. **Context Management** 🔄 NEEDS UPDATE
- **File**: `test_context_persistence.py`
- **Purpose**: Test session memory and learning capabilities
- **Coverage Needed**:
  - Session context storage and retrieval
  - Project context tracking
  - Conversation history management
  - User preference learning
  - Context persistence across sessions

#### 4. **Business Intelligence** 🔄 NEEDS UPDATE
- **File**: `test_insights_engine.py`
- **Purpose**: Test PM analytics and reporting
- **Coverage Needed**:
  - Work item analysis and health scoring
  - Project health calculations
  - Team workload analysis
  - Pull request insights
  - Recommendation generation

### PM Tools and Workflows

#### 5. **Query System** 🔄 NEEDS UPDATE
- **File**: `test_smart_queries.py`
- **Purpose**: Test natural language to WIQL conversion
- **Coverage Needed**:
  - Natural language parsing
  - WIQL query generation
  - Domain knowledge application
  - Query optimization and performance

#### 6. **Batch Operations** 🔄 NEEDS UPDATE
- **File**: `test_batch_operations.py`
- **Purpose**: Test performance-critical API operations
- **Coverage Needed**:
  - Parallel API execution
  - Batch project overviews
  - Batch work item queries
  - Performance improvements verification

#### 7. **Wiki Integration** 🔄 NEEDS UPDATE
- **File**: `test_manual_wiki.py`
- **Purpose**: Test wiki documentation workflows
- **Coverage Needed**:
  - Manual wiki push functionality
  - Context selection for documentation
  - Wiki content formatting
  - PM-friendly output generation

### Repository Intelligence

#### 8. **Repository Analysis** 🔄 NEEDS UPDATE
- **File**: `test_repository_intelligence.py`
- **Purpose**: Test AI-powered repository matching
- **Coverage Needed**:
  - README analysis and understanding
  - Technology stack detection
  - Domain classification
  - Repository scoring and matching
  - Work item assignment recommendations

### Integration and Workflows

#### 9. **End-to-End Workflows** 🔄 NEEDS UPDATE
- **File**: `demo_wiki_flow.py`
- **Purpose**: Demonstrate realistic PM workflows
- **Coverage Needed**:
  - Complete PM analysis workflow
  - Natural language interaction
  - Wiki documentation generation
  - Executive reporting capabilities

#### 10. **System Health** 🔄 NEEDS UPDATE
- **File**: `test_ai_system.py`
- **Purpose**: Comprehensive system validation
- **Coverage Needed**:
  - All component integration
  - Configuration system validation
  - Error handling across modules
  - Performance benchmarking
  - Production readiness checks

## Test Categories by Function

### **Core Intelligence**
- Intent classification and natural language understanding
- Context learning and session management
- Business intelligence generation

### **Azure DevOps Integration**
- MCP server tool execution
- Batch operations and performance optimization
- Work item and project data analysis

### **PM-Specific Features**
- Wiki documentation workflows
- Repository intelligence and matching
- Query building and optimization

### **System Integration**
- End-to-end workflow validation
- Cross-component functionality
- Performance and reliability testing

## Current Status

| Component | Test File | Status | Priority | Pytest |
|-----------|-----------|--------|----------|---------|
| MCP Integration | `test_mcp_integration.py` | ✅ Complete | - | ✅ Ready |
| AI Orchestration | `test_ai_orchestrator.py` | ✅ Updated | High | ✅ Ready |
| Context Management | `test_context_persistence.py` | ✅ Updated | High | ✅ Ready |
| Business Intelligence | `test_insights_engine.py` | ✅ Updated | High | ✅ Ready |
| Query System | `test_smart_queries.py` | 🔄 Needs Update | Medium | ❌ Excluded |
| Batch Operations | `test_batch_operations.py` | 🔄 Needs Update | Medium | ❌ Excluded |
| Wiki Integration | `test_manual_wiki.py` | 🔄 Needs Update | Medium | ❌ Excluded |
| Repository Intelligence | `test_repository_intelligence.py` | 🔄 Needs Update | Medium | ❌ Excluded |
| Workflow Demo | `demo_wiki_flow.py` | 🔄 Needs Update | Low | ❌ Excluded |
| System Health | `test_ai_system.py` | 🔄 Needs Update | Low | ❌ Excluded |

## Running Tests

### Pytest Test Suite (Recommended)

**Install test dependencies:**
```bash
pip install -e .[test]
```

**Run high-priority core tests:**
```bash
# Run all high-priority tests with HTML report
pytest -m high_priority

# Or use the dedicated runner script
python run_high_priority_tests.py
```

**Run specific test files:**
```bash
pytest tests/test_ai_orchestrator.py
pytest tests/test_context_persistence.py
pytest tests/test_insights_engine.py
pytest tests/test_mcp_integration.py
```

**Advanced pytest options:**
```bash
# Run with verbose output
pytest -m high_priority -v

# Run with coverage report
pytest -m high_priority --cov=src --cov-report=html

# Run specific test function
pytest tests/test_ai_orchestrator.py::test_orchestrated_requests

# Run tests in parallel (if you add pytest-xdist)
pytest -m high_priority -n auto
```

### View Test Results

**HTML Report (Auto-generated):**
- Location: `reports/test_results.html`
- Open in browser: `Invoke-Item reports/test_results.html` (PowerShell) or `start reports/test_results.html` (CMD)
- Features: Interactive dashboard, detailed results, failure analysis

**Console Output:**
- Real-time test progress
- Pass/fail summary with execution times
- Detailed error messages for failures

### Individual Script Tests (Legacy)
```bash
# Direct script execution (if needed)
python tests/test_mcp_integration.py           # ✅ Works now
python tests/test_ai_orchestrator.py           # ✅ Updated
python tests/test_context_persistence.py       # ✅ Updated
python tests/test_insights_engine.py           # ✅ Updated
```

## Test Environment Requirements

- Azure DevOps credentials configured in `.env`
- OpenAI API access for AI orchestration
- Python 3.9+ with required dependencies
- Real Azure DevOps project for integration testing

## Utilities

- **`cleanup_automation.py`**: Test cleanup utility for managing test data and artifacts

## Pytest Configuration

The project uses pytest configured in `pyproject.toml`. Pytest automatically discovers this configuration by searching upward from the current directory.

### **How Pytest Works**

1. **Configuration Discovery**: Looks for `pyproject.toml`, `pytest.ini`, `tox.ini`, or `setup.cfg` (in that order)
2. **Test Discovery**: Finds test functions matching `test_*` pattern in configured files
3. **Marker Filtering**: Runs only tests marked with specified markers (e.g., `@pytest.mark.high_priority`)
4. **Execution & Reporting**: Runs tests and generates console + HTML output

### **Current Configuration**

**Test Markers:**
- `@pytest.mark.high_priority`: Core system tests (always run)
- `@pytest.mark.medium_priority`: Feature tests (planned)
- `@pytest.mark.integration`: Integration tests (planned)
- `@pytest.mark.slow`: Long-running tests (planned)

**Automatic Features:**
- ✅ **HTML Reports**: Auto-generated at `reports/test_results.html`
- ✅ **Async Support**: Built-in support for `async def` test functions
- ✅ **Verbose Output**: Detailed test progress and results
- ✅ **Error Handling**: Short traceback format for faster debugging
- ✅ **Strict Validation**: Ensures markers are defined and config is valid

**Configured Test Files (testpaths):**
- `tests/test_ai_orchestrator.py` (Core orchestration)
- `tests/test_context_persistence.py` (Context management)
- `tests/test_insights_engine.py` (Business intelligence)
- `tests/test_mcp_integration.py` (MCP integration)

**What happens when you run `pytest -m high_priority`:**
```bash
# Pytest automatically applies these options from pyproject.toml:
pytest -ra --strict-markers --strict-config --tb=short -v \
       --html=reports/test_results.html --self-contained-html \
       -m high_priority \
       tests/test_ai_orchestrator.py \
       tests/test_context_persistence.py \
       tests/test_insights_engine.py \
       tests/test_mcp_integration.py
```

## Quality Standards

Each test should verify:
- ✅ Functional correctness
- ✅ Error handling and edge cases
- ✅ Performance within acceptable bounds
- ✅ Integration with real Azure DevOps APIs
- ✅ AI model responses and reliability

**Current Test Results:**
- 🎉 **12 tests passing** (last run: 3m 9s)
- ✅ All high-priority core system tests working
- 📊 HTML dashboard available for detailed analysis