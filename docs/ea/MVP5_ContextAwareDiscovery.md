# EA MVP5: Context-Aware Iterative Discovery

**Status:** Planning
**Priority:** Critical - Blocks iterative EA model building
**Date:** 2025-01-13

---

## Problem Statement

### Current State: Context-Blind Discovery

**What happens now:**
```python
# Session 1
ea_discover("Microsoft Dynamics CRM for customer service")
→ Creates: elements.csv with "Microsoft Dynamics" ApplicationComponent

# Session 2 (minutes later)
ea_discover("CRM integrates with QAD EE for purchase orders")
→ Creates DUPLICATE: "CRM" ApplicationComponent (doesn't recognize it's same as "Microsoft Dynamics")
→ Missing relationship: No Flow/Serving relationship between elements
```

**Root cause:**
```python
# src/mcp_server.py:136
discovery_result = self.ea_engine.discover(input_text)
# ↑ NO context passed - each discovery is isolated
```

**Evidence:**
- `discover()` method has no parameters for existing model context
- `archi_inputs/` is never read during discovery
- ArchiMateCSVProvider exists but isn't used in discovery flow
- Only used AFTER discovery for diagram generation

### Critical Limitations

1. **No Entity Resolution** - "CRM", "Microsoft Dynamics CRM", "Dynamics" all treated as different elements
2. **No Relationship Inference** - Even when elements exist, relationships aren't detected
3. **No Incremental Building** - Can't add to existing model, only replace
4. **No Duplicate Detection** - Same app mentioned twice creates duplicates
5. **No Cross-Session Memory** - Each call is stateless

---

## Success Criteria

### Must Have (Priority 1)

1. **Context Loading**
   - Read existing archi_inputs/ before each discovery
   - Pass element names to prompt for entity resolution
   - Validate relationship endpoints exist

2. **Relationship Detection**
   - Consistently detect app→capability Serving relationships
   - Detect app→app Flow relationships for integrations
   - Include relationship descriptions/metadata

3. **Entity Resolution**
   - Recognize "CRM" = "Microsoft Dynamics" from context
   - Deduplicate elements across sessions
   - Preserve existing element IDs

### Should Have (Priority 2)

4. **Preview Mode**
   - Show proposed changes before committing
   - Highlight new vs updated vs unchanged
   - Allow user review/approval

5. **Multi-File Discovery**
   - Process entire ea_inputs/ directory
   - Aggregate findings across documents
   - Infer cross-document relationships

### Nice to Have (Priority 3)

6. **Quality Validation**
   - Detect orphaned relationships
   - Flag naming inconsistencies
   - Confidence scoring per element

---

## Proposed Architecture

### Design Principle: Prompt-Driven, Not Code-Driven

**Core Philosophy:**
> "The prompt should contain ALL intelligence. Code only loads/passes context."

### Context Retrieval Mechanism

**Location:** `src/mcp_server.py:_ea_discover()` (additive enhancement)

```python
async def _ea_discover(self, input_text: str, update_archi: bool = True) -> Dict[str, Any]:
    # NEW: Load existing context
    existing_context = self._load_archi_context()

    # ENHANCED: Pass context to discovery
    discovery_result = self.ea_engine.discover(
        system_description=input_text,
        existing_model=existing_context  # ← New parameter
    )
```

**What is `existing_context`?**
```python
{
    "elements": [
        {"id": "id-abc123", "type": "ApplicationComponent", "name": "Microsoft Dynamics"},
        {"id": "id-def456", "type": "Capability", "name": "Customer Service"}
    ],
    "element_names": ["Microsoft Dynamics", "Customer Service", "QAD EE"],
    "relationships": [
        {"type": "Serving", "source": "Microsoft Dynamics", "target": "Customer Service"}
    ]
}
```

**Source:** Read from `archi_inputs/` using existing `ArchiMateCSVProvider`

### Prompt Enhancement Strategy

**Location:** `prompts/ea/ea_discovery.md`

#### Phase 1: Element Extraction (existing)
```markdown
Extract ArchiMate elements from the system description...
[Current logic unchanged]
```

