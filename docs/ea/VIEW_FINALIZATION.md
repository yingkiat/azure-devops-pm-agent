# View Finalization - Hybrid Validation + Approval (MVP6+)

**Status:** ✅ Complete and Tested
**Date:** 2025-11-10
**Purpose:** Fix view generation issues (wrong content, duplicates, meaningless views)

---

## The Problem

Previously, view generation worked like this:

```
YAML Spec (WHERE clause)
    ↓
Apply Filter Silently
    ↓
Generate View (blindly)
    ↓
[Results: Wrong elements, empty views, unexpected grouping]
```

Users never saw what elements were selected before the view was rendered. If the WHERE clause didn't match expectations, bad views were generated silently.

---

## The Solution: Hybrid Validation

New workflow adds a **preview + validation step** before XML generation:

```
YAML Spec (WHERE clause)
    ↓
[1] PYTHON VALIDATION (Deterministic)
    - Check for empty views
    - Detect duplicate elements
    - Verify grouping properties exist
    - Show property distributions
    - Identify orphaned elements
    ↓
[2] PREVIEW REPORT (Human-readable)
    - Show sample elements for each view
    - Display element types and counts
    - List any data quality issues
    - Indicate property availability
    ↓
[3] LLM INTERVIEW (Interactive)
    - Claude Code shows report
    - User reviews content
    - User approves or asks to fix YAML
    ↓
[4] FINALIZATION (On Approval)
    - Generate views.csv
    - Update model.xml
    - Import to Archi
```

---

## How It Works

### Step 1: Generate Views from Specs (Validation Only)

```bash
Claude Code: "Generate views from specs"
```

This calls `ea_generate_views_from_specs()` which:
1. Loads YAML specs from `ea_inputs/views/*.yaml`
2. Applies WHERE clauses to select elements
3. **Validates** each view with ViewFinalizer
4. **Returns detailed report** (no XML generated yet)

**Output:**
- ✓/✗ status for each view
- Element counts and types
- Property distribution
- Sample elements (first 15)
- Issues and warnings
- Message: "Review the report. Reply with 'generate the views' to proceed"

### Step 2: Validation Checks

ViewFinalizer performs **deterministic Python checks**:

| Check | What it finds |
|-------|---|
| **EMPTY_VIEW** | WHERE clause matched no elements |
| **DUPLICATE_ELEMENTS** | Same element appears multiple times |
| **MISSING_GROUPING_PROPERTY** | Elements lack primary grouping property (e.g., Region) |
| **MISSING_SECONDARY_PROPERTY** | Elements lack secondary grouping property (e.g., Sub-Domain) |
| **ORPHANED_ELEMENTS** | Elements have no relationships in the view |

**Severity Levels:**
- 🔴 **Error**: Blocks finalization (empty views, duplicates)
- 🟡 **Warning**: Doesn't block, but indicates data quality issues

### Step 3: Preview Report

Example output:

```
==========================================================================================
VIEW FINALIZATION - VALIDATION & PREVIEW
==========================================================================================

SUMMARY:
  Views Processed:    2
  Valid:              2
  Issues:             0
  Warnings:           3

------------------------------------------------------------------------------------------

VIEW 1: ✓ VALID - Commercial Applications Matrix
  Elements: 12 | Relationships: 3
  Element Types: 12x ApplicationComponent
  Grouping: By 'Region'
  Property Distribution:
    Region: ANZ:8, Australia:1, JPN:1, Japan:2
    Domain: Commercial:12
    Sub-Domain: Customer Service:1, Marketing:1, ...
  Sample Elements (showing 5 of 12):
    • Microsoft Dynamics (ApplicationComponent)
    • Salesforce.com (ApplicationComponent)
    • MedQuote (ApplicationComponent)
    • PO Automation (ApplicationComponent)
    • ...
  ⚠ WARNINGS (1):
    [ORPHANED_ELEMENTS] View: 8 elements have no relationships
      → Unconnected elements may indicate missing relationships

...
```

### Step 4: Finalization (On Approval)

Once user approves:

```bash
Claude Code: "The views look good, generate them"
```

