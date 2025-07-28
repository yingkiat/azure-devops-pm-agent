# CLAUDE.md

This file provides guidance to Claude Code when working with the Azure DevOps PM Agent codebase.

## Quick Start

### Installation
```bash
python -m venv .venv && source .venv/bin/activate  # (or .venv\Scripts\activate on Windows)
pip install -e .
```

### Environment Configuration
Configure `.env` with Azure DevOps and OpenAI credentials:
- `AZDO_ORG_URL`, `AZDO_PROJECT`, `AZDO_PAT`, `AZDO_WIKI_NAME`
- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY`, `AZURE_OPENAI_API_VERSION`, `AZURE_OPENAI_DEPLOYMENT`

**🔐 CRITICAL**: Never hardcode PATs in Python files. Always use `settings.azdo_pat` from the settings module.

## Primary Workflows

### Business Intelligence (Main Use Case)
```bash
# 1. Setup PM-Agent page template
python -m src.cli.main setup-pm-page

# 2. PM manually edits /PM-Agent page with requests
# 3. Execute intelligent business analysis
python -m src.cli.main execute-requests
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

## Architecture Summary

The system implements a **two-layer architecture** with **prompt-driven intelligence**:

### Core Philosophy
1. **Two-Layer Separation**: LLM reasoning layer + deterministic sync layer
2. **Prompt-Driven**: Intelligence externalized to `prompts/` directory for easy iteration
3. **Business Intelligence**: PM configures via wiki page, LLM classifies and executes requests
4. **External Key System**: Idempotent operations using tagged work items

### Key Files
- **`src/cli/main.py`**: CLI commands and entry point
- **`src/agent/request_classifier.py`**: LLM-based request classification using prompts
- **`src/agent/business_intel.py`**: Executes BI requests (PRs, Issues, Sprint Progress)
- **`src/agent/sync_engine.py`**: Deterministic sync to Azure DevOps
- **`prompts/classify_business_request.md`**: Classification prompt template
- **`src/devops_gateway/`**: Azure DevOps SDK wrappers with direct REST API fallbacks

### Data Flow
PM Wiki Page → LLM Classification → Azure DevOps Queries → BI Report → Wiki Transcript

See `ARCHITECTURE.md` for detailed system design and component documentation.