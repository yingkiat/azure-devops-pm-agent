# MVP8: AI-Driven Diagram Generation

## Status: Implementation Complete

## Goal

AI that contemplates, plans, and draws diagrams - outputting to either Archi XML or draw.io format. Grounded in ArchiMate notation but not limited to official viewpoints.

## What's New in MVP8

### 1. ArchiMate Layer Colors

Standard ArchiMate layer colors now applied automatically:

| Layer | Color | Element Types |
|-------|-------|---------------|
| Strategy | #F5DEAA | Capability, Resource, CourseOfAction |
| Business | #FFFFB5 | BusinessProcess, BusinessFunction, BusinessService |
| Application | #B5D4E8 | ApplicationComponent, ApplicationService, DataObject |
| Technology | #C9E7CB | TechnologyService, Node, Device, SystemSoftware |
| Physical | #F2D1C9 | Equipment, Facility, Material |

Lifecycle Status colors (Strategic, Maintain, Sunset, New) take priority when available.

### 2. Relationship Line Styles

Different ArchiMate relationships now have distinct visual styling:

| Type | Line Style | Arrow |
|------|------------|-------|
| Serving | Solid | Open arrow |
| Flow | Dashed | Filled arrow |
| Composition | Solid | Filled diamond |
| Aggregation | Solid | Hollow diamond |
| Realization | Dashed | Hollow triangle |
| Triggering | Solid | Filled arrow |

### 3. Dynamic Element Sizing

Element width now calculated from name length:
- Minimum: 120px
- Maximum: 300px
- No more 25-character truncation

### 4. Extended YAML Schema

New sections for controlling diagram output:

```yaml
view:
  name: "CRM Application Landscape"
  documentation: "Shows CRM applications by region"

# NEW: Presentation hints
presentation:
  color_by: "Lifecycle Status"    # Property to use for coloring
  size_by: "Business Criticality" # Property to use for sizing (future)
  highlight:
    - where: { Lifecycle Status: Strategic }
      style: { border: bold, size: large }
  notation: archimate             # archimate | simple

# Existing: Element selection
elements:
  where:
    type: ApplicationComponent
    Domain: Commercial

# Existing: Grouping
grouping:
  by_property: Region
  secondary_by_property: Sub-Domain
  order: [ANZ, JPN, AEM]

# Existing: Layout
layout:
  algorithm: column
  spacing_y: 40

# NEW: Output format
output:
  format: drawio                  # archi | drawio | both
```

### 5. Unified Diagram Generator

New `DiagramGenerator` class that:
1. Reads extended YAML spec
2. Loads ArchiMate data (elements, relations, properties)
3. Applies presentation hints (color_by, etc.)
4. Calls AI for intelligent layout
5. Generates output in requested format

### 6. New MCP Tool

```
ea_generate_diagram(spec_path)
```

Generates diagram from YAML spec with AI-driven layout. Outputs to `ea_diagrams/` directory.

## Files Changed

| File | Change |
|------|--------|
| `src/ea/drawio_export.py` | Added layer colors, relationship styles, dynamic sizing |
| `src/ea/view_builder.py` | Parse presentation and output YAML sections |
| `src/ea/diagram_generator.py` | NEW - Unified generator with AI layout |
| `src/mcp_server.py` | Added ea_generate_diagram tool |
| `prompts/ea/drawio_diagram_layout.md` | NEW - AI prompt for draw.io layout |

## Usage

### Generate draw.io diagram with AI layout:

```
ea_generate_diagram("ea_inputs/views/crm_landscape.yaml")
```

### YAML spec with MVP8 features:

```yaml
view:
  name: "Commercial CRM Landscape"

elements:
  where:
    type: ApplicationComponent
    Domain: Commercial

grouping:
  by_property: Region
  order: [ANZ, JPN, AEM]

presentation:
  color_by: "Lifecycle Status"

output:
  format: drawio
```

## Architecture

