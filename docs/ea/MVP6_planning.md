# EA MVP6: Spec-Driven View Generation

## 🎯 Revolutionary Objective

**Transform from auto-generated generic views to business-specific, repeatable, version-controlled architecture views.** Enable business users to define, iterate, and refine their exact view requirements using declarative YAML specifications.

## 🧠 The Business Value Gap

### ❌ **Current Limitations (MVP4)**
- **Non-Deterministic**: Same discovery generates slightly different views each time
- **Generic Views**: Auto-generated views lack business specificity
- **No Iteration**: Can't refine a view without regenerating entire model
- **No Business Control**: Technical users control what gets visualized
- **No Version Control**: View definitions exist only as transient LLM output
- **Inconsistent Results**: LLM variability means unreliable business artifacts

**Current Frustrating Experience:**
```bash
# Discovery auto-generates views
User: "analyze our CRM integrations"
AI: [generates elements] → auto-creates 7 generic views

# Views are random each time
Run 1: Integration View shows CRM, QAD, 3 interfaces
Run 2: Integration View shows CRM, QAD, D365, 5 interfaces (different layout!)
Run 3: Integration View missing critical API gateway

# User wants specific view
User: "I only want CRM-to-QAD flow with purchase orders"
AI: [confused] "I'll regenerate everything..." (still generic)

# No refinement capability
User: "That view is missing the Document Intelligence service"
AI: [regenerates all 7 views] "Here's a fresh model..."
```

## 🎯 MVP6 Vision: Spec-Driven Architecture Views

**Revolutionary User Experience:**
```bash
# Initial discovery (unchanged)
User: "analyze CRM integrations"
AI: [discovery] → 15 elements extracted to archi_inputs/

# User requests specific view
User: "create a view showing CRM-to-QAD purchase order flow"
AI: [generates spec] → ea_inputs/views/crm_qad_po_flow.yaml

# AI shows spec for review
AI: "I've created a spec for 'CRM-QAD Purchase Order Flow' including:
     - CRM application
     - QAD EE application
     - Purchase Order data object
     - Document Intelligence service
     - Serving and Flow relationships

     Review: ea_inputs/views/crm_qad_po_flow.yaml"

# User reviews spec, iterates
User: "add the approval workflow capability"
AI: [edits spec] "Added Business-Capability: PO Approval Workflow"

User: "remove Document Intelligence, it's out of scope"
AI: [edits spec] "Removed Application-Component: Document Intelligence"

# Generate deterministic view
AI: "Generating views.csv from specs..."
→ views.csv updated with exact elements specified

# Import into Archi
User: [imports views.csv]
→ Archi shows "CRM-QAD Purchase Order Flow" view
→ Exactly as specified, every time

# Next week...
User: "update the CRM flow view to include the new API gateway"
AI: [reads spec] → [adds API gateway] → [regenerates]
→ Same view layout, deterministic output, version controlled
```

## 🏗️ Core Architecture: Dual-Mode View System

### **Architecture Evolution**

```
MVP4 (Auto-Gen):
  Discovery → Elements/Relations → Auto-Gen Views → views.csv
                                    (generic, random)

MVP6 (Spec-Driven):
  Discovery → Elements/Relations → YAML Specs → views.csv
                                   (specific, deterministic)

  [Both modes supported simultaneously]
```

### **1. View Specification Format** (`ea_inputs/views/*.yaml`)

**Declarative View Definition:**
```yaml
# ea_inputs/views/crm_qad_po_flow.yaml
view:
  name: "CRM-QAD Purchase Order Flow"
  documentation: "Integration flow for automated purchase order creation from CRM opportunities to QAD EE"
  viewpoint: "application_cooperation"  # ArchiMate standard viewpoint

elements:
  include:
    # Criteria-based selection (dynamic)
    - where:
        type: "Application-Component"
        name_contains: ["CRM", "QAD"]

    # Explicit name references (human-readable)
    - name: "Document Intelligence"
      type: "Application-Component"

    # Explicit ID references (guaranteed precision)
    - id: "id-abc123"  # Purchase Order data object

    # Transitive inclusion (smart selection)
    - where:
        type: "Business-Capability"
        serves: "included_applications"  # Capabilities linked to selected apps

relationships:
  include:
    # Relationship type filters
    - type: ["Serving", "Flow"]
      between: "included_elements"

    # Exclude specific relationships
    - exclude:
        type: "Composition"  # Hide internal composition details

layout:
  algorithm: "layered"  # Uses existing LayeredLayout from archi_layouts.py
  spacing_x: 50
  spacing_y: 80
  group_by: "layer"  # Group by ArchiMate layer (business, application, data)
```

