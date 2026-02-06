# MVP10: Interactive EA Portal

## Status: Planning

**Date:** 2026-01-12

---

## Overview

MVP10 delivers an **interactive web portal** for navigating enterprise architecture diagrams. Unlike static publishing (wikis, PowerPoint, PDFs), the portal enables element-level navigation across views while preserving the AI-generated diagram quality from MVP8.

**Core Value Proposition:** Click "Microsoft Dynamics CRM" in a roadmap view → navigate to the application landscape view with that element highlighted → explore its relationships → jump to integration architecture.

**Inspiration:** iServer's portal experience (diagram navigation, shared element model) without the performance/complexity issues (slow publication, clunky UI).

---

## Goal

Build a lightweight, fast web portal that:
1. **Displays pre-generated diagrams** with exact AI layout quality
2. **Enables element-level navigation** across multiple views
3. **Shows element context** (properties, relationships, appearances)
4. **Supports cross-diagram movement** via "Appears in" links
5. **Deploys to Azure Container Apps** (existing infrastructure)

**Non-Goals for MVP10:**
- Search (deferred to MVP11)
- Filtering/dynamic queries (deferred)
- Real-time model editing (read-only portal)
- Authentication (manual republish acceptable, AAD deferred)

---

## Architecture

### Two-Phase Design

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: BUILD (Local CLI)                                     │
│                                                                  │
│  ea_diagrams/*.drawio + archi_inputs/* + ea_inputs/views/*.yaml │
│                           ↓                                      │
│                   build_portal()                                 │
│                           ↓                                      │
│              portal/ directory (static files)                    │
│              ├── index.html                                      │
│              ├── dist/app.js (Vue bundle)                        │
│              ├── diagrams/*.svg (with element IDs)               │
│              └── data/*.json (indexes)                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Deploy
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2: RUNTIME (ACA)                                         │
│                                                                  │
│  FastAPI app serves static files                                │
│       ↓                                                          │
│  Browser loads Vue.js SPA                                       │
│       ↓                                                          │
│  User clicks element in SVG                                     │
│       ↓                                                          │
│  JS queries element_index.json                                  │
│       ↓                                                          │
│  Shows detail panel, enables navigation                         │
└─────────────────────────────────────────────────────────────────┘
```

### Key Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| **Pre-render diagrams to SVG** | Preserves AI layout quality, fast browser rendering |
| **Static JSON indexes** | No database needed, instant queries, easy to deploy |
| **Vue.js SPA** | Rich interactivity, component model, mature ecosystem |
| **FastAPI static server** | Simple, Python-native, ACA-ready |
| **Build-time data processing** | Move complexity to build phase, runtime is just serving files |

---

## Component Breakdown

### 1. Portal Builder (`src/ea/portal_builder.py`)

**Purpose:** Convert diagrams + model data into portal-ready static files

**Main Function:**
```python
def build_portal(
    diagrams_dir: str = "ea_diagrams",
    model_dir: str = "archi_inputs",
    specs_dir: str = "ea_inputs/views",
    output_dir: str = "portal"
) -> dict:
    """
    Build interactive portal from existing diagrams and model data.

    Returns:
        {
            "views_processed": 12,
            "elements_indexed": 145,
            "relationships_mapped": 203,
            "output_path": "portal/"
        }
    """
```

**Steps:**
1. **Find all .drawio files** in `ea_diagrams/`
2. **Convert to SVG** with element IDs embedded
3. **Read ArchiMate model** from `archi_inputs/`
4. **Read YAML specs** from `ea_inputs/views/`
5. **Generate JSON indexes:**
   - `view_registry.json` - Available views with metadata
   - `element_index.json` - All elements with properties and appearances
   - `relationship_graph.json` - Element connections
6. **Copy frontend files** (HTML, JS, CSS)
7. **Output to `portal/` directory** (ready for deployment)

### 2. SVG Converter (`src/ea/drawio_to_svg.py`)

**Purpose:** Convert .drawio XML to SVG with stable element IDs

**Main Function:**
```python
def convert_drawio_to_svg(
    drawio_path: str,
    output_path: str,
    preserve_element_ids: bool = True
) -> dict:
    """
    Convert draw.io diagram to SVG with interactive features.

    Returns:
        {
            "svg_path": "portal/diagrams/commercial_roadmap.svg",
            "elements_found": 10,
            "element_ids": ["elem-abc123", "elem-def456", ...]
        }
    """
```

**Implementation Notes:**
- Parse .drawio XML structure (mxfile → diagram → mxGraphModel → root → mxCell)
- Extract `mxCell` elements with `value` attribute (these are diagram elements)
- Map cell IDs to element names (match against `archi_inputs/elements.csv`)
- Inject `data-element-id` attributes into SVG shapes
- Preserve viewBox, dimensions, styles from original
- Add CSS classes for hover effects

**Challenge:** draw.io uses internal cell IDs, need to map to ArchiMate element IDs

**Solution:**
- Match by element `value` attribute (name) against `elements.csv`
- Fallback: use hash of element name if exact ID not found
- Log unmapped elements for manual review

### 3. Data Index Generator (`src/ea/portal_indexes.py`)

**Purpose:** Generate JSON data structures for frontend

**Functions:**

```python
def generate_view_registry(specs_dir: str, diagrams_dir: str) -> dict:
    """Maps view_id → view metadata"""

def generate_element_index(
    elements_csv: str,
    properties_csv: str,
    view_registry: dict
) -> dict:
    """Maps element_id → element data + appearances"""

def generate_relationship_graph(
    relations_csv: str,
    elements_csv: str
) -> dict:
    """Maps element_id → connected elements"""
```

### 4. Frontend Application (`portal/src/`)

**Tech Stack:**
- Vue 3 (Composition API)
- Vite (build tool)
- Pinia (state management)
- SVG Pan Zoom library (diagram interaction)

**Component Structure:**
```
portal/src/
├── App.vue                 # Root component, 3-column layout
├── components/
│   ├── ViewList.vue        # Left sidebar - view navigator
│   ├── DiagramViewer.vue   # Center - SVG display with pan/zoom
│   ├── ElementPanel.vue    # Right sidebar - element details
│   └── ViewPicker.vue      # Modal for multi-view selection
├── stores/
│   ├── views.js            # View registry state
│   ├── elements.js         # Element index state
│   └── navigation.js       # Current view/element state
└── main.js                 # App initialization
```

### 5. Backend Server (`src/ea/portal_server.py`)

**Purpose:** Serve static files to browser

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Serve portal static files
app.mount("/", StaticFiles(directory="portal", html=True), name="portal")

# Health check for ACA
@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

**Alternative:** Could use nginx instead of FastAPI for pure static serving

### 6. MCP Tools

**New Tools:**

```python
@mcp_server.tool()
def ea_build_portal() -> dict:
    """
    Build interactive EA portal from current diagrams and model.

    Generates portal/ directory ready for deployment to ACA.
    """

@mcp_server.tool()
def ea_preview_portal(port: int = 8000) -> str:
    """
    Start local server to preview portal before deployment.

    Returns URL to access portal in browser.
    """
```

---

## Data Structures

### View Registry (`portal/data/view_registry.json`)

```json
{
  "commercial_roadmap": {
    "id": "commercial_roadmap",
    "name": "Commercial CRM Roadmap",
    "diagram_path": "diagrams/commercial_roadmap.svg",
    "spec_path": "ea_inputs/views/crm-consolidation/01_current_state.yaml",
    "category": "crm-consolidation",
    "intent": {
      "question": "What's the CRM consolidation plan?",
      "audience": "Steering Committee",
      "key_message": "Consolidate 3 CRMs to single platform by Q4"
    },
    "elements": ["elem-abc123", "elem-def456", "elem-xyz789"],
    "metadata": {
      "created": "2026-01-10",
      "last_updated": "2026-01-12"
    }
  },
  "commercial_landscape": {
    "id": "commercial_landscape",
    "name": "Commercial Application Landscape",
    "diagram_path": "diagrams/commercial_landscape.svg",
    "category": "commercial",
    "elements": ["elem-abc123", "elem-ghi789", ...]
  }
}
```

### Element Index (`portal/data/element_index.json`)

```json
{
  "elem-abc123": {
    "id": "elem-abc123",
    "name": "Microsoft Dynamics CRM",
    "type": "ApplicationComponent",
    "properties": {
      "Domain": "Commercial",
      "Lifecycle Status": "Strategic",
      "Region": "Global",
      "Business Criticality": "High"
    },
    "appears_in": [
      {
        "view_id": "commercial_roadmap",
        "view_name": "Commercial CRM Roadmap",
        "context": "H3 (TO-BE)",
        "emphasis": "prominent"
      },
      {
        "view_id": "commercial_landscape",
        "view_name": "Commercial Application Landscape",
        "context": "ANZ Region"
      },
      {
        "view_id": "integration_architecture",
        "view_name": "Integration Architecture",
        "context": "Hub System"
      }
    ]
  }
}
```

### Relationship Graph (`portal/data/relationship_graph.json`)

```json
{
  "elem-abc123": {
    "outbound": [
      {
        "target_id": "elem-xyz789",
        "target_name": "UDW Agent",
        "type": "Serving",
        "description": "CRM sends customer data to data warehouse"
      }
    ],
    "inbound": [
      {
        "source_id": "elem-def456",
        "source_name": "Microsoft Document Intelligence",
        "type": "Serving",
        "description": "Document processing supports CRM workflows"
      }
    ]
  }
}
```

---

## Frontend Design

### Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│ EA Portal                                    [Refresh] [View Source]  │
├──────────┬───────────────────────────────────────────┬───────────────┤
│          │                                           │               │
│ VIEWS    │           DIAGRAM VIEWER                  │               │
│          │                                           │               │
│ Commercial                                           │               │
│  Roadmap │   ┌──────────────────────────────┐       │               │
│  Landscape   │                              │       │               │
│  Integr.. │  │    [SVG Diagram]             │       │               │
│          │   │                              │       │               │
│ Operations   │    Pan/Zoom enabled          │       │               │
│  App Map │   │                              │       │               │
│  Matrix  │   └──────────────────────────────┘       │               │
│          │                                           │               │
│ CRM Consol.                                          │               │
│  01 Curr.│                                           │               │
│  02 Targ.│                                           │               │
│          │                                           │               │
└──────────┴───────────────────────────────────────────┴───────────────┘
         250px              flex-grow                       0px (hidden)
```

**When element clicked:**

```
┌──────────────────────────────────────────────────────────────────────┐
│ EA Portal                                    [Refresh] [View Source]  │
├──────────┬───────────────────────────────────────────┬───────────────┤
│          │                                           │               │
│ VIEWS    │           DIAGRAM VIEWER                  │ ELEMENT PANEL │
│          │                                           │               │
│ Commercial                                           │ MS Dynamics   │
│  Roadmap │   ┌──────────────────────────────┐       │ CRM           │
│  Landscape   │                              │       │ ─────────────│
│  Integr..│   │    [SVG with highlighted     │       │ Type:         │
│          │   │     element]                 │       │ Application   │
│ Operations   │                              │       │               │
│  App Map │   │                              │       │ Domain:       │
│  Matrix  │   └──────────────────────────────┘       │ Commercial    │
│          │                                           │               │
│ CRM Consol.                                          │ Status:       │
│  01 Curr.│                                           │ Strategic     │
│  02 Targ.│                                           │               │
│          │                                           │ Relationships │
│          │                                           │ → UDW Agent   │
│          │                                           │ ← Doc Intel   │
│          │                                           │               │
│          │                                           │ Appears in:   │
│          │                                           │ • Roadmap ✓   │
│          │                                           │ • Landscape   │
│          │                                           │ • Integration │
└──────────┴───────────────────────────────────────────┴───────────────┘
         250px              flex-grow                      350px (visible)
```

### User Interactions

**1. View Selection:**
- Click view in left sidebar → Load diagram in center panel
- Active view highlighted in sidebar
- URL updates: `/view/commercial_roadmap`

**2. Element Click:**
- Click element in SVG → Highlight element, show detail panel
- Panel slides in from right
- URL updates: `/view/commercial_roadmap/elem-abc123`

**3. Cross-View Navigation:**
- In element panel, click "Appears in: Commercial Landscape"
- Diagram viewer loads new SVG
- Element remains highlighted in new view
- URL updates: `/view/commercial_landscape/elem-abc123`

**4. Relationship Navigation:**
- In element panel, click relationship target "UDW Agent"
- If target appears in multiple views → Show view picker modal
- User selects view → Navigate to that view with target highlighted
- If target appears in only one view → Navigate directly

**5. Multi-View Selection:**
- Modal shows: "UDW Agent appears in 3 views. Where do you want to go?"
- List of views with context snippets
- Click to navigate

### Styling

**Colors:**
- Background: `#F5F5F5` (light gray)
- Sidebar: `#FFFFFF` (white)
- Active view: `#E3F2FD` (light blue)
- Panel: `#FFFFFF` (white)
- Element highlight: `#FFC107` (amber border, 3px)

**Typography:**
- Headers: `Segoe UI`, 16px, 600 weight
- Body: `Segoe UI`, 14px, 400 weight
- Code/IDs: `Consolas`, 12px

**Transitions:**
- Panel slide: 200ms ease-in-out
- Element highlight: 150ms ease
- View fade: 300ms ease

---

## Deployment Strategy

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy portal static files
COPY portal/ ./portal/

# Copy server
COPY src/ea/portal_server.py ./server.py

# Expose port
EXPOSE 8000

# Run server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Azure Container Apps Configuration

**Resource Requirements:**
- CPU: 0.5 cores
- Memory: 1GB
- Min replicas: 1
- Max replicas: 3

**Environment Variables:**
- `PORT`: 8000
- `LOG_LEVEL`: info

**Deployment Commands:**

```bash
# Build container
docker build -t ea-portal:latest .

# Tag for ACR
docker tag ea-portal:latest yourregistry.azurecr.io/ea-portal:latest

# Push to ACR
docker push yourregistry.azurecr.io/ea-portal:latest

# Create/update ACA
az containerapp create \
  --name ea-portal \
  --resource-group your-rg \
  --environment your-aca-env \
  --image yourregistry.azurecr.io/ea-portal:latest \
  --target-port 8000 \
  --ingress external \
  --cpu 0.5 --memory 1Gi
```

---

## Integration Points

### With Existing Workflows

**Diagram Generation (MVP8) → Portal Build (MVP10):**

```
User: "Create commercial roadmap diagram"
    ↓
ea_generate_diagram("ea_inputs/views/commercial_roadmap.yaml")
    ↓
Generates: ea_diagrams/commercial_roadmap.drawio
    ↓
User: "Build portal"
    ↓
ea_build_portal()
    ↓
Converts .drawio → SVG, generates indexes
    ↓
Output: portal/ directory ready for deployment
```

**Model Discovery (MVP1-4) → Portal:**

```
ea_discover_directory("ea_inputs")
    ↓
Updates: archi_inputs/elements.csv, relations.csv, properties.csv
    ↓
ea_build_portal()
    ↓
Regenerates element_index.json with new data
```

### MCP Tool Workflow

**Local Development:**

```python
# Generate diagrams
ea_generate_diagram("ea_inputs/views/commercial_roadmap.yaml")
ea_generate_diagram("ea_inputs/views/commercial_landscape.yaml")

# Build portal
result = ea_build_portal()
# Returns: {"views_processed": 2, "elements_indexed": 25, ...}

# Preview locally
url = ea_preview_portal(port=8000)
# Returns: "http://localhost:8000"
# Opens browser to test navigation

# Deploy to ACA (manual for now)
# Docker build/push/deploy commands
```

---

## Success Criteria

MVP10 is complete when:

**Build Phase:**
- ✅ `ea_build_portal()` successfully converts all .drawio files to SVG
- ✅ Element IDs in SVG match ArchiMate element IDs in `elements.csv`
- ✅ JSON indexes generated correctly (view registry, element index, relationship graph)
- ✅ Frontend build completes (Vue app bundled to `dist/`)

**Frontend Functionality:**
- ✅ View list displays all available diagrams, grouped by category
- ✅ Click view → Diagram loads in center panel
- ✅ Click element in diagram → Detail panel shows properties
- ✅ Click "Appears in: X" → Navigate to target view with element highlighted
- ✅ Click relationship target → Navigate to view containing that element
- ✅ Multi-view picker works when element appears in multiple views

**Performance:**
- ✅ View navigation <1 second
- ✅ Element detail panel <500ms
- ✅ Diagram pan/zoom smooth at 60fps

**Deployment:**
- ✅ Docker image builds successfully
- ✅ Container runs locally
- ✅ Deployed to ACA and accessible via URL
- ✅ Health check endpoint returns 200

**Quality:**
- ✅ No console errors in browser
- ✅ Responsive layout (works on laptop screen)
- ✅ All elements in diagrams are clickable
- ✅ Element highlighting visually distinct

---

## Open Questions

### 1. Element ID Stability

**Status: VALIDATED ✅**

**Findings:** Drew.io files contain stable, properly-formatted element IDs that match `archi_inputs/elements.csv`.

**Evidence from `commercial_asis_crm_current.drawio`:**
```xml
<!-- In .drawio -->
<mxCell id="id-c508ffe79f87" value="Microsoft Dynamics" ... />

<!-- In elements.csv -->
id-c508ffe79f87,ApplicationComponent,Microsoft Dynamics,...
```

**ID Pattern Analysis:**

| Cell Type | ID Format | Example | Source |
|-----------|-----------|---------|--------|
| **Elements** | `id-XXXXXX` or `elem-id-XXXXXX` | `id-c508ffe79f87` | ArchiMate ID (injected by diagram generator) |
| **Containers** | `container-N` | `container-ANZ` | Logical grouping (region, domain, etc) |
| **Edges** | `edge-id-XXXXXX` | `edge-id-b4c3e014b06d` | Relationship ID (for future use) |
| **Annotations** | `ann-N` | `ann-1` | Labels, not clickable elements |
| **Narrative** | `narrative-N` | `narrative-285878` | Info box, skip in conversion |

**Mapping Strategy for SVG Converter:**
1. Extract all `mxCell` elements from .drawio XML
2. Filter by ID pattern:
   - `id-*` or `elem-id-*` → Extract as clickable element, preserve ID
   - `container-*` → Extract as container/swimlane, use `value` attribute for label
   - `edge-id-*` → Extract as relationship edge
   - `ann-*`, `narrative-*` → Skip or handle as decorative
3. When converting to SVG, embed `data-element-id` attribute matching the original `id`

**Impact on Portal Builder:**
- ✅ No name-based mapping needed
- ✅ Element index lookup is direct (ID → properties)
- ✅ Diagram generator already creates IDs correctly (MVP8 handles this)
- ✅ SVG converter just needs to preserve and embed these IDs

### 2. Frontend Build Tool

**Question:** Vite or webpack for Vue build?

**Recommendation:** Vite (faster, modern, officially recommended by Vue team)

### 3. SVG Interactivity Method

**Question:** Embed click handlers directly in SVG or use JS event delegation?

**Recommendation:** JS event delegation
- Keeps SVG clean (no inline onclick)
- Easier to update logic without regenerating SVGs
- Better performance with many elements

### 4. View Grouping Strategy

**Question:** How to organize view list sidebar?

**Options:**
- By domain (Commercial, Operations, IT Security)
- By epic (crm-consolidation/, jpn-refresh/)
- By type (Roadmaps, Landscapes, Integration Views)

**Recommendation:** Hybrid
- Top level: Epics (folders in `ea_inputs/views/`)
- Flat views go in "Ad-hoc" section
- User can collapse/expand groups

### 5. URL Routing

**Question:** Use hash-based (#/view/...) or history API (/view/...)?

**Recommendation:** Hash-based for simplicity
- Works without server-side routing configuration
- ACA serves everything from root, hash routing just works
- Can upgrade to history API later if needed

---

## Implementation Phases

### Phase 1: Build Pipeline (Days 1-2)
1. Create `src/ea/drawio_to_svg.py` - SVG converter
2. Create `src/ea/portal_indexes.py` - JSON generators
3. Create `src/ea/portal_builder.py` - Orchestrator
4. Add MCP tool `ea_build_portal()`
5. Test on existing diagrams, verify output

### Phase 2: Frontend App (Days 3-4)
1. Set up Vue 3 + Vite project in `portal/`
2. Create component structure (ViewList, DiagramViewer, ElementPanel)
3. Implement state management (Pinia stores)
4. Add SVG pan/zoom integration
5. Implement element click handling
6. Implement cross-view navigation
7. Test locally with sample data

### Phase 3: Backend & Deployment (Day 5)
1. Create `src/ea/portal_server.py` - FastAPI static server
2. Create Dockerfile
3. Add MCP tool `ea_preview_portal()`
4. Test local container run
5. Deploy to ACA
6. Verify health check and accessibility

### Phase 4: Integration & Testing (Day 6)
1. Generate multiple diagrams using MVP8
2. Build portal from those diagrams
3. Test all navigation flows
4. Fix any element ID mapping issues
5. Performance testing
6. Documentation updates

---

## Files to Create

**Backend:**
- `src/ea/portal_builder.py` (~200 lines)
- `src/ea/drawio_to_svg.py` (~150 lines)
- `src/ea/portal_indexes.py` (~250 lines)
- `src/ea/portal_server.py` (~50 lines)

**Frontend:**
- `portal/src/App.vue` (~100 lines)
- `portal/src/components/ViewList.vue` (~150 lines)
- `portal/src/components/DiagramViewer.vue` (~200 lines)
- `portal/src/components/ElementPanel.vue` (~250 lines)
- `portal/src/components/ViewPicker.vue` (~100 lines)
- `portal/src/stores/views.js` (~80 lines)
- `portal/src/stores/elements.js` (~100 lines)
- `portal/src/stores/navigation.js` (~80 lines)
- `portal/src/main.js` (~50 lines)
- `portal/vite.config.js` (~30 lines)
- `portal/package.json` (~40 lines)
- `portal/index.html` (~30 lines)

**Deployment:**
- `Dockerfile` (~20 lines)
- `portal/.dockerignore` (~10 lines)

**Documentation:**
- `docs/ea/MVP10_STATUS.md` (after completion)
- Update `CLAUDE.md` with portal workflow
- Update `README.md` with portal deployment instructions

**Total Estimated Lines:** ~1900 lines of new code

---

## Dependencies

**Python:**
- `fastapi` - Web server
- `uvicorn` - ASGI server
- `xml.etree.ElementTree` - XML parsing (stdlib)
- `cairosvg` or `selenium` - .drawio → SVG conversion (if needed)

**JavaScript:**
- `vue@3` - Frontend framework
- `pinia` - State management
- `vue-router` - Routing (optional, hash-based is simpler)
- `svg-pan-zoom` - Diagram interaction
- `vite` - Build tool

**Development:**
- `@vitejs/plugin-vue` - Vite Vue plugin
- `eslint` - Linting
- `prettier` - Formatting

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Element ID mismatch** | Navigation fails | Pre-check IDs, implement name-based fallback mapping |
| **SVG rendering issues** | Diagrams don't display | Test conversion on sample files first, validate SVG output |
| **Large diagrams slow** | Poor UX | Implement lazy loading, limit pan/zoom area |
| **ACA deployment complexity** | Delayed launch | Test Docker locally first, use simple FastAPI setup |
| **Build pipeline errors** | Portal can't be generated | Robust error handling, detailed logging, validation steps |

---

## Future Enhancements (MVP11+)

**MVP11: Search & Filtering**
- Full-text search across elements, properties, views
- Filter views by domain, lifecycle status, etc.
- Search results with context highlighting

**MVP12: Advanced Navigation**
- Relationship path finding ("How does CRM connect to ERP?")
- Impact analysis ("What uses this data object?")
- Dependency visualization
- Side-by-side view comparison

**MVP13: Collaboration Features**
- Comments on elements/views
- Change tracking (model diff viewer)
- Export to PowerPoint/PDF from browser
- Share links to specific elements

**MVP14: Authentication & Authorization**
- Azure AD integration
- Role-based view access (sensitive diagrams)
- Audit logging

---

## Related Documentation

- `docs/ea/MVP8_STATUS.md` - AI-driven diagram generation (input to portal)
- `docs/ea/MVP9_STATUS.md` - Collaborative workflow (how diagrams are created)
- `docs/ea/README.md` - Overall EA system architecture
- `CLAUDE.md` - Integration with Claude Code CLI workflow

---

**Next Step:** Validate element ID strategy by inspecting sample .drawio file, then proceed with implementation.
