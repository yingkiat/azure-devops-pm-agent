# EA Tool Assessment

**Date:** 2026-01-03
**Purpose:** Evaluate current state of this repo as an EA catalogue, diagramming, and dashboarding tool

---

## Executive Summary

**What we have:** A solid **EA discovery and documentation tool** - excellent at ingesting messy data, extracting structure, and generating diagrams.

**What we don't have:** An **EA management platform** - no live dashboards, no portfolio analytics, no what-if analysis.

---

## Current Capabilities (Strengths)

### 1. Data Ingestion - Production Ready

| Format | Method | Features |
|--------|--------|----------|
| Text (.txt) | LLM extraction | 6000 token batching |
| CSV (.csv) | Schema extraction | Column preservation |
| Excel (.xlsx) | Auto-convert to CSV | Full attribute capture |
| Markdown (.md) | Free-form + headers | Batched processing |
| Images (.png, .jpg) | Vision LLM | Checksum caching |
| YAML specs | View parsing | Intent-driven |

**Smart features:**
- Batch processing (70-90% API call reduction)
- File change detection (skip unchanged)
- Provenance tracking (audit trail per element)

### 2. Catalogue Management - Production Ready

**Current Model Size:**
- 31 ApplicationComponent elements
- 10 Capability elements
- 5 BusinessProcess elements
- 2 DataObject elements
- 1 Node element
- 20 relationships (Serving, Flow, Access, Composition)

**Metadata Properties:**
- Horizon (H1, H2, H3 - technology adoption timeline)
- Domain (Sales, Operations, Marketing, Customer Service, IT, Analytics)
- Sub-Domain, Region, Criticality
- Technology Stack, Lifecycle Status
- Custom CSV attributes (preserved automatically)

**Features:**
- Flexible hierarchical organization (Region → Domain → Sub-Domain)
- Dynamic filtering by property values
- Multiple output formats (CSV, markdown, HTML)
- Entity resolution (no duplicates)
- Incremental model building

### 3. Diagramming - Production Ready

**Output Formats:**

| Format | Tool | Use Case |
|--------|------|----------|
| draw.io (.drawio) | MVP8 Generator | Editable diagrams |
| ArchiMate XML | Model Exchange | Archi tool import |
| Mermaid (.mermaid) | Code generator | Technical docs |
| Presentation diagrams | AI layout | Executive slides |

**Layout Algorithms:**
- `grid` - Simple tabular positioning
- `column` - Vertical stacking with grouping
- `matrix` - Two-dimensional (Horizon × Process)
- Hierarchical/layered
- Nested columnar (Region × Sub-Domain)

**Visual Features:**
- ArchiMate layer colors (Strategy, Business, Application, Technology)
- Lifecycle Status colors (Strategic=green, Sunset=red, Maintain=orange)
- Relationship line styles (Solid/dashed, arrow types)
- Dynamic element sizing (120-300px based on name)
- Nested container grouping
- Annotations and callouts

**Current Diagrams:**
- 10 draw.io diagrams in `ea_diagrams/`
- Covering: CRM consolidation, operations landscape, capability maps, transformation roadmaps

### 4. View Specifications - Production Ready

**YAML Schema (MVP9):**
```yaml
intent:      # Question, audience, decision, key message
story:       # Setup, tension, insight
visual:      # Emphasis treatments, grouping rationale, color strategy
elements:    # Explicit selection or WHERE clauses with overrides
relationships:
grouping:    # Primary + secondary property, order
layout:      # Algorithm (grid/column/matrix)
annotations: # Callouts near elements
output:      # Format (drawio/archi/both)
iterations:  # Learning log
```

**Skill Workflow (create-diagram v1.1.0):**
- Phase 1: Intent Capture
- Phase 1.5: Source Document Review (MANDATORY)
- Phase 2: Data Audit
- Phase 3: Draft Spec
- Phase 4: Review Loop
- Phase 5: Generate
- Phase 5.5: Output Verification (MANDATORY)
- Phase 6: Document

### 5. PM Integration - Production Ready

**Azure DevOps Tools:**
- Work items: get, create, update, WIQL queries
- Pull requests: query, batch analysis
- Projects/repos: listing, README access
- Batch operations: multi-project health analysis

**Analytics:**
- Work item aging, status distribution
- PR review cycle time
- Team velocity and capacity
- Project health scores (0-100)
- Critical issues and bottleneck detection

**Output:**
- CLI reports (JSON)
- Azure DevOps Wiki articles
- Natural language summaries

### 6. Architecture Strengths

| Principle | Implementation |
|-----------|----------------|
| Prompt-driven | All logic in `prompts/`, no hardcoded rules |
| Zero maintenance | LLM handles schema variations |
| Open formats | ArchiMate XML, draw.io (portable) |
| Provenance | Full audit trail in provenance.csv |
| Version control | YAML specs in git |

---

## Gaps (Weaknesses)

### Critical EA Gaps

| Gap | Impact | Current State |
|-----|--------|---------------|
| **No Visual Dashboard** | Can't show live portfolio health to stakeholders | CLI/JSON reports only |
| **No Gap Analysis** | Can't systematically compare AS-IS vs TO-BE | Manual YAML comparison |
| **No Cost/Resource Model** | Can't answer "what does this cost?" | No financial data layer |
| **No Risk/Compliance Scoring** | Can't prioritize by business risk | Properties exist but no scoring engine |
| **No Change Impact Analysis** | Can't answer "what breaks if X changes?" | Relationships exist but no traversal |
| **No Dependency Tracing** | Can't follow transitive relationships | Only direct relationships |
| **No Technology Reference Model** | Can't map apps to standard tech patterns | Ad-hoc tech stack property |
| **No Business Capability Hierarchy** | 10 capabilities but flat, no levels | No L1/L2/L3 structure |