**Key Features:**
- **Hybrid Selection**: Criteria + Names + IDs
- **Transitive Inclusion**: "capabilities that serve included apps"
- **Relationship Filters**: Control exactly which connections show
- **Layout Reuse**: Leverages existing MVP4 layout algorithms
- **Human-Readable**: Business users can understand and edit

### **2. View Builder Engine** (`src/ea/view_builder.py`)

**Deterministic View Generation:**
```python
class ViewBuilder:
    """Generates views.csv from YAML specifications"""

    def __init__(self, archi_inputs_dir: str = "ea_inputs"):
        self.provider = ArchiMateProvider(archi_inputs_dir)
        self.elements = self.provider.get_all_elements()
        self.relations = self.provider.get_all_relationships()
        self.spec_dir = f"{archi_inputs_dir}/views"

    def generate_views_from_specs(self) -> str:
        """Read all specs, generate views.csv"""
        specs = self._load_all_specs()

        view_rows = []
        for spec in specs:
            # 1. Deterministic element selection
            selected = self._select_elements(spec)

            # 2. Deterministic layout (reuse existing algorithms)
            layout = self._get_layout_engine(spec['layout'])
            positions = layout.calculate_layout(selected['elements'], selected['relations'])

            # 3. Format as CSV rows (existing format)
            view_rows.extend(self._format_view_csv(spec, positions, selected))

        # Write views.csv
        self._write_views_csv(view_rows)
        return f"Generated {len(specs)} views from specs"

    def _select_elements(self, spec: Dict) -> Dict:
        """Select elements based on spec criteria"""
        selected_elements = []

        for selector in spec['elements']['include']:
            if 'where' in selector:
                # Criteria-based selection
                matched = self._filter_elements(selector['where'])
                selected_elements.extend(matched)
            elif 'name' in selector:
                # Name-based selection
                matched = self._find_by_name(selector['name'])
                selected_elements.append(matched)
            elif 'id' in selector:
                # ID-based selection
                matched = self._find_by_id(selector['id'])
                selected_elements.append(matched)

        # Handle transitive inclusion
        if self._has_transitive_selectors(spec):
            selected_elements.extend(self._resolve_transitive(selected_elements, spec))

        return {
            'elements': selected_elements,
            'relations': self._filter_relations(selected_elements, spec)
        }
```

### **3. ArchiMate Viewpoint Templates** (`ea_inputs/view_templates/`)

**Standard Viewpoint Definitions:**
```yaml
# ea_inputs/view_templates/application_cooperation.yaml
viewpoint: "application_cooperation"
archimate_spec:
  standard: "ArchiMate 3.1"
  purpose: "Design and assignment of application structure and behavior"
  concerns:
    - "Application structure"
    - "Application cooperation"
    - "Consistency and completeness"
    - "Reduction of complexity"

  typical_elements:
    - "Application-Component"
    - "Application-Interface"
    - "Application-Service"
    - "Application-Function"
    - "Data-Object"

  typical_relationships:
    - "Serving"
    - "Flow"
    - "Access"
    - "Composition"
    - "Assignment"

  validation_rules:
    - "Application-Component can serve Business-Capability"
    - "Application-Interface realizes Application-Service"
    - "Data-Object flows between Application-Components"

default_layout:
  algorithm: "layered"
  group_by: "layer"
  spacing_x: 50
  spacing_y: 80
```

**Supported Viewpoints (ArchiMate 3.1 Standard):**
1. **Application Cooperation** - App structure and interactions
2. **Capability Map** - Business capabilities and realizations
3. **Information Structure** - Data objects and flows
4. **Technology Architecture** - Infrastructure and deployments
5. **Layered View** - Cross-layer architecture overview
6. **Migration View** - As-is to to-be transformations
7. **Business Process** - Process flows and supporting apps

### **4. Conversational Spec Management**