#### Phase 2: Entity Resolution (NEW)
```markdown
## ENTITY RESOLUTION

You are provided with existing model context:
- Known element names: {{EXISTING_ELEMENT_NAMES}}
- Existing relationships: {{EXISTING_RELATIONSHIPS}}

Before creating new elements:
1. Check if an element already exists with a similar name
2. If match found (>80% similarity), REUSE the existing element name exactly
3. Only create new element if truly distinct

Examples:
- Input: "CRM", Existing: ["Microsoft Dynamics CRM"] → Use "Microsoft Dynamics CRM"
- Input: "Dynamics", Existing: ["Microsoft Dynamics"] → Use "Microsoft Dynamics"
- Input: "QAD", Existing: ["QAD EE"] → Use "QAD EE"
```

#### Phase 3: Relationship Inference (NEW)
```markdown
## RELATIONSHIP ANALYSIS

Analyze text for relationships between elements:

1. **Application serves Capability** (Serving)
   Keywords: "supports", "provides", "enables", "for [capability]"
   Example: "CRM for customer service" → CRM serves Customer Service

2. **Application integrates with Application** (Flow)
   Keywords: "integrates with", "calls", "sends data to", "feeds"
   Example: "CRM integrates with ERP" → Flow from CRM to ERP

3. **Validation Rules**
   - Source and target MUST exist in either discovered or existing elements
   - If source/target not found, DO NOT create relationship
   - Include relationship description from context

**CRITICAL**: Every ApplicationComponent SHOULD serve at least one Capability.
If you find an app without capabilities, look harder in the text for clues.
```

### Tool Enhancements (Additive)

#### New Tool: `ea_discover_preview`

**Purpose:** Preview discovery results before committing

```python
@mcp.tool()
async def ea_discover_preview(input_text: str) -> str:
    """
    Preview EA discovery results without updating archi_inputs/.

    Shows:
    - New elements to be created
    - Existing elements that match (entity resolution)
    - Relationships to be added
    - Validation warnings

    Returns:
        JSON with proposed changes for user review
    """
```

**Output Format:**
```json
{
  "new_elements": [
    {"type": "ApplicationComponent", "name": "QAD EE", "status": "NEW"}
  ],
  "matched_elements": [
    {"input": "CRM", "matched": "Microsoft Dynamics", "confidence": 0.95}
  ],
  "new_relationships": [
    {"type": "Flow", "source": "Microsoft Dynamics", "target": "QAD EE"}
  ],
  "warnings": [
    "Element 'Document Intelligence' has no relationships"
  ]
}
```

#### Enhanced Tool: `ea_discover` (parameter addition)

**Add optional parameter:**
```python
@mcp.tool()
async def ea_discover(
    input_text: str,
    update_archi: bool = True,
    preview_first: bool = False  # ← NEW
) -> str:
```

**Behavior:**
- `preview_first=True` → Show proposed changes, wait for confirmation
- `preview_first=False` → Direct commit (current behavior)

#### New Tool: `ea_discover_directory`

**Purpose:** Batch process multiple input files

```python
@mcp.tool()
async def ea_discover_directory(
    directory: str = "ea_inputs",
    file_pattern: str = "*.txt"
) -> str:
    """
    Discover EA objects from all files in a directory.

    Processes files in order, building context incrementally:
    1. Read file 1 → discover → update context
    2. Read file 2 → discover with file 1 context → update context
    3. Continue...

    Returns:
        Aggregated discovery results across all files
    """
```

---

## Implementation Plan

### Phase 1: Context Loading (Week 1)

**Files Changed:**
- `src/mcp_server.py:_ea_discover()` - Add context loading
- `src/ea/ea_discovery.py:discover()` - Add `existing_model` parameter
- `prompts/ea/ea_discovery.md` - Add entity resolution section

**Testing:**
```bash
# Test 1: Initial discovery
ea_discover("Microsoft Dynamics for customer service")

# Test 2: Incremental discovery (should recognize "Dynamics")
ea_discover("Dynamics integrates with QAD EE")
→ Should NOT create duplicate "Dynamics"
→ SHOULD recognize as "Microsoft Dynamics"
```