### UX Gaps

| Gap | Impact |
|-----|--------|
| **No UI** | Everything via Claude Code / CLI - not accessible to non-technical users |
| **No Drag-and-Drop** | Can't visually edit diagrams in-tool |
| **No Real-Time Collaboration** | Single user, no concurrent editing |
| **No Form-Based Entry** | Must write text or edit CSV |
| **No Search/Browse** | Can't explore catalogue interactively |

### Data Model Gaps

| Gap | Impact |
|-----|--------|
| **No 3+ Level Nesting** | Only 2-level grouping (Region × Domain) |
| **No Data Flow Diagrams** | Relationships exist but no DFD generation |
| **No Interface/API Catalogue** | Integration points not first-class |
| **No Standards Mapping** | Can't map to TOGAF, Zachman, etc. |

---

## Maturity Model Position

```
Level 1: Documentation     [CURRENT POSITION]
         - Catalogue apps, capabilities, relationships
         - Generate static diagrams
         - Export to Archi tool
         - Track provenance

Level 2: Analysis          [PARTIAL - Next Priority]
         - Gap analysis (AS-IS vs TO-BE)
         - Dependency tracing
         - Change impact assessment
         - What-if scenarios

Level 3: Governance        [NOT STARTED]
         - Risk scoring and compliance
         - Standards enforcement
         - Approval workflows
         - Policy automation

Level 4: Optimization      [NOT STARTED]
         - Cost modeling
         - Resource optimization
         - Scenario planning
         - Investment prioritization
```

---

## Recommended Priorities

### Quick Wins (Low Effort, Use Existing Data)

| Priority | Capability | Effort | Why |
|----------|------------|--------|-----|
| 1 | **Gap Analysis Tool** | Low | Compare AS-IS (H1) vs TO-BE (H3) elements, show additions/removals/changes |
| 2 | **Risk/Criticality Scoring** | Low | Score elements by existing properties (Lifecycle Status, Criticality, Domain) |
| 3 | **Dependency Graph Query** | Medium | Traverse relationships to answer "what uses X?" and "what does X depend on?" |

### Medium Effort (New Features)

| Priority | Capability | Effort | Why |
|----------|------------|--------|-----|
| 4 | **HTML Dashboard** | Medium | Static HTML portfolio view, regenerated on demand |
| 5 | **Business Capability Hierarchy** | Medium | L1/L2/L3 capability model with app mapping |
| 6 | **Interface/API Catalogue** | Medium | First-class integration point tracking |

### High Effort (Platform Evolution)

| Priority | Capability | Effort | Why |
|----------|------------|--------|-----|
| 7 | **Cost Model Integration** | High | Financial data layer, TCO calculations |
| 8 | **Interactive Web UI** | High | Browse/search/edit without CLI |
| 9 | **Real-Time Collaboration** | High | Multi-user, concurrent editing |

---

## Data Assets Summary

### Current Files

```
archi_inputs/                    # Single source of truth
├── elements.csv                 # 31 apps, 10 capabilities, 5 processes
├── properties.csv               # All metadata (Horizon, Domain, etc.)
├── relations.csv                # 20 relationships
├── views.csv                    # View definitions with positions
├── provenance.csv               # Element source tracking
└── model.xml                    # ArchiMate 3.0 Model Exchange

ea_inputs/                       # Source documents
├── 01_company_context/          # Company info
├── 02_IT_systems/               # 15 files (txt, xlsx, md, images)
├── 03_global_standards/         # Policies, standards
├── images/                      # Diagrams for vision extraction
└── views/                       # 7 YAML view specifications

ea_diagrams/                     # Generated outputs
└── *.drawio                     # 10 draw.io diagrams
```

### MCP Tools Exposed (16)

**EA Discovery (7):**
- ea_discover, ea_discover_directory, ea_ingest_images, ea_clear_image_cache
- ea_generate_archi, ea_get_data_summary, ea_reset_model

**View & Diagramming (7):**
- ea_list_view_specs, ea_list_available_elements
- ea_generate_views_from_specs, ea_finalize_views
- ea_generate_diagram, ea_generate_presentation_diagram, ea_generate_mermaid

**PM (8):**
- get_work_items, create_work_item, update_work_item
- get_pull_requests, get_projects, get_repositories, get_readme
- batch_project_overview, batch_work_item_queries, batch_pull_requests

---

## Next Session Topics

1. **Gap Analysis MVP** - What's the minimum viable implementation?
2. **Dashboard Options** - Static HTML vs live web app vs Power BI integration?
3. **Capability Hierarchy** - Import existing capability model or build from scratch?
4. **Priority Validation** - Which gaps matter most for your use cases?

---

## Related Documentation

- `docs/ea/MVP6_STATUS.md` - View specification schema
- `docs/ea/MVP7_STATUS.md` - AI-driven diagram layout
- `docs/ea/MVP8_STATUS.md` - Extended YAML schema, ArchiMate colors
- `docs/ea/MVP9_STATUS.md` - Collaborative storyboarding workflow
- `.claude/skills/create-diagram/SKILL.md` - Diagram creation skill v1.1.0