**Natural Language Spec Editing:**
```python
# User says: "add the API gateway to the CRM flow view"
# AI workflow:

1. Identify target spec: "crm_qad_po_flow.yaml"
2. Parse user intent: ADD operation
3. Resolve element: "API Gateway" → id-xyz789
4. Edit YAML:
   elements:
     include:
       - id: "id-xyz789"  # API Gateway (ADDED)
5. Regenerate views.csv
6. Confirm: "Added API Gateway to CRM-QAD Purchase Order Flow view"
```

**Supported Natural Language Operations:**
- **Add**: "add X to view Y"
- **Remove**: "remove X from view Y"
- **Replace**: "replace X with Y in view Z"
- **Create**: "create a view showing X, Y, Z"
- **Duplicate**: "copy the CRM view and add security layer"
- **Clear**: "remove all capabilities from integration view"

## 🚀 Implementation Plan

### **Phase 1: Core Spec Engine** (Priority 1 - MVP6 Foundation)

**1.1 View Builder Implementation**
```
File: src/ea/view_builder.py
- YAML spec parsing (PyYAML)
- Element selection (criteria, name, ID)
- Relationship filtering
- Integration with existing ArchiMateProvider
- CSV generation (existing format)
```

**1.2 Element Selection Logic**
```
Methods:
- _filter_elements(criteria) → Query-based selection
- _find_by_name(name) → Fuzzy name matching
- _find_by_id(id) → Exact ID lookup
- _resolve_transitive(elements, spec) → "serves", "accesses" relationships
```

**1.3 Layout Integration**
```
Reuse existing archi_layouts.py:
- LayeredLayout (default)
- HierarchicalLayout (process flows)
- GridLayout (simple views)
- CompactLayout (small diagrams)

No new layout code needed!
```

### **Phase 2: Conversational Spec Management** (Priority 2)

**2.1 Spec Editor Module**
```
File: src/ea/spec_editor.py
- parse_edit_intent(user_input) → ADD/REMOVE/REPLACE
- apply_edit(spec_path, operation, element) → YAML modification
- validate_spec(spec) → ArchiMate viewpoint rules
- list_available_elements() → Show what's in archi_inputs/
```

**2.2 Natural Language Integration**
```
MCP Tool: ea_edit_view_spec(view_name, operation, element)
- "add the API gateway to CRM view"
  → ea_edit_view_spec("crm_qad_po_flow", "add", "API Gateway")
- "remove Document Intelligence from integration view"
  → ea_edit_view_spec("integration_view", "remove", "Document Intelligence")
```

**2.3 Spec Generation from Natural Language**
```
MCP Tool: ea_create_view_spec(view_name, description)
User: "create a view showing CRM, QAD, and purchase order flows"
AI:
  1. Parse elements: ["CRM", "QAD", "Purchase Order"]
  2. Load viewpoint template: "application_cooperation"
  3. Generate spec YAML
  4. Save to ea_inputs/views/crm_qad_integration.yaml
  5. Return spec for user review
```

### **Phase 3: ArchiMate Viewpoint System** (Priority 3)

**3.1 Viewpoint Templates**
```
Create 7 standard templates in ea_inputs/view_templates/:
- application_cooperation.yaml
- capability_map.yaml
- information_structure.yaml
- technology_architecture.yaml
- layered_view.yaml
- migration_view.yaml
- business_process_cooperation.yaml
```

**3.2 Validation Engine**
```
File: src/ea/viewpoint_validator.py
- load_viewpoint_rules(viewpoint) → Get validation rules
- validate_element_types(spec) → Check element types allowed
- validate_relationships(spec) → Check relationship types allowed
- suggest_corrections(violations) → Help fix spec errors
```

**3.3 Template-Based Spec Creation**
```
User: "create an application cooperation view for CRM integrations"
AI:
  1. Load template: application_cooperation.yaml
  2. Apply user filter: "CRM integrations"
  3. Select elements: Applications with "CRM" in name
  4. Add default relationships: Serving, Flow
  5. Generate spec: ea_inputs/views/crm_integrations.yaml
```

### **Phase 4: Dual-Mode Coexistence** (Priority 4)

