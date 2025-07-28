# Azure DevOps PM Agent - Architecture

## Overview
The PM Agent implements a two-layer architecture with intelligent business intelligence capabilities driven by LLM-based request classification.

## Directory Structure

```
azure-devops-pm-agent/
├── src/
│   ├── cli/
│   │   └── main.py                    # CLI commands and entry point
│   ├── agent/                         # Core PM agent logic
│   │   ├── agent.py                   # Legacy LLM plan generation
│   │   ├── plan_schema.py             # Pydantic models for structured plans
│   │   ├── sync_engine.py             # Deterministic sync layer (two-layer arch)
│   │   ├── page_reader.py             # Reads PM-Agent wiki page instructions
│   │   ├── request_classifier.py      # LLM-based business request classification
│   │   ├── business_intel.py          # Executes BI requests (PRs, Issues, Sprint)
│   │   └── wiki_interface.py          # Creates interaction transcripts
│   ├── devops_gateway/                # Azure DevOps SDK wrappers
│   │   ├── connection.py              # Authentication and client setup
│   │   ├── work_items.py              # CRUD operations with external_key tags
│   │   ├── wiki.py                    # Wiki page management (with includeContent fix)
│   │   └── wiki_setup.py              # One-time wiki structure setup
│   └── utils/                         # Shared utilities
│       ├── settings.py                # Pydantic-based configuration
│       ├── openai_client.py           # Azure OpenAI client wrapper
│       └── json_fence.py              # JSON extraction from LLM responses
├── prompts/                           # LLM prompt templates
│   └── classify_business_request.md   # Business request classification prompt
├── outputs/                           # Generated outputs (PLAN-*.json, BI-*.json)
├── .env                               # Environment configuration (secrets)
├── CLAUDE.md                          # Development guidance for Claude Code
└── ARCHITECTURE.md                    # This file
```

## Core Architecture Patterns

### 1. Two-Layer Architecture (FEEDBACK.md Implementation)

**Layer 1: LLM Planner** (Pure reasoning, no API calls)
- **Location**: `src/agent/agent.py` + `src/agent/plan_schema.py`
- **Purpose**: Generates structured plans from business goals
- **Output**: Validated `StructuredPlan` objects with external keys

**Layer 2: Deterministic Sync Engine** (Idempotent operations)
- **Location**: `src/agent/sync_engine.py`
- **Purpose**: Processes structured plans and syncs to Azure DevOps
- **Features**: Diff-first workflow, external_key tracking, idempotent upserts

### 2. Business Intelligence System

**PM-Agent Page** → **LLM Classification** → **Data Retrieval** → **Report Generation**

1. **Configuration**: Business PM edits `/PM-Agent` wiki page with projects and requests
2. **Classification**: `request_classifier.py` uses LLM prompts to intelligently parse requests
3. **Execution**: `business_intel.py` queries Azure DevOps based on classification
4. **Reporting**: Results saved as interaction transcripts in wiki

### 3. Prompt-Driven Intelligence

- **Location**: `prompts/` directory
- **Pattern**: Externalized LLM prompts for maintainable AI logic
- **Benefits**: Easy iteration, version control, context-rich classification

## Key Components

### CLI Interface (`src/cli/main.py`)
Primary commands:
- `setup-pm-page` - Create template PM-Agent page
- `execute-requests` - Run business intelligence analysis
- `plan-new` - Generate structured plans (Layer 1)
- `sync` - Apply plans to Azure DevOps (Layer 2)

### Request Classification (`src/agent/request_classifier.py`)
- **Input**: Business requests from PM-Agent page
- **Process**: LLM-based classification using prompt templates
- **Output**: Structured classification (pull_requests, work_items, sprint_progress)
- **Fallback**: Keyword matching if LLM fails

### Business Intelligence (`src/agent/business_intel.py`)
- **Pull Requests**: Cross-project PR analysis with date filtering
- **Work Items**: Issue tracking with priority filtering
- **Sprint Progress**: State breakdown and progress reporting

### Azure DevOps Gateway (`src/devops_gateway/`)
- **Authentication**: Centralized connection management
- **Work Items**: CRUD with external_key tagging for idempotency
- **Wiki**: Page management with `includeContent=true` fix
- **Direct REST API**: Fallback for SDK limitations (e.g., PR status filtering)

## Data Flow

### Business Intelligence Workflow
1. **Setup**: `setup-pm-page` creates template
2. **Configuration**: PM manually edits `/PM-Agent` page
3. **Classification**: LLM analyzes requests using prompts
4. **Execution**: Query Azure DevOps APIs based on classification
5. **Reporting**: Generate comprehensive BI report in wiki

### Plan Generation Workflow
1. **Planning**: LLM generates structured plan (Layer 1)
2. **Preview**: Show diff of changes before applying
3. **Approval**: Human approves changes with `--approve` flag
4. **Sync**: Deterministic application to Azure DevOps (Layer 2)

## Key Design Decisions

### External Key System
- Every work item tagged with `external_key:EP-001` for idempotent lookups
- Enables diff-first workflow and prevents duplicate creation

### Separation of Concerns
- LLM layer never calls Azure DevOps APIs directly
- Deterministic sync layer handles all API interactions
- Clear boundaries between reasoning and execution

### Wiki-Based Interface
- **Main Page**: `/PM-Agent` dashboard for PM configuration
- **Interactions**: `/PM-Agent/Interactions/{timestamp}` for full reports
- **Auto-Updates**: Dashboard refreshes after operations

### Prompt-Driven Classification
- LLM prompts stored in `prompts/` directory
- Easy to iterate and improve without code changes
- Rich context provided for accurate classification

## Security Notes

🔐 **Critical Security Practices**:
- Never hardcode PATs in Python files
- Always use `settings.azdo_pat` from environment variables
- `.env` file must be in `.gitignore`
- Use settings module for all secret access