# MVP9: Collaborative Diagram Storyboarding

## Status: Complete

## Goal

Establish the **conversation pattern** for creating architecture diagrams. The tooling (ingestion, YAML specs, diagram generation) was complete in MVP8. MVP9 defines how human and Claude collaborate to go from intent to output - with mandatory quality gates.

## What's New in MVP9

### 1. Enhanced create-diagram Skill (v1.1.0)

Updated `.claude/skills/create-diagram/SKILL.md` with two mandatory gates that prevent common failures:

| Gate | Phase | Prevents |
|------|-------|----------|
| **Source Document Review** | 1.5 | "Only 3 elements" failure - jumping to design without understanding business context |
| **Output Verification** | 5.5 | "H1/H3 inversion" failure - declaring success without verifying output matches intent |

### 2. Phase 1.5: Source Document Review (MANDATORY)

Before auditing the model (`archi_inputs/`), understand the business context from source documents (`ea_inputs/`):

```
1. Identify source files: "What source files describe this domain?"
2. Read source documents: ea_inputs/02_IT_systems/[domain]/*.txt
3. Extract business context:
   - AS-IS: What systems exist today? Which regions use what?
   - TO-BE: What's the future vision? Target platforms?
   - Timeline: Key dates, migration phases
   - Scope: Regions, departments, process areas
4. Present summary for user validation
5. User confirms before proceeding
```

**Why this matters:** Source files contain the STORY. The model only contains discovered ELEMENTS. You need both.

### 3. Phase 5.5: Output Verification (MANDATORY)

After generation, READ and ANALYZE the `.drawio` output before declaring success:

```
1. Read the generated .drawio file
2. Parse output structure:
   - Rows/columns created (row-*, col-* cell IDs)
   - Element positions (x, y coordinates)
   - Visual treatments (fillColor, strokeWidth, opacity)
3. Compare output against spec intent:
   - Does layout match intended grouping?
   - Are elements positioned correctly?
   - Do emphasis treatments match visual strategy?
4. Identify discrepancies:
   - Semantic inversions (AS-IS where TO-BE should be)
   - Missing elements, wrong grouping, incorrect emphasis
5. Present verification summary
6. User confirms before finalizing
```

**Why this matters:** The spec may be technically correct but semantically wrong. Only by reading actual output can you verify the diagram tells the right story.

### 4. Matrix Layout Algorithm

Added `algorithm: "matrix"` to layout options:

```yaml
layout:
  algorithm: "matrix"  # Two-dimensional grouping

grouping:
  by_property: "Horizon"              # Row headers
  secondary_by_property: "Process"     # Column headers
  order: ["H1", "H2", "H3"]
  secondary_order: ["Sales", "Operations", "Marketing", "Service"]
```

Use for:
- AS-IS → TO-BE transition views
- Capability matrices
- Any view requiring row × column grouping

### 5. Design Epic Pattern (Lightweight)

For multi-diagram narratives, use subfolder organization:

```
ea_inputs/views/
├── quick_overview.yaml           # Ad-hoc single diagram
├── crm-consolidation/            # Design epic folder
│   ├── 01_current_state.yaml
│   ├── 02_integration_complexity.yaml
│   ├── 03_target_state.yaml
│   └── 04_roadmap.yaml
```

**No formal skill yet** - keep it conversational until pattern stabilizes.

## Files Changed

| File | Change |
|------|--------|
| `.claude/skills/create-diagram/SKILL.md` | v1.1.0 - Added Phase 1.5 (Source Review) and Phase 5.5 (Output Verification) |
| `ea_inputs/views/test_mvp9_crm_consolidation.yaml` | Test spec demonstrating full workflow |

## Workflow Summary

```
Phase 1:   Intent Capture (question, audience, decision, key message)
Phase 1.5: Source Document Review ← NEW (read ea_inputs/, extract AS-IS/TO-BE)
Phase 2:   Data Audit (check archi_inputs/)
Phase 3:   Draft Spec (YAML with all sections)
Phase 4:   Review Loop (iterate until approved)
Phase 5:   Generate (call ea_generate_diagram)
Phase 5.5: Output Verification ← NEW (read .drawio, verify against intent)
Phase 6:   Document (update iterations section)
```