**4.1 Mode Selection**
```python
# src/ea/archi_export.py - Updated

def generate_views_csv():
    """Generate views using appropriate method"""

    # Check if spec files exist
    spec_dir = "ea_inputs/views"
    if os.path.exists(spec_dir) and os.listdir(spec_dir):
        # MVP6: Spec-driven mode
        from src.ea.view_builder import ViewBuilder
        builder = ViewBuilder()
        return builder.generate_views_from_specs()
    else:
        # MVP4: Auto-gen mode (backward compatible)
        from src.ea.archi_views import ViewGenerator
        generator = ViewGenerator()
        return generator.generate_all_views(ea_analysis, elements, relations)
```

**4.2 Migration Workflow**
```
User starts with auto-gen (MVP4):
1. Discovery → Auto-generates 7 generic views

User wants specific view (MVP6):
2. "create a spec for the CRM integration view"
3. AI generates YAML spec from existing view
4. User edits spec, regenerates
5. MVP6 mode activated (specs exist)

Both modes coexist:
- New discoveries → Auto-gen views (MVP4)
- Refined views → Spec-driven (MVP6)
- Users "graduate" views from auto-gen to spec-driven
```

## 🧪 Testing Strategy

### **Test 1: Basic Spec Generation**
```bash
# Given: Elements in archi_inputs/ (from discovery)
# When: User requests specific view

User: "create a view showing all critical applications"
AI: [generates spec]

Expected:
- File created: ea_inputs/views/critical_apps.yaml
- Spec contains: where: {criticality: "High"}
- User can review YAML before generating
```

### **Test 2: Deterministic Output**
```bash
# Given: Existing spec file
# When: Generate views 3 times

Run 1: Generate views.csv → View contains elements A, B, C at positions X1, Y1, X2, Y2
Run 2: Generate views.csv → View contains elements A, B, C at positions X1, Y1, X2, Y2
Run 3: Generate views.csv → View contains elements A, B, C at positions X1, Y1, X2, Y2

Expected: Identical output every time (deterministic)
```

### **Test 3: Spec Editing**
```bash
# Given: Existing spec with 3 elements
# When: User requests addition

User: "add the API gateway to the CRM integration view"
AI: [edits YAML] → adds element
AI: [regenerates views.csv]

Expected:
- YAML updated with new element
- views.csv contains 4 elements (previous 3 + new one)
- Layout adjusts automatically
```

### **Test 4: Hybrid Selection**
```bash
# Given: Spec with mixed selection types
elements:
  include:
    - where: {type: "Application-Component"}  # Finds 10 apps
    - name: "Legacy System X"                 # Finds 1 specific app by name
    - id: "id-abc123"                        # Finds 1 specific app by ID

Expected:
- Total 12 elements selected (10 + 1 + 1)
- No duplicates if overlap exists
- Exact matches for name and ID
```

### **Test 5: Transitive Inclusion**
```bash
# Given: Spec with transitive selector
elements:
  include:
    - where: {type: "Application-Component"}
    - where:
        type: "Business-Capability"
        serves: "included_applications"  # Transitive

Expected:
- Selects all Application-Components
- Finds all Business-Capabilities that serve those apps
- Includes both in view
```

### **Test 6: Viewpoint Validation**
```bash
# Given: Spec with invalid element type for viewpoint
view:
  viewpoint: "application_cooperation"
elements:
  include:
    - type: "Business-Actor"  # Not allowed in application cooperation viewpoint

Expected:
- Validation error: "Business-Actor not allowed in application_cooperation viewpoint"
- Suggestion: "Use Application-Component, Application-Interface, or Application-Service"
```

### **Test 7: Dual-Mode Coexistence**
```bash
# Scenario A: No spec files → MVP4 auto-gen
ea_inputs/views/ [empty]
→ Auto-generates 7 generic views

# Scenario B: Spec files exist → MVP6 spec-driven
ea_inputs/views/
  - crm_integration.yaml
  - security_architecture.yaml
→ Generates only views from specs (deterministic)

# Scenario C: User switches modes
Start: Auto-gen mode
User: "create a spec for the integration view"
AI: Converts auto-gen view → YAML spec
End: Spec-driven mode
```

## 📁 New File Structure