```
YAML Spec (extended)
       |
       v
+----------------------+
|  DiagramGenerator    |
|  - Load spec         |
|  - Select elements   |
|  - Enrich with color |
|  - Pass grouping_spec|  <-- AI handles grouping
+----------------------+
       |
       v
+----------------------+
|  AI Layout Engine    |
|  - Read prompt       |
|  - Group elements    |  <-- AI-driven grouping
|  - Position elements |
|  - Call Azure OpenAI |
|  - Generate XML      |
+----------------------+
       |
       v
+----------------------+
|  Output              |
|  - draw.io XML       |
|  - ArchiMate XML     |
+----------------------+
```

**Key Design Principle:** Python handles data loading and element selection. AI handles layout decisions including grouping. This makes the system more flexible and maintainable.

## Fallback Behavior

If AI layout fails:
- Falls back to deterministic 4-column grid layout
- Still applies ArchiMate colors and relationship styles
- Logs warning message

---

## Bug Fixes (2025-12-22)

### Issue: Diagram Elements and Narrative Mismatch

**Symptoms:**
- Narrative text said "9 elements, 1 relationship"
- Diagram only showed 5 boxes in 1 swimlane (ANZ)
- Zero relationship connectors visible
- Missing regions: Japan, Australia

### Root Cause Analysis

| Bug | Description | Impact |
|-----|-------------|--------|
| Group Filtering | `_organize_groups()` iterated over `order` list, not actual data. "JPN" in order didn't match "Japan" in data. | 4 elements dropped silently |
| Missing Groups | Groups with values not in order list were never added | Japan, Australia swimlanes missing |
| No Edge Rendering | Relationship connector only renders if both endpoints exist | Flow connector invisible |
| Narrative Disconnect | Narrative generated from selected elements, not rendered elements | Counts didn't match visual |

### Solution: AI-Driven Grouping

**Architectural Change:** Moved grouping logic from Python to AI.

**Before:**
```
YAML Spec → Python (organize_groups) → Pre-computed groups → AI Layout → XML
                    ↓
            Bug: drops groups before AI sees them
```

**After:**
```
YAML Spec → Python (select elements) → Raw elements + grouping_spec → AI Layout → XML
                                                    ↓
                                       AI handles grouping intelligently
```

### Files Changed

| File | Change |
|------|--------|
| `src/ea/diagram_generator.py` | Pass raw `grouping_spec` to AI instead of pre-computed groups |
| `src/ea/diagram_generator.py` | Fixed fallback `_organize_groups` to include ALL groups found in data |
| `src/ea/diagram_generator.py` | Fixed element Y positioning to use relative coordinates |
| `prompts/ea/drawio_diagram_layout.md` | Updated prompt to explain `grouping_spec` - AI now handles grouping |

### Key Code Changes

**1. `_build_layout_data()` - Pass grouping spec, not pre-computed groups:**
```python
# Before
'groups': groups,  # Pre-computed, filtered groups

# After
'grouping_spec': grouping_spec,  # Raw spec - AI decides grouping
```

**2. `_organize_groups()` fallback - Include all groups:**
```python
# Before
ordered_keys = order if order else sorted(primary_groups.keys())
for primary_val in ordered_keys:
    if primary_val not in primary_groups:
        continue  # Drops groups not in order list!

# After
if order:
    ordered_keys = [k for k in order if k in primary_groups]
    remaining = [k for k in primary_groups.keys() if k not in order]
    ordered_keys.extend(sorted(remaining))  # Include ALL groups
```

**3. AI Prompt - Grouping instructions:**
```markdown
**Your Task:**
1. Group elements by the value of `by_property`
2. Handle variations intelligently: "JPN" matches "Japan"
3. Create container for EACH unique value in data
4. Include ALL elements - never drop because name doesn't match order
```

### Verification

**Before Fix:**
```
Elements: 5 boxes | Relationships: 0 connectors
Swimlanes: ANZ only
```

**After Fix:**
```
Elements: 9 boxes | Relationships: 1 connector (MedPack → MedReports)
Swimlanes: ANZ (5), Australia (2), Japan (2)
Narrative matches visual
```

