# EA Portal

Interactive web portal for navigating enterprise architecture diagrams. Click elements to explore properties, relationships, and cross-diagram navigation.

## Quick Start

### Build

```bash
python portal/build.py
```

This converts all diagrams from `ea_diagrams/*.drawio` to SVG, generates JSON indexes from the ArchiMate model, folds in supported inventory JSON views, and outputs everything to `portal/dist/`.

Build output:
- `portal/dist/index.html` - Single-file Vue 3 app
- `portal/dist/diagrams/` - 8 converted SVG files
- `portal/dist/data/` - JSON indexes (view registry, element index, relationship graph)
- `portal/dist/projects/<project>/` - Generated project inventory iframe pages with embedded JSON data

### Preview Locally

First build the portal:
```bash
python portal/build.py
```

Then start the server:
```bash
python -m http.server 8080 -d portal/dist
```

Open browser: **http://localhost:8080**

You should see the full EA Portal UI with the purple sidebar, diagram viewer, and detail panel.

To review the PSS2 application inventory detail view directly:

```text
http://localhost:8080/projects/pss2/app-inventory/?inventory=app-inventory.dev.json&embed=diagram
```

### Deploy to Azure Container Apps

```bash
# Build container
docker build -t ea-portal:latest .

# Tag for ACR
docker tag ea-portal:latest yourregistry.azurecr.io/ea-portal:latest

# Push to ACR
docker push yourregistry.azurecr.io/ea-portal:latest

# Deploy to ACA
az containerapp create \
  --name ea-portal \
  --resource-group your-rg \
  --environment your-aca-env \
  --image yourregistry.azurecr.io/ea-portal:latest \
  --target-port 8000 \
  --ingress external \
  --cpu 0.5 --memory 1Gi
```

## Directory Structure

```
portal/
├── README.md              (This file)
├── build.py               (Single command to rebuild)
├── Dockerfile             (ACA deployment)
├── backend/
│   ├── __init__.py
│   ├── converter.py       (Draw.io → SVG converter)
│   ├── indexes.py         (JSON index generator)
│   └── builder.py         (Orchestrator)
├── assets/
│   ├── infra-portal.html          (Infrastructure inventory iframe template)
│   └── app-inventory-portal.html  (Application inventory iframe template)
└── dist/                  (Generated - .gitignore'd)
    ├── index.html
    ├── diagrams/          (SVG files with element IDs)
    ├── data/              (JSON indexes)
    └── projects/          (Generated project inventory pages)
```

## How It Works

### Build Phase (Local)

1. **Converter** reads `.drawio` files and extracts diagram structure
2. **Converter** builds SVG with `data-element-id` attributes on each element
3. **Index Generator** reads ArchiMate CSV model
4. **Builder** collects supported inventory JSON views:
   - `json_inventory` YAML specs embed infrastructure inventories using `portal/assets/infra-portal.html`
   - `app-inventory*.json` files generate two project-scoped application views:
     - Application Architecture draw.io/SVG overview
     - Application Inventory iframe detail view using `portal/assets/app-inventory-portal.html`
5. **Index Generator** creates 3 JSON files:
   - `view_registry.json` - Available views with metadata
   - `element_index.json` - All elements with properties and appearances
   - `relationship_graph.json` - Element connections (Serving, Flow, etc.)

Inventory iframe pages embed their JSON at build time, so they work in static hosting and do not depend on runtime `fetch()` of source files.

### Runtime Phase (Browser)

1. Vue 3 app loads data from JSON files
2. User clicks view in sidebar → Loads SVG diagram
3. For inventory-backed views, the portal opens the generated project page in an iframe via `iframe_src`
4. User clicks element in diagram → Shows detail panel with properties
5. User clicks relationship or "Appears in" → Navigates to another view

## Project Inventory Views

### Infrastructure Inventory

`type: json_inventory` YAML specs point at project `infra-inventory.<env>.json` files. During `python portal/build.py`, the builder:

- validates the inventory contract
- writes a generated project iframe page under `portal/dist/projects/<project>/`
- registers the view with `view_type: json_inventory`
- sets `iframe_src` to the generated project page

### Application Inventory

Project `app-inventory*.json` files under `ea_inputs/04_projects/<project>/` are handled automatically. During `python portal/build.py`, the builder:

- generates the existing application architecture overview draw.io/SVG
- writes an interactive application inventory iframe page under `portal/dist/projects/<project>/app-inventory/`
- embeds `window.APP_INVENTORY_DATA` into that page
- registers the project view with `view_type: app_inventory`

For PSS2, the generated registry entry is:

```text
view_id: project_pss2_app_inventory
name: PSS 2.0 - Application Inventory
project_key: pss2
iframe_src: projects/pss2/app-inventory/?inventory=app-inventory.dev.json&embed=diagram
```

The app inventory iframe intentionally starts at the detail drilldown, not another architecture overview. It provides:

- `Components` - app components and build/runtime output
- `Frontend Paths` - frontend pages and frontend service modules
- `API Surface` - side-by-side frontend outbound paths and backend function endpoints

Clicking a row opens a closeable details modal. The modal replaces the earlier always-visible details pane to keep the iframe short and avoid nested scrolling.

## Elements & Navigation

**Element Selection:**
- Click any blue/green/orange box in diagram
- Right panel slides in with details

**Cross-Diagram Movement:**
- Panel shows "Appears in:" list
- Click to navigate and keep element highlighted

**Relationship Navigation:**
- Panel shows "Serves" and "Served By" relationships
- Click to jump to related element

## Build Requirements

- Python 3.9+
- No external dependencies (XML, CSV parsing is stdlib)

## Redeploy After New Diagrams

1. Generate diagrams using `/create-diagram` skill or `ea_generate_diagram` tool
2. Run `python portal/build.py`
3. If on ACA, redeploy container or rebuild locally and copy `dist/` contents

## Future Enhancements

- **MVP11:** Full-text search across elements
- **MVP12:** Relationship path finding ("How does CRM connect to ERP?")
- **MVP13:** Comments, change tracking, side-by-side comparison
- **MVP14:** Azure AD authentication
