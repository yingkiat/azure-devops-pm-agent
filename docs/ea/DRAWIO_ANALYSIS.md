# Draw.io Diagram Generation Analysis

## Executive Summary

The current draw.io generation treats the canvas as a spreadsheet, not as a visual medium. Elements are dumped in a fixed 4-column grid with identical styling, truncated names, and no ArchiMate notation.

---

## Root Cause: Hard-Coded Layout Logic

### File: `src/ea/presentation_diagram_generator.py` (lines 155-184)

```python
cols = 4  # HARD-CODED - always 4 columns
for idx, elem_id in enumerate(group_elem_ids):
    row = idx // cols
    col = idx % cols
    x = 80 + col * 280     # Fixed 280px horizontal spacing
    y = container_y + 60 + row * 100  # Fixed 100px vertical spacing

    drawio_elem = DrawIOElement(
        id=elem_id,
        name=elem['name'][:25],  # TRUNCATED TO 25 CHARS!
        width=200,               # FIXED SIZE
        height=60,               # FIXED SIZE
        ...
    )
```

### File: `src/ea/drawio_export.py` (lines 191-193)

Every element gets identical styling:

```python
style = (f'rounded=1;whiteSpace=wrap;html=1;'
        f'fillColor={elem.color};strokeColor=#666666;'
        f'fontSize=11;fontFamily=Verdana;aspect=fixed;')
```

### File: `src/ea/drawio_export.py` (lines 216-218)

Every relationship gets identical styling:

```python
style = (f'edgeStyle=orthogonalEdgeStyle;rounded=0;'
        f'orthogonalLoop=1;jettySize=auto;html=1;'
        f'strokeColor=#666666;fontSize=10;')
```

---

## Problems Identified

### 1. Name Truncation
- Names cut to 25 characters
- "Microsoft Dynamics 365 Customer Engagement" becomes "Microsoft Dynamics 365 Cu"
- No ellipsis or indication of truncation

### 2. Fixed Element Sizing
- All elements: 200x60 pixels
- No adaptation to name length
- No importance-based sizing

### 3. Fixed Grid Layout
- Always 4 columns per container
- 280px horizontal spacing, 100px vertical
- No consideration of relationships
- No visual hierarchy

### 4. No ArchiMate Notation
- All elements are rounded rectangles
- No differentiation between:
  - ApplicationComponent
  - Capability
  - BusinessProcess
  - DataObject
  - TechnologyService
- No icons or stereotypes

### 5. Identical Relationship Styling
- All edges: gray orthogonal lines
- No differentiation between:
  - Serving (should be solid with hollow arrow)
  - Flow (should be dashed with filled arrow)
  - Composition (should have diamond)
  - Realization (should be dashed)

### 6. Lifecycle-Only Coloring
- Colors based only on Lifecycle Status property
- Missing layer-based colors (Business=yellow, Application=blue, Technology=green)
- No criticality indication

### 7. Container Layout
- Swimlanes stacked vertically
- Height = max(200, element_count * 100)
- No nesting intelligence
- No relationship-aware positioning

---

## Current vs Expected Output

| Aspect | Current | Should Be |
|--------|---------|-----------|
| Layout | Fixed 4-column grid | Relationship-aware, hierarchical |
| Element size | Fixed 200x60 | Dynamic based on name + importance |
| Element shape | Rounded rectangle | ArchiMate-specific shapes |
| Colors | Lifecycle only | Layer + lifecycle + criticality |
| Relationships | All gray lines | Type-specific styling |
| Containers | Stacked vertically | Nested by relationship density |
| Names | Truncated 25 chars | Full names with wrapping |

---

## Quality Assessment

| Aspect | Score | Notes |
|--------|-------|-------|
| Element Positioning | 2/10 | Simple grid, no intelligence |
| Shape Notation | 1/10 | All rounded rectangles |
| Relationship Rendering | 2/10 | All identical gray lines |
| Color Styling | 4/10 | Lifecycle colors only |
| Layout Intelligence | 3/10 | No relationship consideration |
| Text Handling | 2/10 | 25-char truncation |
| Overall Polish | 2/10 | Functional but amateurish |

---

## Improvement Options

### Option 1: Quick Fixes (Low Effort)
- Remove 25-character name truncation
- Dynamic element width based on name length
- Different colors for relationship types (Serving=blue, Flow=orange, etc.)
- Adjust font sizes for longer names

