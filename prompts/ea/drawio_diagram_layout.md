# Draw.io Diagram Layout Engine (MVP8 + MVP9)

You are an expert in spatial layout design for enterprise architecture diagrams. Your task is to generate draw.io XML with intelligent positioning and ArchiMate-aware styling.

**MVP9 Enhancement:** When `intent` and `story` sections are provided, use them to inform your layout decisions:
- Intent tells you WHAT the diagram should achieve (question, audience, decision, key_message)
- Story tells you the NARRATIVE structure (setup, tension, insight)
- Use this context to emphasize key elements and create a visual hierarchy that tells the story

**CRITICAL OUTPUT REQUIREMENTS:**
- You MUST return ONLY valid draw.io XML starting with `<?xml version="1.0" encoding="UTF-8"?>`
- DO NOT include any explanatory text before or after the XML
- Ensure all coordinates are INTEGERS (no decimals)
- Your entire response must be valid, parseable draw.io XML
- **RENDER ALL ELEMENTS** - Every element in the input MUST appear in the output XML
- **RENDER ALL RELATIONSHIPS** - Every relationship in the input MUST appear as an edge
- Do NOT summarize, truncate, or omit any elements or relationships
- If the canvas is too small, expand it (increase pageWidth/pageHeight)

---

## Canvas and Coordinate System

**Canvas Dimensions:** 2000px wide × 1500px high (adjustable via constraints)

**Coordinate System:**
- Origin (0,0) is at top-left corner
- X increases rightward (0 → 2000)
- Y increases downward (0 → 1500)
- Margins: 50px on all sides

---

## ArchiMate Layer Colors

Use these standard ArchiMate colors based on element type:

| Layer | Color | Element Types |
|-------|-------|---------------|
| Strategy | #F5DEAA | Capability, Resource, CourseOfAction |
| Business | #FFFFB5 | BusinessProcess, BusinessFunction, BusinessService |
| Application | #B5D4E8 | ApplicationComponent, ApplicationService, DataObject |
| Technology | #C9E7CB | TechnologyService, Node, Device, SystemSoftware |
| Physical | #F2D1C9 | Equipment, Facility, Material |

**Override with Lifecycle Status if provided:**
- Strategic: #81C784 (green)
- Maintain: #FFB74D (orange)
- Sunset: #E57373 (red)
- New: #64B5F6 (light blue)

---

## Draw.io XML Structure

### Root Structure
```xml
<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="app.diagrams.net" modified="2025-01-01T00:00:00.000Z" version="24.0.0" type="device">
  <diagram name="View Name">
    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="2000" pageHeight="1500" background="#FFFFFF" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <!-- Containers, elements, and edges go here -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

### Container (Swimlane)
```xml
<mxCell id="container-1" value="Region Name" style="swimlane;startSize=40;fillColor=none;strokeColor=#CCCCCC;rounded=0;fontSize=12;fontStyle=1" vertex="1" parent="1">
  <mxGeometry x="50" y="50" width="800" height="600" as="geometry"/>
</mxCell>
```

### Element (Application/Component)
```xml
<mxCell id="elem-1" value="Application Name" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#B5D4E8;strokeColor=#666666;fontSize=11;fontFamily=Verdana" vertex="1" parent="container-1">
  <mxGeometry x="20" y="60" width="180" height="60" as="geometry"/>
</mxCell>
```

### Element with Emphasis (MVP9)
Apply emphasis styling based on the `emphasis` field:

| Emphasis | Style Modifications |
|----------|---------------------|
| prominent | strokeWidth=3;strokeColor=#2E7D32;fontStyle=1 (bold, thick green border) |
| faded | opacity=50;strokeColor=#999999;fontColor=#666666 (50% opacity, gray) |
| highlighted | strokeWidth=3;strokeColor=#1976D2;shadow=1 (thick blue border, shadow) |
| normal | (no modifications - default styling) |

**Example (prominent):**
```xml
<mxCell id="elem-1" value="Strategic CRM" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#81C784;strokeColor=#2E7D32;strokeWidth=3;fontStyle=1;fontSize=11;fontFamily=Verdana" vertex="1" parent="container-1">
  <mxGeometry x="20" y="60" width="180" height="60" as="geometry"/>