### Benefits of AI-Driven Grouping

| Aspect | Before | After |
|--------|--------|-------|
| Flexibility | Exact string match required | AI handles variations |
| Maintenance | Edit Python code | Edit prompt |
| Error Handling | Silent drops | AI includes all |
| Fuzzy Matching | None | "JPN" → "Japan" |

---

---

## MVP8.1 Enhancements (2025-12-22)

### 1. Relationship-Based Structure

New `structure` section enables parent-child hierarchy based on ArchiMate relationships:

```yaml
structure:
  parent:
    type: "Capability"
  children:
    type: "ApplicationComponent"
    via: "Serving"           # Relationship type
    direction: "inbound"     # Apps point TO capabilities
  layout: column             # column | grid
```

**How it works:**
- Finds parent elements matching `parent.type`
- For each parent, finds children connected via specified relationship
- `direction: inbound` means children point TO parent (App -Serving-> Capability)
- `direction: outbound` means parent points TO children (BusinessFunction -Composition-> Capability)
- Children are auto-discovered and added to the view

**Visual Result:**
```
┌─ Order Management (Capability) ─────────────────┐
│ ┌──────────────┐ ┌──────────────┐               │
│ │ QAD ERP      │ │ SAP APO      │               │
│ └──────────────┘ └──────────────┘               │
└─────────────────────────────────────────────────┘
```

### 2. Annotations (Simple Labels)

New `annotations` section adds text labels to elements:

```yaml
annotations:
  - text: "Strategic Platform"
    near: "UDW Agent"

  - text: "Sunset Q2 2025"
    near: "MedQuote"
```

**Rendering:**
- Labels appear as small italic text above/beside the target element
- Light background, no border
- Non-overlapping placement

### 3. Combined Mode

Structure and grouping can be combined for 3-level nesting:

```yaml
# 3-level: Group (by Domain) → Parent (Capability) → Children (Applications)
structure:
  parent: { type: "Capability" }
  children: { type: "ApplicationComponent", via: "Serving", direction: "inbound" }

grouping:
  by_property: "Domain"
  order: ["Operations", "IT Security", "Business Intelligence"]
```

### Files Changed

| File | Change |
|------|--------|
| `src/ea/view_builder.py` | Parse `structure` and `annotations` sections |
| `src/ea/diagram_generator.py` | `_build_structure_hierarchy()` method, pass to AI |
| `prompts/ea/drawio_diagram_layout.md` | Document structure and annotation handling |

### Test View Spec

`ea_inputs/views/test_mvp8_capability_map.yaml` - Tests all MVP8.1 features

---

## How AI Diagram Generation Works

