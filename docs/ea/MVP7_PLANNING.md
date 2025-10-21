# MVP7: LLM-Based Diagram Layout Engine

**Status:** Planning Phase
**Decision Date:** 2025-01-16
**Context:** Rules-based drawing (MVP6) cannot handle all possibilities. Pivoting to AI-driven layout.

---

## Executive Summary

Replace rules-based coordinate calculation with **LLM-driven layout planning**. AI receives structural data (elements, groups, notes, relationships) and generates complete diagram XML with intelligently positioned coordinates.

**Why:**
- Rules-based systems struggle with arbitrary nesting, overlap avoidance, readability optimization
- AI naturally understands spatial reasoning and constraints
- Extensible to new diagram types without code changes
- Deterministic via prompts (version-controlled, reproducible)

---

## Architecture

### Current Flow (MVP6)
```
YAML Spec
    ↓
ViewBuilder (rules-based positioning)
    ↓
ArchiExporter (hardcoded coordinate math)
    ↓
model.xml (with positioning bugs)
```

### New Flow (MVP7)
```
YAML Spec
    ↓
ViewBuilder (element selection, unchanged)
    ↓
views.csv (element + group metadata, unchanged)
    ↓
ArchiLayoutAI (NEW - LLM-based positioning)
    ↓
Azure OpenAI with layout prompt
    ↓
AI outputs: Complete XML with coordinates
    ↓
ArchiExporter wraps in model structure
    ↓
model.xml (AI-positioned)
```

### New Files

**`src/ea/archi_layout_ai.py`** (NEW)
- Reads views.csv, elements.csv, relations.csv, properties.csv
- Organizes data for AI consumption
- Calls Azure OpenAI with layout prompt
- Parses AI response (XML block with coordinates)
- Validates coordinates against canvas
- Returns complete diagram XML

**`prompts/ea/archimate_diagram_layout.md`** (NEW)
- Explicit layout instructions for AI
- Canvas constraints, sizing rules
- Hierarchical positioning logic
- Spacing and alignment rules
- Z-ordering principles
- Group nesting guidelines
- Collision avoidance strategy
- Label placement rules
- Connection routing guidance

**`src/ea/archi_export.py`** (MODIFIED)
- Keep existing rules-based as legacy mode (backward compatible)
- Add new mode: `use_ai_layout=True`
- When enabled: calls archi_layout_ai instead of rules-based positioning
- Falls back to rules-based if AI fails

---

## Key Findings from Research

### Labels in Archi (Not Notes)

**Critical Discovery:** Archi uses `xsi:type="Label"` for text annotations, NOT `xsi:type="Note"`

**Correct XML Structure:**
```xml
<node identifier="id-xyz" xsi:type="Label" x="177" y="264" w="185" h="80">
  <label xml:lang="en">Manufacturing</label>
  <style>
    <fillColor r="255" g="255" b="255" a="100" />
    <lineColor r="92" g="92" b="92" a="100" />
    <font name="Segoe UI" size="9">
      <color r="0" g="0" b="0" />
    </font>
  </style>
</node>
```

**Key Attributes:**
- `xsi:type="Label"` - Identifies as text label/annotation
- `x`, `y` - Position from top-left corner (0,0)
- `w`, `h` - Width and height (required for Labels)
- `<label>` - Text content
- `<style>` - Optional styling (colors, fonts)

**Container Nesting:**
```xml
<node identifier="region-anz" xsi:type="Container" x="20" y="20" w="800" h="600">
  <!-- Label inside container -->
  <node identifier="label-mfg" xsi:type="Label" x="20" y="20" w="300" h="40">
    <label>Manufacturing</label>
  </node>

  <!-- Element inside container (absolute coordinates) -->
  <node identifier="app-1" xsi:type="Element" x="20" y="70" w="120" h="60" elementRef="id-app1"/>
</node>
```

**Positioning Rules:**
- Coordinates are ABSOLUTE (not relative to parent container)
- Child nodes positioned within parent's bounding box
- Z-order determined by sibling order in XML
- No explicit parent-child coordinate math needed

### MVP6 Issues Identified

**Why MVP6 Failed:**
1. ✅ Correct: Used `xsi:type="Container"` for region groups
2. ❌ Wrong: Used `xsi:type="Note"` instead of `xsi:type="Label"`
3. ❌ Wrong: Missing `w` (width) and `h` (height) on Label nodes
4. ❌ Wrong: Apps positioned in first row as columns (coordinate math error)
5. ❌ Missing: Labels not rendering in Archi

**Root Cause:** Attempted to use complex nesting rules with hardcoded math. Should have delegated positioning to AI from the start.

---

## YAML Configuration (MVP6 → MVP7)

**Kept from MVP6:**
```yaml
grouping:
  by_property: "Region"
  secondary_by_property: "Sub-Domain"  # Two-level nesting still needed
  order: ["ANZ", "JPN", "AEM"]
  group_width: 800
  group_height: 900
  group_spacing_x: 50
  group_spacing_y: 50

layout:
  algorithm: "column"                  # Layout hint for AI
  spacing_y: 40
```

**How AI Uses This:**
- `algorithm: "column"` → AI stacks apps vertically
- `spacing_y: 40` → AI maintains 40px between items
- `group_height: 900` → AI knows container size limit
- Secondary grouping → AI creates Labels for sub-domains

**Canvas Configuration (Fixed, not in YAML):**
```python
# In archi_layout_ai.py
CANVAS_WIDTH = 2000
CANVAS_HEIGHT = 1500
CANVAS_MARGIN = 20
```

---

## Data Flow for AI

**Input JSON Structure:**