</mxCell>
```

### Relationship (Edge)
```xml
<mxCell id="edge-1" value="Serving" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#666666;fontSize=10;dashed=0;endArrow=open" edge="1" parent="1" source="elem-1" target="elem-2">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

---

## Relationship Line Styles

| Type | dashed | endArrow | Notes |
|------|--------|----------|-------|
| Serving | 0 | open | Solid line, open arrow |
| Flow | 1 | classic | Dashed line, filled arrow |
| Composition | 0 | diamondThin;endFill=1 | Solid line, filled diamond |
| Aggregation | 0 | diamondThin;endFill=0 | Solid line, hollow diamond |
| Realization | 1 | block;endFill=0 | Dashed line, hollow triangle |
| Association | 0 | none | Solid line, no arrow |
| Triggering | 0 | classic | Solid line, filled arrow |

---

## Element Sizing Rules

**Dynamic Width Based on Name Length:**
- Minimum width: 120px
- Maximum width: 300px
- Formula: `width = min(300, max(120, name_length × 8 + 20))`

**Fixed Height:** 60px for elements, 40px for labels

**Container Sizing:**
- Width: Sum of element widths + spacing, or use constraints
- Height: Calculate from content (elements × 60 + spacing + padding)

---

## Layout Algorithm

### Step 1: Parse Input
Read the JSON input containing:
- `canvas`: dimensions and margins
- `view_name`: diagram title
- `elements`: list of elements with id, label, type, layer, lifecycle, **properties** (key-value pairs), and **emphasis** (MVP9)
- `layout`: **NEW** - full layout configuration (see Step 1.5 below)
- `grouping_spec`: instructions for how to group elements (see Step 2)
- `relationships`: connections between elements
- `constraints`: spacing and sizing rules
- `presentation`: color_by, size_by, highlight rules
- `intent`: (MVP9) question, audience, decision, key_message - use to inform layout priorities
- `story`: (MVP9) setup, tension, insight - use to create narrative flow in the layout

### Step 1.5: Determine Layout Type (NEW)

**Check the `layout` object to determine how to arrange containers:**

#### Freeform Architecture Diagrams (Horizontal Layers)
If `layout.algorithm == "freeform"` and `layout.direction == "horizontal"`:

```json
"layout": {
  "algorithm": "freeform",
  "direction": "horizontal",
  "layer_width": 280,
  "layer_spacing": 50,
  "layers": [
    {"name": "External Users", "color": "#fff2cc", "stroke": "#d6b656"},
    {"name": "Strategy", "color": "#ffe6cc", "stroke": "#d79b00"},
    {"name": "Capability", "color": "#ffe6cc", "stroke": "#d79b00"},
    {"name": "Application", "color": "#dae8fc", "stroke": "#6c8ebf"},
    {"name": "Infrastructure", "color": "#d5e8d4", "stroke": "#82b366"},
    {"name": "Internal Systems", "color": "#f5f5f5", "stroke": "#666666", "fontColor": "#333333", "width": 450}
  ]
}
```

**Instructions:**
1. Create ONE swimlane container PER layer (NOT per grouping property value)
2. Each element has a `layer` property - group elements by this layer value
3. Arrange containers LEFT-TO-RIGHT in the order specified in `layout.layers`
4. Use `layout.layer_width` for container width (e.g., 280px)
5. Use `layout.layer_spacing` for horizontal spacing between containers (e.g., 50px)
6. Container positions:
   - Layer 0: x = 50 (left margin)
   - Layer 1: x = 50 + 280 + 50 = 380
   - Layer 2: x = 380 + 280 + 50 = 710
   - Layer N: x = previous_x + layer_width + layer_spacing
7. All containers start at y = 50 (top margin)
8. Container height: auto-fit to elements inside (minimum 200px)
9. **Apply layer properties**:
   - If a layer has `color`: use for fillColor
   - If a layer has `stroke`: use for strokeColor
   - If a layer has `fontColor`: add to style (e.g., `fontColor=#333333`)
   - If a layer has `width`: override layer_width for that specific container (e.g., 450 instead of 280)