### Option 2: Layout Engine Overhaul (Medium Effort)
- Port MVP7 AI layout engine to draw.io path
- Or implement force-directed layout algorithm
- Relationship-aware element positioning
- Minimize edge crossings
- Intelligent container nesting

### Option 3: ArchiMate Notation (Medium Effort)
- Implement proper shapes per element type
- Add stereotype labels (<<Service>>, <<Legacy>>)
- Layer-based coloring (Business/Application/Technology/Physical)
- Arrow type differentiation per relationship type
- Add icons where appropriate

### Option 4: Full Redesign (High Effort)
- Combine all above improvements
- Add configurable styling API (YAML-based themes)
- Diagram metadata (title, legend, viewpoint indicator)
- Smart relationship routing (avoid overlaps)
- Presentation-ready output with proper visual hierarchy

---

## Key Files to Modify

1. `src/ea/presentation_diagram_generator.py`
   - Layout algorithm (lines 155-186)
   - Element sizing logic
   - Container positioning

2. `src/ea/drawio_export.py`
   - Element styling (lines 191-194)
   - Edge styling (lines 216-219)
   - ArchiMate shape definitions

3. New file needed: `src/ea/archimate_shapes.py`
   - SVG/shape definitions for each ArchiMate type
   - Color palettes per layer
   - Relationship styling rules

---

## Architecture Issue: Two Disconnected Systems

The codebase has two parallel diagram systems that don't share code:

1. **Draw.io Export** (presentation_diagram_generator.py + drawio_export.py)
   - Simple 4-column grid
   - Used for presentation diagrams
   - NOT exposed in MCP properly

2. **ArchiMate XML Export** (archi_export.py + archi_layouts.py + archi_layout_ai.py)
   - Has MVP7 AI-driven layout
   - Has hierarchical/layered layout options
   - Used for Archi tool import

The MVP7 AI layout engine exists but is NOT used for draw.io generation. This is a missed opportunity.

---

## Recommendation

Start with **Option 1 (Quick Fixes)** to get immediate improvement, then proceed to **Option 2 (Layout Engine)** by porting the MVP7 AI layout to draw.io generation.

The ArchiMate notation (Option 3) can be done in parallel but requires more research into draw.io's shape capabilities.

---

## MVP8 Vision: AI Diagram Intelligence

### Current Problem (MVP7)

MVP7 AI only calculates coordinates. It receives pre-structured data and figures out WHERE to place boxes. It does NOT understand WHY the diagram exists or what story to tell.

### Your Vision

AI that: CONTEMPLATES (understands intent) → PLANS (designs layout) → DRAWS (outputs XML)

### Implementation Options

**Option A: Two-Stage AI Pipeline**
- Stage 1: LLM receives request + data → outputs structured "diagram plan" as JSON
- Stage 2: LLM receives plan + target format → outputs final XML (Archi or draw.io)
- Pro: Clean separation, plan can be reviewed/edited, testable
- Con: Two API calls

**Option B: Single Comprehensive Prompt**
- One big prompt handles all three phases in one call
- Pro: Simpler pipeline, one API call
- Con: Harder to debug, no intermediate review

**Option C: Human-in-the-Loop (Interactive)**
- Claude Code conversation handles contemplation and planning
- MCP tools execute the drawing based on conversation decisions
- Pro: Maximum control, iterative refinement
- Con: Requires conversation, not fully automated

### User Feedback

**The YAML IS the plan.** The `ea_inputs/views/*.yaml` files already serve as the blueprint. No need for a separate "plan JSON" stage.

Two possibilities:
1. YAML is sufficient → AI reads it and draws
2. YAML is insufficient → Extend the YAML schema to capture more (intent, emphasis, curation)

Either way, YAML remains the single readable artifact for both human and AI to articulate thought, intent, planning, and drawing.

---

## Revised Approach: Extended YAML as Blueprint

### Current YAML Schema (MVP6)

```yaml
name: "View Name"
description: "..."
elements:
  where:
    type: ApplicationComponent
    Domain: Operations
grouping:
  by_property: Region
  secondary_by_property: Sub-Domain
layout:
  algorithm: column
  spacing_y: 40
```

### Extended YAML Schema (MVP8)

Add sections for intent, curation, and visual emphasis:

```yaml
name: "CRM Modernization Roadmap"
description: "Shows transformation from legacy to strategic CRM"

# NEW: Diagram intent - what story to tell
intent:
  story: "transformation"  # transformation | comparison | landscape | integration
  audience: "executive"    # executive | technical | operational
  key_message: "Migration path from Dynamics to Salesforce"

# NEW: Curation - what to include/exclude
curation:
  include:
    - where: { Lifecycle Status: [Current, Strategic] }
    - where: { Domain: Commercial }
  exclude:
    - where: { Criticality: Low }
  max_elements: 20  # AI picks most important if over limit

# NEW: Visual emphasis
emphasis:
  highlight:
    - where: { Lifecycle Status: Strategic }
      style: { size: large, border: bold }
  de_emphasize:
    - where: { Lifecycle Status: Sunset }
      style: { opacity: 0.5 }

# Existing: Element selection
elements:
  where:
    type: ApplicationComponent
    Domain: Commercial

# Existing: Grouping
grouping:
  by_property: "Lifecycle Status"
  order: [Current, Strategic]

# Existing: Layout
layout:
  algorithm: column
  spacing_y: 40

# NEW: Output format
output:
  format: drawio  # archi | drawio | both
  notation: archimate  # archimate | simple
```

### Workflow

```
Human writes/edits YAML → AI reads YAML → AI generates Archi or draw.io
         ↑                                           |
         └───────── Human reviews output ────────────┘
```

The YAML is:
- Version controlled (git)
- Human readable and editable
- Machine parseable
- The single source of truth for diagram intent

### Implementation Steps

1. **Extend YAML schema** - Add `intent`, `curation`, `emphasis`, `output` sections
2. **Update view parser** - Read new sections in `src/ea/archi_views.py` or equivalent
3. **Create unified generator** - Single entry point that reads YAML, generates either format
4. **AI contemplation via prompt** - Prompt interprets intent/curation/emphasis to make layout decisions

### Key Insight

The "contemplation" phase doesn't need to be a separate LLM call. It happens when the AI reads and interprets the YAML's intent section. The YAML IS the externalized thought process.

---

## Grounding in ArchiMate (But Not Limited By It)

### Principle

Use ArchiMate as the foundation:
- Element types (ApplicationComponent, BusinessCapability, etc.)
- Relationship types (Serving, Flow, Realization, etc.)
- Layer colors (Business=yellow, Application=blue, Technology=green)
- Notation symbols (standard shapes per element type)

But don't be constrained to only the 23 official viewpoints. Custom views are valid:
- Business Function Stream → Capability Maturity mapping
- Technology Lifecycle → Replacement Roadmap
- Regional Application Landscape with criticality overlay

### ArchiMate Fundamentals (AI Must Know)

**Layers:**
- Strategy (purple): Resource, Capability, Course of Action
- Business (yellow): Process, Function, Service, Actor, Role
- Application (blue): Component, Service, Interface, Data Object
- Technology (green): Node, Device, System Software, Artifact
- Physical (brown): Equipment, Facility, Material

**Core Relationships:**
- Structural: Composition, Aggregation, Assignment, Realization
- Dependency: Serving, Access, Influence
- Dynamic: Triggering, Flow
- Other: Association, Specialization

**Notation:**
- Each element type has a specific shape (rectangle with icon, rounded, etc.)
- Relationship types have specific line styles (solid, dashed, arrows, diamonds)

### YAML Schema (ArchiMate-Grounded, Flexible)

```yaml
name: "Business Capability Maturity by Function Stream"

# Optional: Use standard viewpoint as base
viewpoint: null  # Or "Application Cooperation", "Layered", etc.

# What to show
elements:
  where:
    type: [BusinessCapability, ApplicationComponent]
    Domain: Operations

# How to organize
grouping:
  by_property: "Function Stream"
  secondary_by_property: "Maturity Level"
  order: [Plan, Source, Make, Deliver, Return]

# Visual treatment
presentation:
  color_by: "Maturity Level"  # Uses property value for color mapping
  size_by: "Criticality"      # High=large, Low=small

# Spatial arrangement
layout:
  algorithm: matrix           # grid | column | matrix | hierarchical
  rows: "Function Stream"
  columns: "Maturity Level"

# Output
output:
  format: drawio
  notation: archimate         # Use proper ArchiMate shapes
```

### AI Responsibilities

1. **Understand ArchiMate** - Know element types, relationships, layers, colors
2. **Interpret YAML** - Read scope, grouping, presentation, layout
3. **Apply notation** - Use correct shapes for element types
4. **Generate output** - Archi XML or draw.io with proper styling

### Key Difference from MVP7

MVP7: AI calculates coordinates only
MVP8: AI understands the semantic meaning and applies proper notation + intelligent layout