This calls `ea_finalize_views()` which:
1. Calls `view_builder.generate_views_from_specs()` again (deterministic, same output)
2. Generates `archi_inputs/views.csv`
3. Updates `archi_inputs/model.xml` with views
4. Returns success message

```json
{
  "success": true,
  "phase": "finalized",
  "views_generated": 2,
  "model_xml_updated": true,
  "message": "View generation complete! Import archi_inputs/model.xml into Archi tool."
}
```

---

## Architecture

### New Module: `view_finalizer.py`

**Purpose**: Fast, deterministic Python validation (no LLM)

**Key Classes:**
- `ViewValidation` - Results of validating a single view
  - `view_name`: Name of the view
  - `is_valid`: True if no critical errors
  - `element_count`, `relationship_count`: Sizes
  - `issues`: List of errors that block finalization
  - `warnings`: List of data quality concerns
  - `preview`: Sample elements and properties

- `ViewFinalizer` - Validation engine
  - `finalize_view()` - Validate single view
  - `format_validation_report()` - Human-readable output
  - `should_proceed_with_generation()` - Check if safe to finalize

### Integration Points

**MCP Server** (`src/mcp_server.py`):

1. **`ea_generate_views_from_specs()`** - Validation phase
   - Calls `ViewFinalizer.finalize_view()` for each view
   - Returns preview report
   - Does **NOT** generate XML

2. **`ea_finalize_views()`** - Finalization phase
   - Calls `ViewBuilder.generate_views_from_specs()` (same logic, deterministic)
   - Generates `model.xml`
   - Returns success/failure

---

## Workflow Example

### Scenario: User creates new view spec

**1. User creates `operations_dashboard.yaml`:**
```yaml
view:
  name: "Operations Dashboard"
  viewpoint: "application_cooperation"

elements:
  include:
    - where:
        type: "ApplicationComponent"
        Domain: "Operations"
        Region: "JPN"

# ... rest of spec
```

**2. User asks to generate views:**
```
"Generate views from specs"
```

**3. Claude Code:**
- Calls `ea_generate_views_from_specs()`
- Gets validation report back
- Shows report to user

**4. Report shows:**
```
✓ VALID - Operations Dashboard
  Elements: 5 | Relationships: 2
  Element Types: 5x ApplicationComponent
  Grouping: By 'Region'
  Property Distribution:
    Region: JPN:5
    Domain: Operations:5
    Sub-Domain: Manufacturing:2, RAQA:1, ...
  Sample Elements:
    • SAP APO
    • QAD EE
    • W3 Sirius
    • ...
```

**5. User approves:**
```
"Looks good, generate the views"
```

**6. Claude Code:**
- Calls `ea_finalize_views()`
- Gets success response
- Tells user to import `model.xml` to Archi

---

## Benefits

| Benefit | Why it matters |
|---------|---|
| **Catches errors early** | Empty views, missing properties caught before XML generation |
| **Shows selected elements** | User sees exactly what matched the WHERE clause |
| **Deterministic** | Same YAML spec always produces same validation report |
| **Fast** | Python validation is instant (no LLM latency) |
| **Interactive approval** | User can review before expensive XML generation |
| **Data quality visibility** | Warnings highlight property gaps, orphaned elements |
| **Prevents bad exports** | No more meaningless views with random content |

---

## Implementation Details

### ViewFinalizer Validation Logic

```python
def finalize_view(
    view_name: str,
    selected_element_ids: List[str],
    selected_relation_ids: List[str],
    grouping_config: Dict[str, Any],
    spec_file_name: str
) -> ViewValidation:
    """
    Validate view and return detailed results
    """
    validation = ViewValidation(view_name=view_name, is_valid=True)

    # Check 1: Empty view?
    if not selected_element_ids:
        validation.issues.append({
            'code': 'EMPTY_VIEW',
            'message': "WHERE clause matched nothing"
        })
        return validation  # Don't check further

    # Check 2: Duplicates?
    if len(set(selected_element_ids)) != len(selected_element_ids):
        validation.issues.append({...})

    # Check 3: Grouping properties?
    for elem_id in selected_element_ids:
        if 'Region' not in properties[elem_id]:
            validation.warnings.append({...})

    # Check 4: Relationships?
    # ... etc

    # Build preview
    validation.preview = {...}

    return validation
```