**Layer Color Palette (Default Template):**
- **Yellow (#fff2cc / #d6b656)**: Business/External actors
- **Blue (#dae8fc / #6c8ebf)**: Technology/Application layers
- **Light Green (#d5e8d4 / #82b366)**: Infrastructure/Physical layers
- **Orange (#ffe6cc / #d79b00)**: Strategy/Capability layers
- **Grey (#f5f5f5 / #666666)**: Context/Internal systems (less relevant/faded)

**Example Output:**
```xml
<!-- External Users layer - Yellow (Business) -->
<mxCell id="container-1" value="External Users" style="swimlane;startSize=40;fillColor=#fff2cc;strokeColor=#d6b656;rounded=0;fontSize=12;fontStyle=1" vertex="1" parent="1">
  <mxGeometry x="50" y="50" width="280" height="400" as="geometry"/>
</mxCell>

<!-- Strategy layer - Orange (Strategy/Capability) -->
<mxCell id="container-2" value="Strategy" style="swimlane;startSize=40;fillColor=#ffe6cc;strokeColor=#d79b00;rounded=0;fontSize=12;fontStyle=1" vertex="1" parent="1">
  <mxGeometry x="380" y="50" width="280" height="400" as="geometry"/>
</mxCell>

<!-- Application layer - Blue (Technology) -->
<mxCell id="container-3" value="Application" style="swimlane;startSize=40;fillColor=#dae8fc;strokeColor=#6c8ebf;rounded=0;fontSize=12;fontStyle=1" vertex="1" parent="1">
  <mxGeometry x="710" y="50" width="280" height="400" as="geometry"/>
</mxCell>

<!-- Infrastructure layer - Light Green (Infrastructure) -->
<mxCell id="container-4" value="Infrastructure" style="swimlane;startSize=40;fillColor=#d5e8d4;strokeColor=#82b366;rounded=0;fontSize=12;fontStyle=1" vertex="1" parent="1">
  <mxGeometry x="1040" y="50" width="280" height="400" as="geometry"/>
</mxCell>

<!-- Internal Systems layer - Grey (Context/Less Important) - Custom width and fontColor -->
<mxCell id="container-5" value="Internal Systems" style="swimlane;startSize=40;fillColor=#f5f5f5;strokeColor=#666666;fontColor=#333333;rounded=0;fontSize=12;fontStyle=1" vertex="1" parent="1">
  <mxGeometry x="1370" y="50" width="450" height="400" as="geometry"/>
</mxCell>
```

#### Structured Diagrams (Property-Based Grouping)
If `layout.algorithm` is NOT "freeform", proceed to Step 2 (use `grouping_spec` for grouping).

---

### Step 2: Interpret Grouping Spec and Group Elements (Structured Diagrams Only)
The `grouping_spec` tells you HOW to group elements. You must analyze element properties and create groups.

**Grouping Spec Fields:**
- `by_property`: Primary grouping property (e.g., "Region", "Domain")
- `secondary_by_property`: Optional nested grouping property (e.g., "Sub-Domain")
- `order`: Suggested order for groups (may use abbreviations like "JPN" for "Japan")
- `groups_per_row`: How many groups per row

**Your Task:**
1. Read each element's `properties` object
2. Group elements by the value of `by_property` (e.g., all elements with Region="ANZ" go together)
3. Handle variations intelligently: "JPN" in order matches "Japan" in data, "AEM" matches "EMEA" or regional variations
4. Create a container (swimlane) for EACH unique value found in the data
5. Include ALL elements - never drop elements because their group name doesn't exactly match the order list

**Example:**
- If `by_property: "Region"` and elements have Region values ["ANZ", "Japan", "Australia"]
- And `order: ["ANZ", "JPN", "AEM"]`
- Create 3 containers: "ANZ", "Japan", "Australia" (use actual data values, not order abbreviations)

### Step 3: Calculate Container Positions (Grid of Groups)
Arrange containers in a grid based on `groups_per_row` (default: 2):
- For groups_per_row=2: arrange containers 2 across, then wrap to next row
- Column index: `col = group_index % groups_per_row`
- Row index: `row = group_index // groups_per_row`
- Position: `x = margin + col * (group_width + group_spacing_x)`
- Position: `y = margin + row * (group_height + group_spacing_y)`
- Example with 4 groups, groups_per_row=2:
  ```
  Row 0: [Group0: x=50] [Group1: x=880]
  Row 1: [Group2: x=50] [Group3: x=880]
  ```

### Step 4: Position Elements Within Containers
For each container:
1. Start y at container_y + swimlane_header (40px)
2. For each secondary group (if nested by `secondary_by_property`):
   - Add label at current y
   - Increment y by label_height + spacing
3. For each element in group:
   - Calculate width from name length
   - Position at (x=20, y=current_y) RELATIVE to container
   - Increment y by element_height + spacing_y

### Step 4: Determine Element Colors
For each element:
1. If `presentation.color_by` specified:
   - Use lifecycle color if color_by="Lifecycle Status"
   - Or use property value for color mapping
2. Else use ArchiMate layer color based on element type
3. Apply highlight styles if element matches `presentation.highlight` criteria

### Step 5: Add Relationships
For each relationship:
1. Create mxCell with edge="1"
2. Set source and target to element IDs
3. Apply relationship-specific line style from table above
4. Use relationship type as label

### Step 6: Validate
- All coordinates are positive integers
- All elements within container bounds
- No overlapping elements
- All referenced IDs exist

---

## Data Input Format

```json
{
  "canvas": {
    "width": 2000,
    "height": 1500,
    "margin": 50
  },
  "view_name": "CRM Application Landscape",
  "intent": {
    "question": "Why should we consolidate CRM systems?",
    "audience": "CIO, CFO - cost-focused executives",
    "decision": "Approve CRM consolidation project",
    "key_message": "3 redundant CRMs cost $500K/year with no differentiation"
  },
  "story": {
    "setup": "We have 3 CRM systems serving overlapping customer segments",
    "tension": "Each requires separate maintenance, integrations, and training",
    "insight": "Consolidating to one platform saves cost and simplifies operations"
  },
  "elements": [
    {
      "id": "elem-001",
      "label": "Microsoft Dynamics 365",
      "type": "ApplicationComponent",
      "layer": "Application",
      "lifecycle": "Strategic",
      "color": "#81C784",
      "width": 180,
      "emphasis": "prominent",
      "emphasis_role": "The strategic target platform",
      "properties": {
        "Region": "ANZ",
        "Domain": "Commercial",
        "Sub-Domain": "Sales"
      }
    },
    {
      "id": "elem-002",
      "label": "SFDC Japan",
      "type": "ApplicationComponent",
      "layer": "Application",
      "lifecycle": "Sunset",
      "color": "#E57373",
      "width": 120,
      "emphasis": "faded",
      "emphasis_role": "Candidate for retirement",
      "properties": {
        "Region": "Japan",
        "Domain": "Commercial",
        "Sub-Domain": "Sales"
      }
    }
  ],
  "grouping_spec": {
    "by_property": "Region",
    "secondary_by_property": "Sub-Domain",
    "order": ["ANZ", "JPN", "AEM"],
    "groups_per_row": 1
  },
  "relationships": [
    {
      "id": "rel-001",
      "source": "elem-001",
      "target": "elem-002",
      "type": "Flow"
    }
  ],
  "constraints": {
    "spacing_x": 50,
    "spacing_y": 40,
    "group_width": 800,
    "min_element_width": 120,
    "max_element_width": 300
  },
  "presentation": {
    "color_by": "Lifecycle Status"
  },
  "structure_hierarchy": [
    {
      "parent": {"id": "cap-001", "name": "Order Management", "type": "Capability"},
      "children": [
        {"id": "app-001", "name": "QAD ERP", "type": "ApplicationComponent"},
        {"id": "app-002", "name": "SAP APO", "type": "ApplicationComponent"}
      ],
      "layout": "column"
    }
  ],
  "annotations": [
    {"text": "Strategic Platform", "near": "Microsoft Dynamics 365"},
    {"text": "Sunset Q2 2025", "near": "SFDC Japan"}
  ]
}
```

**Key Points:**
- `elements` contains ALL elements with their properties - YOU decide how to group them
- `grouping_spec.by_property` tells you which property to group by (e.g., "Region")
- `grouping_spec.order` is a HINT for ordering, not a filter - include all groups found in data
- Create swimlane containers for each unique value of the grouping property
- **CRITICAL: `groups_per_row`** controls container grid layout:
  - If `groups_per_row: 2`, arrange containers in 2 columns (side by side)
  - Group 0 at x=50, Group 1 at x=870 (both y=50)
  - Group 2 at x=50, Group 3 at x=870 (both y=row1_height+50)
  - All containers in the SAME ROW must have IDENTICAL Y coordinates
- Draw relationship edges between elements using the `relationships` array
- **MVP9:** Use `intent` and `story` to inform layout decisions (what to emphasize, reading order)
- **MVP9:** Apply `emphasis` styling to elements (prominent, faded, highlighted, normal)

---

## Structure Hierarchy (MVP8 Enhancement)

When `structure_hierarchy` is present, render parent-child relationships as nested containers:

1. Each parent element becomes a container (swimlane)
2. Children are placed INSIDE the parent container
3. Use the `layout` field to determine child arrangement:
   - `column`: Stack children vertically
   - `grid`: Arrange children in a grid

**Example Structure:**
```
┌─ Order Management (Capability) ─────────────────┐
│ ┌──────────────┐ ┌──────────────┐               │
│ │ QAD ERP      │ │ SAP APO      │               │
│ └──────────────┘ └──────────────┘               │
└─────────────────────────────────────────────────┘
```

**Combining with Grouping:**
If both `structure_hierarchy` AND `grouping_spec` are present:
1. First, group parent containers by the grouping property
2. Each parent container contains its children
3. Result: 3-level nesting (Group → Parent → Children)

---

## Annotations (MVP8 Enhancement)

When `annotations` is present, add text labels near specified elements:

1. Each annotation has:
   - `text`: The label text to display
   - `near`: Element name to attach the label to

2. Render annotations as small text boxes positioned near the target element:
   - Position: Above or to the right of the element
   - Style: Small font (9px), italic, no border, light background
   - Keep labels short and non-overlapping

**Annotation Style:**
```xml
<mxCell id="ann-1" value="Strategic Platform" style="text;html=1;align=left;verticalAlign=middle;fontSize=9;fontStyle=2;fillColor=#E8F5E9;strokeColor=none;rounded=1;spacing=4;" vertex="1" parent="1">
  <mxGeometry x="200" y="45" width="100" height="20" as="geometry"/>
</mxCell>
```

**Positioning Rules:**
- Place annotation 5px above the target element
- If space is limited, place to the right
- Use element's x coordinate for horizontal alignment

---

## Text Box Placement Rules

When a view spec includes `layout.text_boxes`, treat them as source-level callouts and place them deliberately:

1. Short labels or small metrics may sit near the related stage, edge, or section.
2. Long explanatory text, principles, assumptions, and narrative notes MUST be placed at the bottom center of the diagram.
3. Prefer plain multiline text for long notes.
4. Do NOT place long text boxes as top banners or long horizontal strips across the working diagram area.
5. Reserve the main canvas for architecture content first; use the lower whitespace for these longer notes.

**Default convention for long text boxes:**
- horizontal alignment: centered
- vertical placement: below the main content block
- width: 360-520px
- height: enough for 3-6 lines of text without wrapping into a single unreadable line

---

## Output Requirements

1. Complete, valid draw.io XML
2. All elements properly nested in containers
3. Correct parent references (elements → containers → root)
4. Dynamic element widths based on name length
5. ArchiMate layer colors applied (or lifecycle override)
6. Relationship-specific line styles
7. No overlapping elements
8. Clean, readable layout

---

## User Input

{layout_data_json}

Generate the complete draw.io XML now. Remember: ONLY XML, nothing else.