## Lessons Learned

### The CRM Consolidation Case Study

This session produced a 10-element CRM consolidation diagram through iterative refinement:

| Attempt | Problem | Root Cause |
|---------|---------|------------|
| 1 | "No elements selected" | Used `Domain: "Commercial"` which doesn't exist |
| 2 | Only 3 elements | Didn't read source docs, missed full AS-IS → TO-BE story |
| 3 | 1 column layout | Grouped by Region but elements lacked Region property |
| 4 | Still 1 column | Used `algorithm: "grid"` not `"matrix"` |
| 5 | H1/H3 inverted | User caught semantic error - AS-IS at bottom, TO-BE at top |
| 6 | Success | Full context + correct algorithm + verified output |

**Key Insight:** Two distinct failure modes require two distinct gates:
- **Context failure** (before design) → Phase 1.5 fixes this
- **Verification failure** (after generation) → Phase 5.5 fixes this

## Test Verification

The final CRM consolidation diagram includes:

**Elements (10):**
- H1 (AS-IS): Salesforce.com, SPT Applications, Enquiries and PO CRM
- H2 (Transitional): Kit Management System, CRM Purchase Order Automation System
- H3 (TO-BE): Microsoft Dynamics CRM, CRM Marketing Module, Online Portal, Customer Analytics Portal, Microsoft Document Intelligence API

**Matrix Layout:**
- 3 rows (Horizon: H1, H2, H3)
- 4 columns (Process: Sales, Operations, Marketing, Service)

**Visual Treatments:**
- Microsoft Dynamics CRM: Green/prominent (strategic target)
- Salesforce.com, SPT Applications: Red/faded (legacy to retire)
- CRM Marketing Module, Customer Analytics Portal: Blue/highlighted (new capabilities)

---

## Bug Fix: Synthetic Element Tracking

### Problem

When a YAML spec references elements that don't exist in the official EA model (`archi_inputs/elements.csv`), the diagram generation would either:
1. Silently skip the missing elements, or
2. Create them but lose track of which elements are "official" vs "synthetic"

This caused confusion when:
- User specifies explicit element names in YAML spec
- Some elements exist in model (from discovery), others don't
- No way to distinguish diagram-only elements from discovered elements

### Solution

Introduced `diagram_elements.csv` to track synthetic elements:

```
archi_inputs/
├── elements.csv          # Official EA model (from discovery)
├── diagram_elements.csv  # Synthetic elements (diagram-only)
├── diagram_properties.csv # Properties for synthetic elements
└── ...
```

**Behavior:**
1. During diagram generation, spec elements are matched against `elements.csv`
2. Elements found in official model → used as-is
3. Elements NOT found → created as synthetic with `diagram-*` ID prefix
4. Synthetic elements written to `diagram_elements.csv` (not `elements.csv`)
5. Both official and synthetic elements included in final diagram

**Example from CRM Consolidation test:**
- Official elements: 4 (from archi_inputs/elements.csv)
- Synthetic elements: 6 (Salesforce.com, SPT Applications, etc.)
- Total in diagram: 10

**diagram_elements.csv content:**
```csv
ID,Type,Name,Documentation
diagram-413724910823,ApplicationComponent,Salesforce.com,Diagram element (not in official EA model)
diagram-c99678c9d181,ApplicationComponent,SPT Applications,Diagram element (not in official EA model)
...
```

### Why This Matters

1. **Data integrity**: Official EA model remains clean (only discovered elements)
2. **Traceability**: Easy to see which elements need to be formally discovered
3. **Flexibility**: Users can create diagrams before full discovery is complete
4. **Auditing**: Clear separation between "truth" and "diagram-specific" elements

---

## Related Documentation

- `docs/ea/MVP8_STATUS.md` - AI-driven diagram layout engine
- `docs/ea/MVP9_PLANNING.md` - Original planning document
- `.claude/skills/create-diagram/SKILL.md` - Enhanced skill with quality gates