### Phase 2: Relationship Detection (Week 1)

**Files Changed:**
- `prompts/ea/ea_discovery.md` - Enhanced relationship analysis section

**Testing:**
```bash
ea_discover("CRM integrates with ERP for purchase orders")
→ MUST detect: Flow relationship CRM→ERP
→ MUST detect: Serving relationship CRM→"Purchase Orders" capability
```

### Phase 3: Preview Tools (Week 2)

**Files Changed:**
- `src/mcp_server.py` - Add `ea_discover_preview` tool
- `src/ea/ea_discovery.py` - Add preview mode support

**Testing:**
```bash
ea_discover_preview("New system description")
→ Shows proposed changes
→ User reviews
→ ea_discover_commit() to apply
```

### Phase 4: Batch Discovery (Week 2)

**Files Changed:**
- `src/mcp_server.py` - Add `ea_discover_directory` tool
- `src/ea/ea_discovery.py` - Add batch processing method

---

## Data Flow Diagrams

### Current (Context-Blind)
```
Input Text
    ↓
discover(text) [NO CONTEXT]
    ↓
Extract Elements + Relationships
    ↓
Write to ea_outputs/ea_analysis.json
    ↓
ArchiExporter reads JSON → archi_inputs/
```

**Problem:** Each discovery is isolated, no awareness of existing model

### Proposed (Context-Aware)
```
Input Text
    ↓
Load archi_inputs/ (via ArchiMateCSVProvider)
    ↓
discover(text, existing_model=context)
    ↓
Prompt uses context for:
  - Entity resolution
  - Relationship validation
  - Duplicate detection
    ↓
Extract Elements + Relationships [CONTEXT-AWARE]
    ↓
Write to ea_outputs/ea_analysis.json
    ↓
ArchiExporter MERGES with existing archi_inputs/
```

**Benefit:** Incremental model building, entity resolution, relationship inference

---

## Context Loading Implementation

### Helper Method (additive to `src/mcp_server.py`)

```python
def _load_archi_context(self) -> Dict[str, Any]:
    """
    Load existing ArchiMate model as context for discovery.

    Returns:
        Dict with elements, element_names, relationships
        Returns empty dict if archi_inputs/ doesn't exist yet
    """
    try:
        provider = ArchiMateCSVProvider("archi_inputs")

        if not provider.is_available():
            return {
                "elements": [],
                "element_names": [],
                "relationships": []
            }

        ea_data = provider.get_ea_data()

        # Convert to prompt-friendly format
        elements = [
            {
                "id": f"existing-{i}",
                "type": "ApplicationComponent",  # Inferred from structure
                "name": app.name
            }
            for i, app in enumerate(ea_data.applications)
        ]

        # Add capabilities
        elements.extend([
            {
                "id": f"existing-cap-{i}",
                "type": "Capability",
                "name": cap.name
            }
            for i, cap in enumerate(ea_data.capabilities)
        ])

        element_names = [e["name"] for e in elements]

        # Extract relationships from app_capabilities
        relationships = [
            {
                "type": "Serving",
                "source": rel.application.name,
                "target": rel.capability.name
            }
            for rel in ea_data.application_capabilities
        ]

        return {
            "elements": elements,
            "element_names": element_names,
            "relationships": relationships
        }

    except Exception as e:
        print(f"Warning: Could not load archi context: {e}")
        return {"elements": [], "element_names": [], "relationships": []}
```

### Prompt Template Variables

**Update `prompts/ea/ea_discovery.md`:**