### The Two-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  PYTHON LAYER (Deterministic)                                   │
│  - Load YAML spec                                               │
│  - Select elements from archi_inputs/elements.csv               │
│  - Filter relationships from archi_inputs/relations.csv         │
│  - Build structure hierarchy (parent-child via relationships)    │
│  - Enrich elements with colors based on type/lifecycle          │
│  - Package data as JSON for AI                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  AI LAYER (Creative)                                            │
│  - Receives: elements[], relationships[], grouping_spec,        │
│              structure_hierarchy, annotations, constraints       │
│  - Decides: container positions, element coordinates,           │
│             swimlane dimensions, edge routing                   │
│  - Returns: Complete draw.io XML                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  POST-PROCESSING (Deterministic)                                │
│  - Strip markdown fences if AI wrapped output                   │
│  - Embed narrative textbox with statistics                      │
│  - Write to ea_diagrams/*.drawio                                │
└─────────────────────────────────────────────────────────────────┘
```

### What Goes to AI

The AI receives a JSON payload containing:

```json
{
  "canvas": { "width": 2000, "height": 1500, "margin": 50 },
  "view_name": "Capability Realization Map",
  "elements": [
    { "id": "...", "label": "UDW Agent", "type": "ApplicationComponent",
      "color": "#81C784", "width": 120, "properties": {...} }
  ],
  "grouping_spec": { "by_property": "Domain", "order": [...] },
  "relationships": [ { "source": "...", "target": "...", "type": "Serving" } ],
  "structure_hierarchy": [ { "parent": {...}, "children": [...] } ],
  "annotations": [ { "text": "Strategic", "near": "UDW Agent" } ],
  "constraints": { "spacing_x": 50, "spacing_y": 40 }
}
```

### What AI Returns

Complete draw.io XML with positioned elements:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mxfile>
  <diagram name="...">
    <mxGraphModel>
      <root>
        <mxCell id="container-1" value="Operations" style="swimlane;..." />
        <mxCell id="elem-1" value="UDW Agent" style="rounded=1;fillColor=#81C784;..." />
        <mxCell id="rel-1" style="edgeStyle=orthogonal;..." source="elem-1" target="elem-2" />
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

### AI Prompt Location

`prompts/ea/drawio_diagram_layout.md` - Contains:
- Draw.io XML structure reference
- ArchiMate color codes
- Positioning rules
- Grouping instructions
- Structure hierarchy handling
- Annotation rendering

### Fallback Behavior

If AI fails (malformed response, timeout, etc.):
- Falls back to deterministic Python layout
- 4-column grid within swimlane containers
- All elements rendered, all relationships drawn
- Same color coding and styling

---

## Resolved Issues

### AI Truncation Investigation (2025-12-23)

**Original Symptom:** AI layout appeared to truncate output (28 elements → ~14 rendered).

**Investigation:** Added debug logging to capture API response metadata:
```
[AI DEBUG] finish_reason: stop      ← AI completed normally
[AI DEBUG] completion_tokens: 1429  ← Only used 1429 of 4096 allowed
```

**Root Cause:** Not AI truncation - **data quality issue**. Only 7/45 ApplicationComponents had the `Domain` property set, so WHERE clause correctly returned only 7 elements.

**Solution Implemented:** Added `_check_data_quality()` method that runs before element selection:

```
[DATA QUALITY WARNINGS]
  - Property 'Domain': 27/45 ApplicationComponents (60%) missing this property
  -   Available 'Domain' values: Commercial(9), Operations(7), ...
  - Property 'Region': 30/45 ApplicationComponents (67%) missing this property
  - Property 'Sub-Domain': 40/45 ApplicationComponents (89%) missing this property
```

**What the Diagnostics Check:**
1. Properties used in WHERE clause filters
2. Properties used in grouping (by_property, secondary_by_property)
3. Coverage percentage for each property
4. Available values for context

**Files Changed:**
- `src/ea/diagram_generator.py` - Added `_check_data_quality()` method and warnings output

### Property Normalization Fix (2025-12-23)

**Problem:** Excel files use varied column names (`Business Unit(s)`, `Activity Status`) that don't match standard property names (`Domain`, `Lifecycle Status`) used in view specs.

**Investigation:**
```
Excel column: "Business Unit(s)" → Stored as: "Business Unit(s)"
View spec: WHERE { Domain: "Operations" }
Result: No match → 0 elements selected
```

**Solution:** Added property normalization mapping in `src/ea/archi_export.py`:

```python
PROPERTY_NORMALIZATION = {
    'Business Unit(s)': 'Domain',
    'Business Unit': 'Domain',
    'Activity Status': 'Lifecycle Status',
    'Business Owner': 'Owner',
    # ... more mappings
}
```

**Files Changed:**
- `src/ea/archi_export.py` - Added `PROPERTY_NORMALIZATION` dict and applied in `_generate_properties()`

**Action Required:** Re-run ingestion to apply normalization:
```
ea_discover_directory("ea_inputs", "*")
```

---

## Future Enhancements (MVP9+)

- `size_by` presentation hint (vary element size by property)
- Full ArchiMate shape notation in draw.io (icons, specific shapes)
- Automatic relationship routing optimization
- Multi-view generation from single spec
- 3+ level structure hierarchy
