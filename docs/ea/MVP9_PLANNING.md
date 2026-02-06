# MVP9: Collaborative Diagram Storyboarding

## Overview

MVP9 establishes the **conversation pattern** for creating architecture diagrams. The tooling (ingestion, YAML specs, diagram generation) is complete. This documents how human and Claude collaborate to go from intent to output.

## Two-Level Abstraction

| Level | Scope | Output |
|-------|-------|--------|
| **Single View** | One viewpoint, one story | One YAML spec → one .drawio |
| **Design Epic** | Narrative arc, multiple views | Storyboard plan → multiple linked diagrams |

### Single View (`/create-diagram`)

Use for focused, single-purpose diagrams. Skill already exists with full workflow:
1. Intent Capture (question, audience, decision, key message)
2. Data Audit (check archi_inputs/)
3. Draft Spec (YAML with all MVP9 sections)
4. Review Loop (iterate until approved)
5. Generate (call `ea_generate_diagram`)
6. Document (update iterations section)

**Output location:** `ea_inputs/views/[name].yaml` (flat, ad-hoc)

### Design Epic (Lightweight Pattern)

Use when the goal requires multiple diagrams that build a case together.

**Examples:**
- "Make the case for CRM consolidation" → Current State, Problem, Target State, Roadmap
- "Onboard new architect to Commercial domain" → Overview, Integrations, Tech Stack, Support
- "Architecture review board pack" → Strategic Alignment, Technical Debt, Investments

**Output location:** `ea_inputs/views/[epic-name]/` (subfolder containing all related specs)

```
ea_inputs/views/
├── quick_overview.yaml                    # Ad-hoc single diagram
├── crm-consolidation/                     # Design epic folder
│   ├── 01_current_state.yaml
│   ├── 02_integration_complexity.yaml
│   ├── 03_target_state.yaml
│   └── 04_roadmap.yaml
└── jpn-onboarding/                        # Another epic
    ├── 01_domain_overview.yaml
    └── 02_tech_stack.yaml
```

This folder structure:
- Distinguishes ad-hoc diagrams from consolidated epics
- Keeps related views together
- Enables numbered sequencing for narrative order
- Makes epic scope visible at a glance

**Current Approach: No formal skill.** Keep it conversational:

1. **User states goal**: "I need to make the case for X to Y audience"
2. **Claude proposes storyboard**: List of views with purpose of each
3. **User approves/adjusts**: Iterate on the plan before execution
4. **Create epic folder**: `ea_inputs/views/[epic-name]/`
5. **Execute sequentially**: Call `/create-diagram` for each view, saving to epic folder
6. **Maintain coherence**: Views share visual language, build on each other

## Conversation Entry Points

| Style | Example | Best For |
|-------|---------|----------|
| **Goal-first** | "I need to justify the CRM consolidation investment" | When you know the business outcome |
| **Audience-first** | "I'm presenting to the steering committee on platform strategy" | When stakeholder context is primary |
| **Question-first** | "Why do we have 5 CRMs across 3 regions?" | When answering a specific question |
| **Exploratory** | "What stories can we tell about the Commercial domain?" | When discovering what's possible |

## The Brief (Developed Through Conversation)

Before any diagram work, Claude helps develop:

```
WHO:    Audience + what they care about
WHAT:   The question being answered
WHY:    The decision this enables
SO:     The one-sentence takeaway
```

For design epics, this expands to:

```
NARRATIVE ARC:  Setup → Tension → Resolution
VIEWS NEEDED:   List of diagrams with purpose
SEQUENCE:       Order that builds the argument
EPIC FOLDER:    ea_inputs/views/[epic-name]/
```

## When to Formalize into Skill

Create `/design-epic` skill when:
- [ ] Pattern has been used 3-4 times successfully
- [ ] Repeatable structure emerges
- [ ] Workflow stabilizes
- [ ] Maintenance cost justified by frequency of use

Until then, keep it lightweight and conversational.

## Design Decisions

### Why No Skill Yet?

1. **YAGNI** - Haven't proven the need
2. **Pattern not stable** - Don't know what design-epic looks like for this context
3. **Conversation is the value** - Hard part is figuring out what to show, not executing
4. **Skills add maintenance** - Every skill is docs to keep accurate

### Why Subfolder for Epics?

1. **Visual distinction** - Flat files are ad-hoc, folders are planned work
2. **Cohesion** - Related diagrams stay together
3. **Sequencing** - Number prefix shows narrative order
4. **Scope visibility** - Folder name describes the initiative

### Why Document This?

- Persists understanding across sessions
- Avoids re-explaining the workflow
- Captures design rationale
- Provides foundation if skill is later needed

## Example Workflow

**User:** "I need to make the case for CRM consolidation to the steering committee"