```markdown
# EXISTING MODEL CONTEXT

{{#if EXISTING_ELEMENT_NAMES}}
## Known Elements in Current Model

The following elements already exist in the ArchiMate model:
{{EXISTING_ELEMENT_NAMES}}

When you encounter similar names in the input text, REUSE the existing element name exactly.
Examples:
- Input mentions "CRM" but model has "Microsoft Dynamics CRM" → Use "Microsoft Dynamics CRM"
- Input mentions "ERP" but model has "QAD EE ERP" → Use "QAD EE ERP"

{{else}}
No existing model. This is a fresh start.
{{/if}}

{{#if EXISTING_RELATIONSHIPS}}
## Known Relationships

{{EXISTING_RELATIONSHIPS}}

Do not duplicate these relationships. Only add NEW relationships.
{{/if}}
```

---

## Success Metrics

### Quantitative

1. **Relationship Detection Rate**
   - Current: ~10% of integrations detected as relationships
   - Target: >80% of integrations detected

2. **Entity Resolution Accuracy**
   - Current: 0% (no resolution happens)
   - Target: >90% of synonym references resolved correctly

3. **Duplicate Creation Rate**
   - Current: ~30% duplicates in multi-session scenarios
   - Target: <5% duplicates

### Qualitative

1. **Usability**: Can build EA model incrementally over multiple sessions
2. **Archi Import Quality**: Model has meaningful relationships, not just isolated elements
3. **Natural Workflow**: "Add more detail" works without duplicating existing elements

---

## Risks & Mitigation

### Risk 1: Over-matching (False Positives)

**Problem:** "Portal" matches "Customer Portal" incorrectly

**Mitigation:**
- Prompt includes similarity threshold guidance
- User preview before commit (Phase 3)
- Confidence scoring in output

### Risk 2: Prompt Size Limits

**Problem:** Large existing models exceed token limits

**Mitigation:**
- Only pass element names (compact), not full details
- Summarize relationships (count only for large models)
- Consider RAG/embedding approach for very large models (future)

### Risk 3: Relationship Validation Complexity

**Problem:** Complex validation logic in prompt

**Mitigation:**
- Keep validation rules simple and clear
- Start with basic rules (must exist), enhance iteratively
- Code validates after LLM extraction (safety net)

---

## Appendix: Prompt Excerpt Example

**Enhanced Entity Resolution Section:**

```markdown
## ENTITY RESOLUTION INSTRUCTIONS

Before creating a new element, check if it already exists.

### Step 1: Normalize Input
Convert input text to canonical form:
- Remove articles (a, an, the)
- Standardize abbreviations (CRM → Customer Relationship Management)
- Trim whitespace

### Step 2: Match Against Existing
Compare normalized input against existing element names.

Match criteria:
- Exact match → USE existing name
- Contains/substring match → USE existing name if context matches
- Abbreviation match → USE existing name

Examples:
| Input | Existing Model | Action |
|-------|---------------|--------|
| "CRM" | ["Microsoft Dynamics CRM"] | Use "Microsoft Dynamics CRM" |
| "Dynamics" | ["Microsoft Dynamics"] | Use "Microsoft Dynamics" |
| "QAD" | ["QAD EE", "QAD WMS"] | CLARIFY or use most common |
| "Portal" | ["Customer Portal", "Vendor Portal"] | CREATE new (ambiguous) |

### Step 3: Output Format
In your JSON output, use the EXACT existing element name when matched.

```json
{
  "discovery": {
    "ApplicationComponent": [
      {
        "name": "Microsoft Dynamics",  ← EXACT existing name
        "status": "existing",  ← Mark as existing, not new
        "description": "..."
      }
    ]
  }
}
```

**Key Principle:** When in doubt, REUSE existing elements. Creating duplicates is worse than false positives.
```

---

## Next Actions

1. **Review & Approve Plan** - Stakeholder sign-off on approach
2. **Phase 1 Implementation** - Context loading (1-2 days)
3. **Test with Real Data** - Use actual operations systems description
4. **Iterate Prompt** - Refine based on results
5. **Phase 2+ Implementation** - Preview tools, batch processing

---

**Questions for Discussion:**

1. Should entity resolution be strict (>90% similarity) or loose (>70%)?
2. Preview mode: Required or optional for all discoveries?
3. Batch processing: Process files sequentially or in parallel?
4. Confidence scoring: Show to user or internal only?