```
ea_inputs/
├── elements.csv                    # Existing: Element definitions
├── relations.csv                   # Existing: Relationship definitions
├── properties.csv                  # Existing: Property definitions
├── model.xml                       # Existing: ArchiMate Model Exchange
├── views.csv                       # Updated: Generated from specs OR auto-gen
└── views/                          # 🆕 NEW: View specifications
    ├── crm_qad_po_flow.yaml       # User-defined specific view
    ├── security_architecture.yaml  # User-defined specific view
    └── capability_heatmap.yaml     # User-defined specific view

ea_inputs/view_templates/           # 🆕 NEW: ArchiMate viewpoint templates
├── application_cooperation.yaml    # Standard ArchiMate viewpoint
├── capability_map.yaml             # Standard ArchiMate viewpoint
├── information_structure.yaml      # Standard ArchiMate viewpoint
├── technology_architecture.yaml    # Standard ArchiMate viewpoint
├── layered_view.yaml              # Standard ArchiMate viewpoint
├── migration_view.yaml            # Standard ArchiMate viewpoint
└── business_process_cooperation.yaml

src/ea/
├── ea_discovery.py                 # Existing: Element extraction
├── archi_export.py                 # Modified: Dual-mode view generation
├── archi_views.py                  # Existing: Auto-gen views (MVP4)
├── archi_layouts.py                # Existing: Layout algorithms (reused!)
├── data_providers.py               # Existing: ArchiMate data reader
├── view_builder.py                 # 🆕 NEW: Spec-driven view generation
├── spec_editor.py                  # 🆕 NEW: YAML spec editing
└── viewpoint_validator.py          # 🆕 NEW: ArchiMate viewpoint validation

src/mcp_server.py                   # Modified: Add new MCP tools
```

## 🔧 New MCP Tools

### **Tool 1: `ea_create_view_spec`**
```python
{
  "name": "ea_create_view_spec",
  "description": "Create a YAML specification for a specific architecture view",
  "inputSchema": {
    "view_name": "Name for the view",
    "description": "Natural language description of what to include",
    "viewpoint": "Optional: ArchiMate viewpoint (e.g., application_cooperation)"
  }
}

# Example:
ea_create_view_spec(
  view_name="CRM Integration Flow",
  description="Show CRM, QAD, purchase order flows, and Document Intelligence",
  viewpoint="application_cooperation"
)
→ Creates ea_inputs/views/crm_integration_flow.yaml
```

### **Tool 2: `ea_edit_view_spec`**
```python
{
  "name": "ea_edit_view_spec",
  "description": "Edit an existing view specification (add, remove, replace elements)",
  "inputSchema": {
    "view_name": "Name of the view to edit",
    "operation": "add | remove | replace",
    "element": "Element name or ID to operate on"
  }
}

# Example:
ea_edit_view_spec(
  view_name="CRM Integration Flow",
  operation="add",
  element="API Gateway"
)
→ Updates ea_inputs/views/crm_integration_flow.yaml
```

### **Tool 3: `ea_generate_views_from_specs`**
```python
{
  "name": "ea_generate_views_from_specs",
  "description": "Generate views.csv from YAML specifications (deterministic)",
  "inputSchema": {}
}

# Example:
ea_generate_views_from_specs()
→ Reads ea_inputs/views/*.yaml
→ Writes ea_inputs/views.csv (deterministic output)
→ Returns summary: "Generated 3 views from specs"
```

### **Tool 4: `ea_list_view_specs`**
```python
{
  "name": "ea_list_view_specs",
  "description": "List all view specifications and their contents",
  "inputSchema": {}
}

# Example:
ea_list_view_specs()
→ Returns:
  - CRM Integration Flow (5 elements, 8 relationships)
  - Security Architecture (12 elements, 15 relationships)
  - Capability Heatmap (20 capabilities, 30 relationships)
```

### **Tool 5: `ea_validate_view_spec`**
```python
{
  "name": "ea_validate_view_spec",
  "description": "Validate a view spec against ArchiMate viewpoint rules",
  "inputSchema": {
    "view_name": "Name of the view to validate"
  }
}

# Example:
ea_validate_view_spec(view_name="CRM Integration Flow")
→ Returns:
  ✅ All element types allowed in application_cooperation viewpoint
  ✅ All relationship types allowed
  ⚠️ Warning: Business-Actor typically not included in this viewpoint
```

## 🎯 Success Metrics

### **Determinism Benchmarks**
1. ✅ **Identical Output**: Same spec → Identical views.csv (100% reproducibility)
2. ✅ **Version Control**: Specs track in git, changes reviewable
3. ✅ **Business Specificity**: Views match exact business requirements

