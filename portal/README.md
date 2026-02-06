# EA Portal

Interactive web portal for navigating enterprise architecture diagrams. Click elements to explore properties, relationships, and cross-diagram navigation.

## Quick Start

### Build

```bash
python portal/build.py
```

This converts all diagrams from `ea_diagrams/*.drawio` to SVG, generates JSON indexes from the ArchiMate model, and outputs everything to `portal/dist/`.

Build output:
- `portal/dist/index.html` - Single-file Vue 3 app
- `portal/dist/diagrams/` - 8 converted SVG files
- `portal/dist/data/` - JSON indexes (view registry, element index, relationship graph)

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
└── dist/                  (Generated - .gitignore'd)
    ├── index.html
    ├── diagrams/          (SVG files with element IDs)
    └── data/              (JSON indexes)
```

## How It Works

### Build Phase (Local)

1. **Converter** reads `.drawio` files and extracts diagram structure
2. **Converter** builds SVG with `data-element-id` attributes on each element
3. **Index Generator** reads ArchiMate CSV model
4. **Index Generator** creates 3 JSON files:
   - `view_registry.json` - Available views with metadata
   - `element_index.json` - All elements with properties and appearances
   - `relationship_graph.json` - Element connections (Serving, Flow, etc.)

### Runtime Phase (Browser)

1. Vue 3 app loads data from JSON files
2. User clicks view in sidebar → Loads SVG diagram
3. User clicks element in diagram → Shows detail panel with properties
4. User clicks relationship or "Appears in" → Navigates to another view

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