### Two-Phase MCP Tools

**Phase 1: Validation (ea_generate_views_from_specs)**
```python
async def _ea_generate_views_from_specs(self) -> Dict:
    # 1. Load YAML specs
    result = self.view_builder.generate_views_from_specs()

    # 2. Validate each view
    validations = []
    for view_def in result['view_definitions']:
        v = self.view_finalizer.finalize_view(...)
        validations.append(v)

    # 3. Return report (NO XML YET)
    return {
        'phase': 'validation_complete',
        'can_proceed': finalizer.should_proceed_with_generation(validations),
        'validation_report': finalizer.format_validation_report(validations),
        'view_definitions': [...],
        'message': "Review report. Reply 'generate the views' to proceed."
    }
```

**Phase 2: Finalization (ea_finalize_views)**
```python
async def _ea_finalize_views(self) -> Dict:
    # 1. Generate views.csv (deterministic, same as before)
    result = self.view_builder.generate_views_from_specs()

    # 2. Generate model.xml
    archi_result = await self._ea_generate_archi(generate_xml=True)

    # 3. Return success
    return {
        'phase': 'finalized',
        'views_generated': result['views_generated'],
        'model_xml_updated': True,
        'message': "Import archi_inputs/model.xml into Archi tool."
    }
```

---

## Testing

### Test Files Created

1. **`test_view_validation.py`** - Unit tests for ViewFinalizer
   - ✅ Validates single views
   - ✅ Detects empty views
   - ✅ Formats reports
   - ✅ Checks should_proceed logic

2. **`test_mcp_validation.py`** - Integration tests for MCP tools
   - ✅ Calls ea_generate_views_from_specs()
   - ✅ Validates 2 real YAML specs
   - ✅ Reports 3 warnings (property gaps)
   - ✅ Calls ea_finalize_views()
   - ✅ Generates model.xml successfully

### Test Results

**Real Data Example:**

```
Found 2 view specifications:
  - Commercial Applications Matrix (commercial_app_matrix.yaml)
  - Operations Applications Landscape (operations_app_landscape.yaml)

Validation Result:
  Phase: validation_complete
  Views Validated: 2
  Can Proceed: True

View Details:
  ✓ Commercial Applications Matrix: 12 elements, 0 issues, 1 warnings
    - 8 orphaned elements (no relationships)
  ✓ Operations Applications Landscape: 14 elements, 0 issues, 2 warnings
    - 1 element missing Region property
    - 2 elements missing Sub-Domain property

Finalization (after approval):
  Phase: finalized
  Views Generated: 2
  Model XML Updated: True
  Message: View generation complete! Import archi_inputs/model.xml into Archi tool.
```

---

## Next Steps / Future Enhancements

### MVP6+ (Beyond Current Implementation)

1. **Interactive Property Suggestions**
   - When validation finds missing properties, suggest fixes
   - Example: "Element XYZ missing Region. Add to properties.csv? (Suggest: JPN)"

2. **Auto-Fix Options**
   - For orphaned elements, suggest relationships to add
   - For missing properties, suggest values from similar elements

3. **View Comparison**
   - Show before/after when YAML is edited and re-validated
   - Highlight what changed in element selection

4. **Batch Validation**
   - Validate all specs at once (currently does this)
   - Report common issues across views (e.g., "Region property 30% sparse")

5. **Dry-Run Mode**
   - Generate model.xml without saving
   - Preview layout before committing to file

---

## Conclusion

The hybrid validation approach combines:
- ✅ **Deterministic Python** for fast, auditable validation
- ✅ **Human-readable reports** for easy review
- ✅ **LLM dialogue** for interactive approval
- ✅ **Two-phase generation** to prevent bad exports

Result: Views are validated BEFORE expensive XML generation, users see exactly what will be included, and data quality issues are caught early.
