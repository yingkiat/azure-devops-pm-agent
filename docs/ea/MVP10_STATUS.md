# MVP10: Interactive EA Portal

**Status:** ✅ COMPLETE - All core functionality working, catalogue integration added

**Date:** 2026-01-23 (Updated from 2026-01-12)

---

## Summary

✅ **MVP10 is complete and ready for use.**

**What Works:**
- Interactive diagram viewer with clickable elements
- Application Catalogue view (Excel → searchable table → element details)
- Right sidebar with properties, relationships, and navigation
- "Appears In" cross-view navigation with element highlighting
- Responsive overlay sidebar (works at all viewport sizes)

**Build & Deploy:**
```bash
# Rebuild portal after changes
python portal/build.py

# Preview locally
cd portal/dist && python -m http.server 8080
```

**Key Files:**
- Template source: `portal/backend/builder.py` (lines 290-930)
- Generated output: `portal/dist/index.html` (never edit directly)
- Current build docs: See [AGENTS.md](../../AGENTS.md#portal-sources-and-build) and the [portal README](../../portal/README.md)

---

## Overview

MVP10 delivers an interactive web portal for navigating pre-generated enterprise architecture diagrams. Users can click elements to see properties, relationships, and navigate across multiple views while keeping elements highlighted.

**Architecture:**
- **Backend (Python):** `portal/backend/` - Converts .drawio → SVG, generates JSON indexes
- **Frontend (Vue 3):** Embedded in single `portal/dist/index.html` - No build step required
- **Deployment:** Containerized for Azure Container Apps

---

## Completed ✅

### 1. Backend Infrastructure

**Portal Builder** (`portal/backend/builder.py`)
- Orchestrates entire build process
- Loads ArchiMate model (both `elements.csv` + `diagram_elements.csv`)
- Converts all `.drawio` files to SVG with element IDs
- Generates JSON indexes for portal navigation
- Output: `portal/dist/` ready for deployment

**SVG Converter** (`portal/backend/converter.py`)
- Faithfully translates mxGraphModel cells to SVG
- Preserves exact pixel positioning, colors, fonts, styles
- Layered rendering: backgrounds → clickable elements → annotations
- Embeds `data-element-id` attributes on each element
- Handles containers, swimlanes, labels, annotations

**Index Generator** (`portal/backend/indexes.py`)
- **Element Index:** Maps element_id → properties + appearances across views
- **Relationship Graph:** Maps element_id → outbound/inbound connections
- **View Registry:** Maps view_id → diagram metadata
- **Deduplication:** Prevents duplicate "Appears In" entries (fixed)

**Build Command:**
```bash
python portal/build.py
```

### 2. Frontend Application

**Single-File Vue 3 SPA** (`portal/dist/index.html`)
- Purple gradient sidebar with view navigator
- Central SVG diagram viewer with pan/zoom
- Right detail panel (hidden until element selected)
- No build step, no dependencies beyond Vue CDN

**Core Features Working:**
- ✅ Load views from sidebar
- ✅ Click elements to show properties
- ✅ Display relationships (Serves / Served By)
- ✅ Navigate via "Appears In" links with element highlighting preserved
- ✅ Element properties refresh correctly
- ✅ No duplicate "Appears In" entries
- ✅ **Application Catalogue integration** - Load Excel catalogue, match to ArchiMate elements
- ✅ **Right sidebar overlay** - Fixed positioning for all viewport sizes

### 3. Application Catalogue Integration

**Catalogue Converter** (`portal/backend/builder.py`)
- Reads Excel file: `ea_inputs/02_IT_systems/Application Catalogue.xlsx`
- Converts to JSON: `portal/dist/data/catalogue.json`
- Preserves all columns and properties from Excel
- Handles null values and data types correctly

**Frontend Catalogue View:**
- **Searchable table** - Filter applications across all columns
- **Row click** - Matches catalogue NAME field → ArchiMate element by name
- **Smart sidebar** - Shows ArchiMate element details if matched, catalogue details if not
- **Flexible matching** - Case-insensitive, whitespace-tolerant matching
- **Priority-based column detection** - Finds "name", "application name", etc.

**User Flow:**
1. Click "Application Catalogue" in left sidebar
2. Browse/search applications in table
3. Click row → Right sidebar opens with element details
4. If element exists in ArchiMate model → Full properties, relationships, "Appears In"
5. If not in model → Catalogue data only

### 4. Data Loading

- Loads both core and diagram-specific element/property sets
- Merges `elements.csv` + `diagram_elements.csv`
- Merges `properties.csv` + `diagram_properties.csv`
- Loads `relations.csv` for relationship graph
- Loads `catalogue.json` for application inventory

---

## Resolved Issues ✅

### Issue #1: Sidebar Not Appearing (Fixed 2026-01-23) ⚠️ CRITICAL

**Symptom:**
- Right sidebar would only appear when DevTools was open
- Console logs showed correct state (`sidebarRightOpen=true`, `selectedElement` set)
- Sidebar would disappear when DevTools closed

**Root Cause:**
CSS positioning issue. The sidebar used `position: relative`, which kept it in the flex layout:
- Sidebar took up 350px of space even when hidden (`transform: translateX(100%)`)
- When viewport width was insufficient (sidebar-left: 280px + main + sidebar-right: 350px), the sidebar got pushed off-screen
- DevTools narrowed the viewport, forcing layout to fit, making sidebar visible

**Fix:**
Changed `.sidebar-right` from `position: relative` to `position: fixed`:
```css
.sidebar-right {
    position: fixed;    /* Changed from relative */
    top: 0;
    right: 0;
    height: 100vh;
    z-index: 50;        /* Overlays content */
    /* ... */
}
```

**Impact:** Sidebar now consistently overlays content at all viewport sizes.

### Issue #2: Editing Generated HTML Directly ⚠️ PROCESS ISSUE

**Symptom:**
- Edits to `portal/dist/index.html` were lost/reverted
- Browser showed old code despite file changes
- Wasted debugging time

**Root Cause:**
Portal HTML is **generated by a build process** from a template in `portal/backend/builder.py` (lines 290-930). Editing the dist file directly:
1. Gets overwritten on next build
2. May be cached by browser
3. Is not the source of truth

**Fix:**
- Documented in `CLAUDE.md` under "Portal HTML is Generated, NOT Editable"
- Always edit the template in `portal/backend/builder.py`
- Run `python portal/build.py` to regenerate
- Hard refresh browser (Ctrl+Shift+R) after rebuild

**Lesson Learned:**
Check for build processes before editing output files. Look for:
- `build.py` scripts
- Template strings in Python code
- `dist/` or `output/` directories (usually generated)

---

## Testing Status

### Functionality Tests

| Feature | Status | Notes |
|---------|--------|-------|
| Load views from sidebar | ✅ | Works |
| Click element to show properties | ✅ | Works for all diagrams |
| Display element properties | ✅ | Refreshes correctly |
| Show relationships (Serves/Served By) | ✅ | Works |
| Navigate to related elements | ✅ | Click rel items navigates correctly |
| Appears In list | ✅ | No duplicates, navigation works |
| Element highlighting on navigation | ✅ | Works when element found in view |
| Right sidebar overlay | ✅ | Fixed - uses position:fixed |
| Application Catalogue view | ✅ | Loads Excel, searchable table |
| Catalogue row click | ✅ | Matches to ArchiMate elements |
| Catalogue → Element details | ✅ | Shows full properties + relationships |
| Search across catalogue | ✅ | Filters all columns |

### Working Diagrams ✅
- All diagrams in `ea_diagrams/` directory
- Catalogue table with all applications from Excel
- Sidebar overlay works at all viewport sizes

---

## Files Changed

**Backend:**
- `portal/backend/converter.py` - SVG conversion with layering
- `portal/backend/indexes.py` - Deduplication + dual element/property loading
- `portal/backend/builder.py` - HTML template with Vue 3 app

**Frontend:**
- `portal/dist/index.html` - Generated, contains full Vue app
- `portal/dist/diagrams/*.svg` - Generated from .drawio files
- `portal/dist/data/*.json` - Generated indexes

**Build:**
- `portal/build.py` - Main entry point (run this to rebuild)
- `portal/README.md` - Build and deployment instructions

---

## Architecture

```
Build Phase (Local)
├── SVG Converter
│   ├── Parse .drawio XML
│   ├── Translate mxGraphModel to SVG 1:1
│   └── Embed data-element-id on clickable elements
├── Index Generator
│   ├── Load ArchiMate model (core + diagram)
│   ├── Map element appearances in views
│   └── Generate relationship graph
└── Output: portal/dist/

Runtime Phase (Browser)
├── Load JSON indexes
├── User clicks view → Load SVG
├── Attach click handlers to [data-element-id] elements
├── User clicks element → Show properties panel
└── User clicks "Appears In" → Navigate to view, keep element highlighted
```

---

## Deployment

**Local Preview:**
```bash
cd portal/dist
python -m http.server 8080
# Open http://localhost:8080
```

**Azure Container Apps:**
```bash
docker build -t ea-portal:latest .
docker tag ea-portal:latest yourregistry.azurecr.io/ea-portal:latest
docker push yourregistry.azurecr.io/ea-portal:latest
az containerapp create --name ea-portal --image yourregistry.azurecr.io/ea-portal:latest
```

---

## Future Enhancements (Post-MVP10)

### Enhancement Ideas

1. **Catalogue Editing:**
   - Inline editing of catalogue properties
   - Save back to Excel or database
   - Change tracking and audit log

2. **Advanced Filtering:**
   - Multi-column filters in catalogue
   - Filter by Domain, Region, Lifecycle Status
   - Saved filter presets

3. **Diagram Annotations:**
   - Add sticky notes to diagrams
   - Collaborative comments
   - Version comparison views

4. **Export Capabilities:**
   - Export filtered catalogue to Excel/CSV
   - Export diagram as PNG/PDF
   - Generate reports from selected elements

5. **Performance Optimization:**
   - Lazy load diagrams on scroll
   - Virtual scrolling for large catalogues
   - SVG caching and compression

6. **Mobile Responsiveness:**
   - Touch-friendly element selection
   - Responsive table columns
   - Mobile-optimized sidebar

---

## Session Notes

**Session 1 (2026-01-12):**
- Built complete backend infrastructure
- Created Vue 3 frontend with proper state management
- Fixed duplicate "Appears In" entries
- Fixed panel refresh on "Appears In" navigation
- All core functionality working

**Session 2 (2026-01-23):**
- **Added Application Catalogue integration:**
  - Excel → JSON conversion in build process
  - Catalogue view with searchable table
  - Name-based matching to ArchiMate elements
  - Smart sidebar showing element or catalogue details

- **Fixed critical CSS positioning bug:**
  - Root cause: `position: relative` sidebar pushed off-screen on narrow viewports
  - Solution: Changed to `position: fixed` for consistent overlay behavior
  - Debugging loop: Edited dist/index.html directly instead of template source

- **Documented build process in CLAUDE.md:**
  - Portal HTML is generated from template in `builder.py`
  - Must rebuild after template changes
  - Never edit `dist/index.html` directly

**Lessons Learned:**
1. **Check for build processes** before editing output files
2. **CSS positioning** matters - relative vs. fixed has major layout implications
3. **Template-based generation** - always find the source template, not the output
4. **Hard refresh browsers** after builds to clear cache (Ctrl+Shift+R)

---

**Version:** 1.0-complete

**Completion Estimate:** 100% complete - All features working, catalogue integration added