**Claude:**
> That needs a storyboard. Here's my proposal:
> 1. **Current State** - 3 CRMs, overlapping coverage (the mess)
> 2. **Problem** - Cost of redundancy, integration complexity
> 3. **Target State** - Single platform vision
> 4. **Roadmap** - Migration phases
>
> I'll create these in `ea_inputs/views/crm-consolidation/`
>
> Does this arc work? Adjust, then we'll create each view.

**User:** "Add a view showing integration complexity specifically"

**Claude:**
> Updated storyboard:
> 1. Current State - 3 CRMs, overlapping coverage
> 2. Integration Complexity - Spaghetti of point-to-point connections
> 3. Problem - Cost breakdown
> 4. Target State - Single platform with hub
> 5. Roadmap - Migration phases
>
> Folder: `ea_inputs/views/crm-consolidation/`
>
> Ready to start with View 1?

**User:** "Yes"

**Claude:** [Creates folder, invokes /create-diagram for View 1, saves as `01_current_state.yaml`]

---

## Diagram Element Data Store Pattern

### Problem

YAML specs reference elements that may not be in the official EA model (`elements.csv`). This happens when:
- Elements are proposed/future (not yet ingested from source documents)
- Elements are for diagram clarity but not officially discovered
- User wants diagram flexibility independent of official model

### Solution: Dual Data Store

Diagram generator uses **two concatenated datasets**:

| Source | Purpose | When to Use |
|--------|---------|-------------|
| **elements.csv** | Official EA model (discovered via ingestion) | Elements from source documents, ingested into system |
| **diagram_elements.csv** | Curated diagram elements (user-defined for this diagram) | Proposed/future elements, clarity elements not yet official |
| **properties.csv** | Official EA properties | Metadata for official elements |
| **diagram_properties.csv** | Curated diagram properties | Metadata for diagram-only elements |

### Data Stocktake Workflow

When loading `drawio_generator` or `diagram_generator`:

1. **Read YAML spec** → Extract element names from `elements.include[].name`
2. **Match against elements.csv** → Mark which elements are official EA
3. **Match against diagram_elements.csv** → Mark which are diagram-only
4. **Calculate gap** → Elements in spec but in neither CSV
5. **Data stocktake report**:
   ```
   YAML Spec Elements: 10
   - In elements.csv (official): 4
   - In diagram_elements.csv (curated): 6
   - Gap (missing): 0

   Status: READY (all elements available)
   ```

### Example: test_mvp9_crm_consolidation

**YAML Spec defines 10 elements:**
- Salesforce.com
- SPT Applications
- Enquiries and PO CRM
- Kit Management System
- CRM Purchase Order Automation System
- Microsoft Dynamics CRM
- CRM Marketing Module
- Online Portal
- Customer Analytics Portal
- Microsoft Document Intelligence API

**Data Stocktake:**
```
✓ 4 found in elements.csv (official EA model)
  - Microsoft Dynamics CRM (id-f5619ffd7b65)
  - Microsoft Document Intelligence (id-2e50916cb555)
  - Medline Online Portal (id-59051872c987)
  - Purchase Order Automation (id-ef8339ce9f2e)

→ 6 need to be added to diagram_elements.csv (curated for this diagram)
  - Salesforce.com
  - SPT Applications
  - Enquiries and PO CRM
  - Kit Management System
  - CRM Purchase Order Automation System
  - CRM Marketing Module
```

**Generator concatenates both files** → Renders complete 10-element diagram

### Key Principles

1. **Official model stays clean** - Only discovered/ingested elements in `elements.csv`
2. **Diagrams stay flexible** - Can include proposed/future elements via `diagram_elements.csv`
3. **No coupling** - Diagram specs don't force official model changes
4. **Stocktake first** - Always verify what's missing before generation
5. **User adds missing elements** - Populate `diagram_elements.csv` with non-official elements

### When to Create diagram_elements.csv Entries

Create when a YAML spec references elements that:
- Are not yet in `elements.csv` (not yet officially ingested)
- But ARE needed for the diagram story (for clarity, future state, etc.)
- User explicitly wants them included

Example entry for `diagram_elements.csv`:
```csv
ID,Type,Name,Documentation
diagram-salesforce-jpn,ApplicationComponent,Salesforce.com,Current JPN CRM system to be retired post-migration
diagram-spt-anz,ApplicationComponent,SPT Applications,Legacy ANZ sales support system
```

Example entry for `diagram_properties.csv`:
```csv
ID,Key,Value
diagram-salesforce-jpn,Horizon,H1
diagram-salesforce-jpn,Region,JPN
diagram-salesforce-jpn,Domain,Commercial
diagram-spt-anz,Horizon,H1
diagram-spt-anz,Region,ANZ
diagram-spt-anz,Domain,Commercial
```

---

## Related Documentation

- `docs/ea/MVP8_STATUS.md` - AI-driven diagram layout engine
- `docs/ea/MVP7_STATUS.md` - View specification schema
- `.claude/skills/create-diagram/SKILL.md` - Single view workflow