```json
{
  "canvas": {
    "width": 2000,
    "height": 1500,
    "margin": 20
  },
  "view_name": "Operations Applications Matrix",
  "elements": [
    {
      "id": "id-abc123",
      "label": "SAP ERP",
      "type": "ApplicationComponent",
      "category": "Element"
    },
    {
      "id": "id-def456",
      "label": "Manufacturing",
      "type": "Label",
      "category": "Annotation"
    }
  ],
  "groups": [
    {
      "id": "grp-region-anz",
      "label": "ANZ",
      "type": "Container",
      "children": ["id-abc123", "id-xyz789", ...],
      "width": 800,
      "height": 600
    },
    {
      "id": "grp-subdomain-mfg",
      "label": "Manufacturing",
      "type": "Label",
      "parent_group": "grp-region-anz",
      "children": ["id-abc123", ...]
    }
  ],
  "relationships": [
    {
      "id": "rel-001",
      "source_id": "id-abc123",
      "target_id": "id-def456",
      "type": "Serving"
    }
  ],
  "constraints": {
    "layout_algorithm": "column",
    "grouping_strategy": "hierarchical",
    "spacing": {
      "horizontal": 50,
      "vertical": 40
    },
    "min_element_width": 120,
    "min_element_height": 60,
    "label_width": 300,
    "label_height": 40
  }
}
```

**AI Output (XML Fragment):**

```xml
<diagram identifier="id-view-123" name="Operations Applications Matrix">
  <!-- ANZ Region Container -->
  <node identifier="grp-region-anz" xsi:type="Container" x="20" y="20" w="800" h="900">
    <!-- Manufacturing Label -->
    <node identifier="grp-label-mfg" xsi:type="Label" x="20" y="20" w="300" h="40">
      <label>Manufacturing</label>
      <style>
        <fillColor r="240" g="240" b="240" a="100"/>
        <lineColor r="100" g="100" b="100" a="100"/>
        <font name="Arial" size="11"><color r="0" g="0" b="0"/></font>
      </style>
    </node>

    <!-- Manufacturing Apps (vertical column) -->
    <node identifier="node-abc123" xsi:type="Element" x="20" y="70" w="120" h="60" elementRef="id-abc123"/>
    <node identifier="node-xyz789" xsi:type="Element" x="20" y="140" w="120" h="60" elementRef="id-xyz789"/>

    <!-- Distribution Label -->
    <node identifier="grp-label-dist" xsi:type="Label" x="20" y="220" w="300" h="40">
      <label>Distribution</label>
      <style>...</style>
    </node>

    <!-- Distribution Apps (vertical column) -->
    <node identifier="node-aaabbb" xsi:type="Element" x="20" y="270" w="120" h="60" elementRef="id-aaabbb"/>
  </node>

  <!-- JPN Region Container -->
  <node identifier="grp-region-jpn" xsi:type="Container" x="900" y="20" w="800" h="900">
    ...
  </node>

  <!-- Connections -->
  <connection identifier="conn-001" relationshipRef="rel-001" xsi:type="Relationship" source="node-abc123" target="node-aaabbb"/>
</diagram>
```

---

## Implementation Plan

### Phase 1: Prompt Engineering
1. Create `prompts/ea/archimate_diagram_layout.md`
   - Canvas and sizing rules
   - Hierarchical positioning logic
   - Label placement strategy
   - Connection routing approach
   - Examples of desired output

### Phase 2: Data Marshaling
1. Create `src/ea/archi_layout_ai.py`
   - Class: `DiagramLayoutEngine`
   - Method: `generate_layout(view_spec, elements, groups, relationships)`
   - Converts CSV data to JSON for AI consumption
   - Calls Azure OpenAI
   - Parses response into XML

### Phase 3: Integration
1. Modify `src/ea/archi_export.py`
   - Add `use_ai_layout` parameter
   - When True: call `DiagramLayoutEngine`
   - When False: use legacy rules-based (MVP6)
   - Wrap AI output in model structure

### Phase 4: Testing
1. Test on 2-level nesting (Region → Sub-Domain)
2. Test on flat grouping (Region only)
3. Compare AI layouts vs MVP6 output
4. Refine prompt based on results

---

## Configuration Decisions

**Canvas Size:** Fixed at 2000×1500 px
- Trial and error approach
- Can adjust if crowding occurs
- Not user-configurable (for now)

**AI Model:** Azure OpenAI (existing integration)
- Use gpt-4o for better spatial reasoning
- Structured output format (JSON or XML)

**Fallback:** Legacy rules-based still available
- `use_ai_layout=False` falls back to MVP6
- Safety mechanism if AI fails

**Versioning:** Not tracked (for now)
- Prompt regenerates diagram each time
- No need to store layout decisions

---

## Known Constraints

1. **Arbitrary nesting depth:** MVP7 should handle 3+ levels (MVP6 struggled with 2)
2. **Overlap avoidance:** AI should prevent element collisions
3. **Label placement:** Under/beside groups intelligently
4. **Connection routing:** Curved connections avoid overlaps
5. **Z-ordering:** Important elements on top (per XML sibling order)

---

## Success Criteria

✅ Labels render correctly in Archi (xsi:type="Label")
✅ Two-level nesting (Region → Sub-Domain) works
✅ Apps organized vertically within domains (column layout)
✅ No overlapping elements
✅ Relationships visible and connected properly
✅ Canvas usage optimal (not too sparse, not crowded)
✅ Better than MVP6 (no manual adjustment needed)

---

## Next Steps

1. Create MVP7_PLANNING.md (this file) ✓
2. **Start fresh session with:**
   - Create `prompts/ea/archimate_diagram_layout.md`
   - Create `src/ea/archi_layout_ai.py` skeleton
   - Write prompt engineering
   - Test on simple view first

---

**Version:** 0.1 Planning
**Last Updated:** 2025-01-16
