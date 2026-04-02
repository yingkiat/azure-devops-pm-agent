# UDW Agent Application Specification

**Application Name:** UDW Agent
**Type:** AI-Powered Query & Analysis Platform
**Status:** Active
**Last Updated:** 2025-10-27

---

## 1. Executive Summary

UDW Agent is an intelligent data query platform that combines **PowerApps UI** with **Azure Container-based AI reasoning** and **event logging infrastructure**. It enables users to query Fabric Data Warehouse with natural language input, receiving AI-powered analysis with multi-stage reasoning, structured result tables, and comprehensive audit logging.

**Key Innovation:** Multi-stage agentic reasoning with adaptive execution strategies (Direct Tools, Single-Stage, Multi-Stage) providing response times from 100ms to 45s depending on query complexity.

---

## 2. Architecture Overview

### Architectural Layers

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: PowerApps UI (Frontend)                       │
│  - Text input for natural language queries              │
│  - Button trigger for API calls                         │
│  - Dynamic HTML rendering of results                    │
│  - Table data visualization                             │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴──────────┐
         │                      │
    ┌────▼──────────┐   ┌──────▼────────────┐
    │ Power Automate│   │ Power Automate    │
    │ Flow #1       │   │ Flow #2           │
    │ API Call      │   │ Logging           │
    └────┬──────────┘   └──────┬────────────┘
         │                     │
┌────────▼──────────────────────▼──────────────────────────┐
│  Layer 2: Azure Container API (Intelligence Engine)     │
│  - Fabric DW MCP Server                                 │
│  - Multi-Stage Agentic Reasoning Engine                 │
│  - Adaptive Execution Strategy Selection                │
└────────┬──────────────────────────────────────────────────┘
         │
┌────────▼──────────────────────────────────────────────────┐
│  Layer 3: Data & Logging Infrastructure                 │
│  - Fabric Data Warehouse (Query Backend)                │
│  - Azure Function (Logging Sink)                        │
│  - Event Log Storage                                    │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Component Details

### 3.1 PowerApps UI Component