### **User Experience Improvements**
1. ✅ **Iterative Refinement**: "Add X", "Remove Y" works naturally
2. ✅ **Human-Readable Specs**: Business users can read/edit YAML
3. ✅ **Precision Control**: Mix of criteria, names, and IDs for flexibility

### **ArchiMate Compliance**
1. ✅ **Standard Viewpoints**: 7 ArchiMate viewpoints supported
2. ✅ **Validation**: Catch invalid element/relationship combinations
3. ✅ **Templates**: Accelerate view creation with standards

### **Backward Compatibility**
1. ✅ **Dual-Mode**: Auto-gen (MVP4) and spec-driven (MVP6) coexist
2. ✅ **Migration Path**: Users "graduate" views to specs when needed
3. ✅ **Zero Breaking Changes**: Existing workflows continue working

## 🎉 Business Impact

### **Before MVP6 (Unpredictable)**
```
Discovery → Random views each time
User: "I need a specific CRM integration view"
AI: "Here are 7 generic views, pick one and manually adjust in Archi"
Result: Hours of manual work, inconsistent outputs
```

### **After MVP6 (Deterministic)**
```
Discovery → Generic views (quick start)
User: "Create a spec for CRM-QAD purchase order flow"
AI: [generates YAML spec] "Review this spec"
User: [edits YAML] "Add API gateway"
AI: [updates spec] → [generates view] "Done!"
Result: Minutes to create, identical every time, version controlled
```

### **Key Wins**
- **Repeatability**: Same view, every time (critical for documentation)
- **Iteration**: Business users refine views until perfect
- **Version Control**: Specs tracked in git (audit trail)
- **Business Value**: Views match exact business needs, not generic templates
- **Efficiency**: No manual Archi editing needed

---

## 📊 Implementation Checklist

### **Phase 1: Core Engine** (Week 1)
- [ ] Create `src/ea/view_builder.py` with spec parsing
- [ ] Implement element selection (criteria, name, ID)
- [ ] Integrate with existing `ArchiMateProvider`
- [ ] Implement relationship filtering
- [ ] Integrate existing layout algorithms
- [ ] Generate views.csv in existing format
- [ ] Unit tests for ViewBuilder

### **Phase 2: Conversational Interface** (Week 1-2)
- [ ] Create `src/ea/spec_editor.py` with YAML editing
- [ ] Implement `ea_create_view_spec` MCP tool
- [ ] Implement `ea_edit_view_spec` MCP tool
- [ ] Implement `ea_generate_views_from_specs` MCP tool
- [ ] Add natural language parsing for spec operations
- [ ] Integration tests for conversational workflow

### **Phase 3: ArchiMate Viewpoints** (Week 2)
- [ ] Create 7 viewpoint templates in `ea_inputs/view_templates/`
- [ ] Create `src/ea/viewpoint_validator.py`
- [ ] Implement validation rules per viewpoint
- [ ] Implement `ea_validate_view_spec` MCP tool
- [ ] Template-based spec creation
- [ ] Validation tests

### **Phase 4: Dual-Mode System** (Week 2-3)
- [ ] Update `src/ea/archi_export.py` with mode detection
- [ ] Implement mode switching logic
- [ ] Create migration helper (auto-gen → spec)
- [ ] End-to-end tests for both modes
- [ ] Documentation updates in CLAUDE.md
- [ ] User guide for spec creation

### **Phase 5: Polish & Documentation** (Week 3)
- [ ] Add `ea_list_view_specs` MCP tool
- [ ] Create example spec files
- [ ] Update MCP server with all new tools
- [ ] Create user guide for business users
- [ ] Performance testing (large models)
- [ ] Error handling and user feedback

---

## 🔄 MVP6 Success Definition

**MVP6 is complete when:**
1. ✅ Users can create view specs via natural language
2. ✅ Specs generate deterministic views.csv (100% reproducible)
3. ✅ Users can edit specs naturally ("add X", "remove Y")
4. ✅ All 7 ArchiMate viewpoints supported with templates
5. ✅ Validation catches invalid specs with helpful suggestions
6. ✅ Dual-mode system works (auto-gen + spec-driven)
7. ✅ Business users can read and edit YAML specs
8. ✅ Views import successfully into Archi tool

**The transformation from "random views each time" to "exact views, every time" represents a fundamental shift from AI-generated artifacts to AI-assisted business-controlled artifacts.**
