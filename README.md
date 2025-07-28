# Azure DevOps PM Agent

AI-powered business intelligence agent with two-layer architecture for Azure DevOps project management.

## Features

### 🧠 Business Intelligence (Primary Use Case)
- PM configures requests via Azure DevOps wiki page (`/PM-Agent`)
- LLM-based request classification and intelligent execution
- Automated PR analysis, work item tracking, and sprint progress reporting
- Comprehensive BI reports with actionable insights

### 📋 Strategic Planning
- Generate structured Epic/Feature plans from business goals
- Two-layer architecture: LLM reasoning layer + deterministic sync layer
- Diff-first approval workflow with preview capabilities
- External key system for idempotent Azure DevOps operations

## Quick Start

### Installation
```bash
python -m venv .venv && source .venv/bin/activate  # (or .venv\Scripts\activate on Windows)
pip install -e .
```

### Environment Setup
Configure `.env` with Azure DevOps and OpenAI credentials:
```bash
AZDO_ORG_URL=https://dev.azure.com/yourorg
AZDO_PROJECT=YourProject
AZDO_PAT=your_personal_access_token
AZDO_WIKI_NAME=YourWiki
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_KEY=your_openai_key
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT=gpt-4
```

### Primary Workflow - Business Intelligence
```bash
# 1. Setup PM-Agent page template
python -m src.cli.main setup-pm-page

# 2. PM manually edits /PM-Agent page with projects and requests
# 3. Execute intelligent business analysis
python -m src.cli.main execute-requests
```

### Strategic Planning Workflow
```bash
# Generate structured plan
python -m src.cli.main plan-new "Build unified data platform"

# Preview changes before applying
python -m src.cli.main preview outputs/PLAN-*.json

# Apply with approval
python -m src.cli.main sync outputs/PLAN-*.json --approve
```

## Architecture

### Core Design Principles
1. **Two-Layer Separation**: LLM reasoning layer + deterministic sync layer
2. **Prompt-Driven Intelligence**: Externalized to `prompts/` directory for easy iteration
3. **Business Intelligence Focus**: PM-configurable wiki-based requests with LLM classification
4. **External Key System**: Idempotent operations using tagged work items

### Key Components
- **`src/cli/main.py`**: CLI commands and entry points
- **`src/agent/business_intel.py`**: Executes BI requests with direct Azure DevOps API calls
- **`src/agent/request_classifier.py`**: LLM-based request classification using prompt templates
- **`src/agent/sync_engine.py`**: Deterministic sync engine for planning operations
- **`prompts/classify_business_request.md`**: Classification prompt template
- **`src/devops_gateway/`**: Azure DevOps SDK wrappers with REST API fallbacks

### Data Flow
```
PM Wiki Page → LLM Classification → Azure DevOps Queries → BI Report → Wiki Transcript
```

## Recent Major Fixes
1. **Wiki Reading**: Fixed empty content issue by adding `includeContent=true` parameter
2. **Pull Request Retrieval**: Replaced SDK with direct REST API calls using `searchCriteria.status=all`
3. **DateTime Handling**: Fixed timezone-aware comparisons 
4. **Request Classification**: Implemented LLM-based classification replacing brittle text matching
5. **Auto-linking Issues**: Changed display format from `#4` to `PR-4` and `WI-5` to prevent unwanted linking

## Commands Reference

| Command | Description |
|---------|-------------|
| `setup-pm-page` | Create PM-Agent wiki page template |
| `execute-requests` | Process business intelligence requests |
| `plan-new "goal"` | Generate structured Epic/Feature plan |
| `preview plan.json` | Show planned changes without applying |
| `sync plan.json --approve` | Apply planned changes to Azure DevOps |

## ID Reconciliation System

The system handles Azure DevOps auto-generated IDs (`#1`, `#2`, `#3`) and planning system IDs through:

- **External Key System**: Uses tagged work items with `external_key:PLAN-ID-001` format
- **Display Formatting**: Shows `PR-4` for pull requests and `WI-5` for work items to avoid auto-linking
- **Lookup Mechanism**: Queries work items by external key tags for idempotent operations
- **Planning Integration**: Maps business plans to actual Azure DevOps items via stable external references

This enables the planning system to maintain its own logical structure while syncing with Azure DevOps' auto-generated numeric IDs.