**Location:** PowerApps Canvas App
**Language:** Power FX (Microsoft's formula language)

**Key Features:**

| Feature | Purpose |
|---------|---------|
| Text Input Box | Accepts user's natural language query |
| Submit Button | Triggers API call to Azure Container |
| Session Tracking | Captures start time, user email, screen name |
| Dynamic HTML Rendering | Displays AI response with markdown-to-HTML conversion |
| Table Data Grid | Visualizes structured result data (product numbers, competitor info) |
| Duration Calculation | Tracks API response time in milliseconds |

**Key Variables & State:**
- `varAppName`: "UDW Agent"
- `varScreenName`: Current screen identifier
- `varStartTime`: Timestamp when query initiated
- `varUserEmail`: Current user's email (from `User().Email`)
- `varResponseText`: AI-generated response text
- `varRawJson`: Full JSON response from API
- `varDurationMs`: Computed response duration (milliseconds)
- `colTableData`: Collection of structured results with fields:
  - `競合品番` (Competitor Part Number)
  - `品番` (Part Number)
  - `競合メーカー名` (Competitor Manufacturer)
  - `品番2` (Alternative Part Number)
  - `品番説明` (Part Description)

**Response Processing Pipeline:**
1. Parse JSON response from Azure Container API
2. Extract markdown-formatted business answer and key findings
3. Parse tool chain results into structured table data
4. Convert markdown sections to HTML with proper formatting
5. Display answer, key findings, and data table to user

---

### 3.2 Power Automate Integration Flows

**Flow #1: API Call Flow** (`PowerAppV2->HTTP`)

**Trigger:** Button click in PowerApps
**Input:** Concatenated string of employee country + user query text
**Process:** HTTP request to Azure Container API
**Output:**
- `business_answer`: Markdown-formatted response
- `raw_json`: Complete response object with tool chain results

**Sample Input Construction:**
```
LookUp(Employee, 'Email Address'="akiko.ito@medline.com", Country) + " " + TextInput.Text
```

**Flow #2: Logging Flow** (`PowerAppV2->HTTP,RespondtoaPowerApporflow`)

**Trigger:** After API response received
**Input:** JSON event payload with:
- Event metadata (app name, screen, stage, action)
- Performance metrics (duration_ms)
- User context (email)
- Full API response (raw_json)

**Output:** Sends log event to Azure Function for persistent storage

---

### 3.3 Azure Container API (Intelligence Engine)

**Type:** Container-based microservice
**Framework:** Agentic AI with MCP integration

#### Architecture Layers

**Layer 1: Fabric DW MCP Server**
- Standards-compliant MCP server
- 4 complete tools for Fabric Data Warehouse operations
- Full Azure AD authentication
- Clean abstraction over DW operations

**Layer 2: Multi-Stage Agentic Reasoning Engine**
- Advanced intelligent system with adaptive execution strategies
- Direct tool integration for smart routing

#### Execution Strategy Selection

Three execution pathways based on query complexity:

| Strategy | Response Time | Use Case | Process |
|----------|---------------|----------|---------|
| **Direct Tools** | 100-200ms | Pattern-matched queries | Zero AI API calls, direct SQL execution |
| **Single-Stage** | 3-15s | Simple queries | AI-powered SQL generation + summarization |
| **Multi-Stage** | 30-45s | Complex queries | Discovery → Analysis → Evaluation with AI refinement |

**Algorithm:**
1. Analyze incoming query pattern
2. Check against known query patterns (Direct Tools cache)
3. If match: Execute directly (100-200ms)
4. If simple: Single-stage AI SQL generation (3-15s)
5. If complex: Multi-stage reasoning with refinement (30-45s)

**Output Format:**
- `business_answer`: Human-readable markdown response with Key Findings
- `raw_json`: Structured data including:
  - `tool_chain_results`: Array of execution results
  - `direct_tool_execution.result.results`: Structured table data

---

### 3.4 Azure Function (Logging Sink)

**Trigger:** Power Automate webhook call
**Input Format:** CloudEvents JSON structure with:
```json
{
  "id": "GUID",
  "eventType": "log.created",
  "subject": "log/session",
  "data": {
    "trace_id": "GUID",
    "app_name": "UDW Agent",
    "product_module": "screen name",
    "stage": "gpt_call",
    "action": "responded",
    "duration_ms": number,
    "result": "OK",
    "metadata": "raw JSON from API",
    "user_email": "user@company.com"
  },
  "dataVersion": "1.0"
}
```
**Output:** Persists logs to data store (database/blob storage)

---

## 4. Data Flow

### Query Execution Flow

```
1. User enters query in TextInput
                ↓
2. Click Submit button
                ↓
3. PowerApps captures session metadata (time, user, screen)
                ↓
4. Power Automate Flow #1 calls Azure Container API
    - Input: Country + query text
                ↓
5. Azure Container API processes
    - MCP server interfaces with Fabric DW
    - Agentic engine selects execution strategy
    - Returns: business_answer + raw_json
                ↓
6. PowerApps receives response
    - Parse JSON response
    - Extract and type-convert table data
    - Convert markdown to HTML
                ↓
7. PowerApps renders results
    - Display answer section
    - Display key findings
    - Display structured data table
                ↓
8. Power Automate Flow #2 logs event
    - Send CloudEvents JSON to Azure Function
    - Function persists log record
```

### Data Structures

**Input:** Natural language query + employee context (country)
**Intermediate:** API JSON response with tool chain results
**Output:** Formatted answer + structured table data + audit log

---

## 5. Key Capabilities

| Capability | Description |
|------------|-------------|
| **Natural Language Query** | Accept free-form user questions about data |
| **AI-Powered Analysis** | Multi-stage reasoning with adaptive strategies |
| **Structured Results** | Return both narrative answers and tabular data |
| **Performance Optimization** | Direct tool execution for known patterns (100-200ms) |
| **Comprehensive Logging** | CloudEvents-compliant audit trail with performance metrics |
| **User Context Tracking** | Capture email, department, session timestamp |
| **Markdown Processing** | Parse and render AI responses with formatting |
| **Data Extraction** | Parse complex JSON with type conversion for table visualization |

---

## 6. Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Frontend** | Microsoft PowerApps | UI and user interaction |
| **Orchestration** | Power Automate | API integration and logging |
| **Intelligence** | Azure Container + Azure OpenAI | Agentic reasoning |
| **Data Warehouse** | Fabric Data Warehouse | Query backend |
| **Logging** | Azure Function | Event persistence |
| **Query Interface** | MCP (Model Context Protocol) | DW abstraction |
| **Authentication** | Azure AD | Identity and access control |

---

## 7. Integrations

| System | Direction | Purpose | Protocol |
|--------|-----------|---------|----------|
| **Fabric Data Warehouse** | Inbound | Query backend | MCP |
| **Azure OpenAI** | Inbound | AI reasoning | REST API |
| **Azure Function** | Outbound | Logging | HTTP Webhook |
| **Employee Directory** | Inbound | User context lookup | Local data table |

---

## 8. Quality Attributes

### Performance
- **Direct execution:** 100-200ms response time
- **Simple queries:** 3-15 seconds response time
- **Complex queries:** 30-45 seconds response time
- **Typical user expectation:** <5 seconds for most queries

### Reliability
- **Logging:** CloudEvents-compliant audit trail for all queries
- **Error handling:** Graceful fallback from multi-stage to single-stage reasoning
- **Session tracking:** Complete traceability via trace_id and user_email

### Security
- **Authentication:** Azure AD integration for user identity
- **Audit:** Complete event logging with user context
- **Data:** Fabric DW access controlled via MCP server

### Scalability
- **Containerized:** Azure Container deployable to Kubernetes
- **Stateless:** Each query is independent
- **MCP integration:** Can scale reasoning engine independently

---

## 9. Dependencies

### Required Systems
- Microsoft PowerApps environment (with Fabric DW connector)
- Azure Container Registry / AKS for hosting
- Fabric Data Warehouse instance
- Azure OpenAI deployment (gpt-4 or similar)
- Azure Function for logging
- Power Automate tenant

### Data Dependencies
- Employee directory (for country lookup)
- Fabric DW tables (dynamic based on user queries)

### External Services
- Azure OpenAI API (for multi-stage reasoning)
- Fabric DW MCP Server

---

## 10. Future Enhancements

1. **Caching Layer:** Cache Direct Tools patterns for even faster response times
2. **Visualization:** Add chart/graph generation from structured results
3. **Follow-up Queries:** Support conversational context for multi-turn interactions
4. **Export Formats:** Allow export of results to Excel, Power BI
5. **Custom Prompts:** Let power users customize reasoning strategies
6. **Analytics Dashboard:** Aggregate logging data for usage insights

---

## 11. Notes for EA Analysis

- **Capability Mapping:** AI-Powered Query Analysis, Data Intelligence
- **Domain:** Business Intelligence & Analytics
- **Criticality:** High (direct user-facing intelligence tool)
- **Maturity:** Production (active with continuous enhancement)
- **Owner:** [To be filled in]
- **Related Systems:** Fabric DW, Azure OpenAI, Employee Directory
