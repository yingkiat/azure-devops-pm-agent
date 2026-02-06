"""Build interactive EA portal from diagrams and model data."""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from .converter import DrawioToSvg
from .indexes import PortalIndexGenerator


class PortalBuilder:
    """Build static portal files from diagrams and ArchiMate model."""

    def __init__(
        self,
        diagrams_dir: str = "ea_diagrams",
        model_dir: str = "archi_inputs",
        specs_dir: str = "ea_inputs/views",
        output_dir: str = "portal/dist",
        branding_dir: str = "portal/assets/branding",
        catalogue_file: str = "ea_inputs/02_IT_systems/Application Catalogue.xlsx",
    ):
        self.diagrams_dir = Path(diagrams_dir)
        self.model_dir = Path(model_dir)
        self.specs_dir = Path(specs_dir)
        self.output_dir = Path(output_dir)
        self.branding_dir = Path(branding_dir)
        self.catalogue_file = Path(catalogue_file)
        self.data_dir = self.output_dir / "data"
        self.diagrams_output_dir = self.output_dir / "diagrams"

    def build(self) -> Dict:
        """
        Build complete portal.

        Returns:
            {
                "success": bool,
                "diagrams_processed": int,
                "elements_indexed": int,
                "output_path": str,
                "errors": [str]
            }
        """
        errors = []

        print("\n[Portal Builder] Starting...\n")

        # Step 1: Load ArchiMate model
        print("[1/4] Loading ArchiMate model...")
        index_gen = PortalIndexGenerator()
        if not index_gen.load_archi_model(str(self.model_dir)):
            errors.append("Failed to load ArchiMate model")
            return {
                "success": False,
                "errors": errors,
                "output_path": str(self.output_dir),
            }

        print(f"      ✓ Loaded {len(index_gen.elements)} elements\n")

        # Step 2: Convert application catalogue (optional)
        print("[2/5] Converting application catalogue...")
        catalogue_count = self._convert_catalogue()
        if catalogue_count > 0:
            print(f"      ✓ Converted {catalogue_count} applications from catalogue\n")
        else:
            print(f"      ⚠ No catalogue file found (optional)\n")

        # Step 3: Convert diagrams to SVG
        print("[3/5] Converting diagrams to SVG...")
        diagrams_info = self._convert_diagrams_to_svg()
        print(f"      ✓ Converted {len(diagrams_info)} diagrams\n")

        # Step 4: Generate indexes
        print("[4/5] Generating indexes...")
        element_index = index_gen.generate_element_index(
            {
                "views": [
                    {
                        "view_id": d["view_id"],
                        "name": d["name"],
                        "elements": d["elements"],
                    }
                    for d in diagrams_info
                ]
            }
        )
        relationship_graph = index_gen.generate_relationship_graph(element_index)
        view_registry = index_gen.generate_view_registry(diagrams_info)

        print(f"      ✓ Indexed {len(element_index)} elements")
        print(f"      ✓ Mapped {sum(len(v['outbound']) + len(v['inbound']) for v in relationship_graph.values())} relationships")
        print(f"      ✓ Registered {len(view_registry)} views\n")

        # Step 5: Save indexes
        print("[5/5] Saving files...")
        if not index_gen.save_indexes(
            str(self.data_dir), element_index, relationship_graph, view_registry
        ):
            errors.append("Failed to save indexes")

        # Copy frontend files
        self._copy_frontend_files()

        print(f"\n[Portal Builder] Complete! ✓")
        print(f"  📁 Output: {self.output_dir.absolute()}")
        print(f"  🌐 Open: file://{self.output_dir.absolute() / 'index.html'}\n")

        return {
            "success": len(errors) == 0,
            "diagrams_processed": len(diagrams_info),
            "elements_indexed": len(element_index),
            "views_registered": len(view_registry),
            "catalogue_apps": catalogue_count,
            "output_path": str(self.output_dir),
            "errors": errors,
        }

    def _convert_diagrams_to_svg(self) -> List[Dict]:
        """Convert all .drawio files to SVG, preserving folder structure."""
        diagrams_info = []
        self.diagrams_output_dir.mkdir(parents=True, exist_ok=True)
        converter = DrawioToSvg()

        # Recursively find all .drawio files
        for drawio_file in sorted(self.diagrams_dir.glob("**/*.drawio")):
            # Get relative path from diagrams_dir to preserve folder structure
            try:
                relative_path = drawio_file.relative_to(self.diagrams_dir)
            except ValueError:
                relative_path = Path(drawio_file.name)

            # Extract category from parent folder (empty if at root)
            category = relative_path.parent.as_posix() if relative_path.parent != Path(".") else ""

            # Use full relative path (without extension) as view_id for uniqueness
            view_id = relative_path.with_suffix("").as_posix().replace("/", "_")

            # Preserve folder structure in output
            svg_output = self.diagrams_output_dir / relative_path.with_suffix(".svg")
            svg_output.parent.mkdir(parents=True, exist_ok=True)

            result = converter.convert(str(drawio_file), str(svg_output))

            if result["success"]:
                element_ids = [e["id"] for e in result.get("elements", [])]

                # Use original filename for display name
                display_name = drawio_file.stem.replace("_", " ").title()

                diagrams_info.append(
                    {
                        "view_id": view_id,
                        "name": display_name,
                        "diagram_file": f"diagrams/{relative_path.with_suffix('.svg').as_posix()}",
                        "category": category,
                        "elements": element_ids,
                        "element_count": len(element_ids),
                        "created": datetime.now().isoformat(),
                    }
                )
                print(f"      ✓ {view_id:45s} ({len(element_ids):2d} elements)")
            else:
                print(f"      ✗ {view_id:45s} {result.get('error', 'Unknown error')}")

        return diagrams_info

    def _convert_catalogue(self) -> int:
        """
        Convert Excel application catalogue to JSON.

        Returns:
            Number of applications converted (0 if catalogue not found or pandas not available)
        """
        if not PANDAS_AVAILABLE:
            print(f"      ⚠ pandas not installed, skipping catalogue conversion")
            return 0

        if not self.catalogue_file.exists():
            print(f"      ⚠ Catalogue file not found: {self.catalogue_file}")
            return 0

        try:
            # Read Excel file with groupings (row 0) and column names (row 1)
            df_all = pd.read_excel(str(self.catalogue_file), header=None)

            # Extract groupings from row 0 and column names from row 1
            groupings = {}
            if len(df_all) > 0:
                # Forward-fill NaN values in grouping row (row 0) to handle merged cells
                grouping_row = df_all.iloc[0].copy()
                grouping_row = grouping_row.fillna(method='ffill')

                for col_idx, col_name in enumerate(df_all.iloc[1]):
                    if pd.notna(col_name):
                        col_name_str = str(col_name)
                        grouping_value = grouping_row.iloc[col_idx] if col_idx < len(grouping_row) else None
                        groupings[col_name_str] = str(grouping_value) if pd.notna(grouping_value) else None

            # Read data with row 1 as headers (skip row 0)
            df = pd.read_excel(str(self.catalogue_file), header=1)

            # Convert to records and clean NaN values
            catalogue = []
            for record in df.to_dict('records'):
                # Replace NaN with None, convert to proper types
                cleaned_record = {}
                for key, value in record.items():
                    if pd.isna(value):
                        cleaned_record[key] = None
                    elif isinstance(value, (pd.Timestamp, datetime)):
                        cleaned_record[key] = value.isoformat()
                    else:
                        cleaned_record[key] = value
                catalogue.append(cleaned_record)

            # Save to JSON with metadata
            self.data_dir.mkdir(parents=True, exist_ok=True)
            catalogue_json = self.data_dir / "catalogue.json"

            output_data = {
                "metadata": {
                    "groupings": groupings,
                    "columns": list(df.columns)
                },
                "data": catalogue
            }

            with open(catalogue_json, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            return len(catalogue)

        except Exception as e:
            print(f"      ✗ Error converting catalogue: {e}")
            return 0

    def _copy_frontend_files(self) -> None:
        """Create frontend app files."""
        # Create frontend directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Copy branding assets to dist
        branding_dist = self.output_dir / "assets" / "branding"
        branding_dist.mkdir(parents=True, exist_ok=True)

        logo_file = self.branding_dir / "logo.jpg"
        if logo_file.exists():
            import shutil
            shutil.copy2(str(logo_file), str(branding_dist / "logo.jpg"))

        # Load branding
        colors = self._load_branding_colors()
        logo_url = self._get_logo_url()

        # Create index.html with Vue 3 app
        html_content = self._get_html_template(colors, logo_url)
        (self.output_dir / "index.html").write_text(html_content, encoding="utf-8")
        print(f"      ✓ Created index.html with branding")

    def _load_branding_colors(self) -> Dict:
        """Load color scheme from branding/colors.json."""
        colors_file = self.branding_dir / "colors.json"
        if colors_file.exists():
            try:
                return json.loads(colors_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                print(f"      ⚠ Failed to load colors.json, using defaults")
                return self._get_default_colors()
        return self._get_default_colors()

    def _get_logo_url(self) -> str:
        """Get logo URL if it exists."""
        logo_file = self.branding_dir / "logo.jpg"
        if logo_file.exists():
            return "./assets/branding/logo.jpg"

        return None

    @staticmethod
    def _get_default_colors() -> Dict:
        """Return default color palette."""
        return {
            "primary": "#0052CC",
            "primary_light": "#1E5FD9",
            "primary_dark": "#003D99",
            "secondary": "#00A651",
            "sidebar_gradient_start": "#0052CC",
            "sidebar_gradient_end": "#003D99",
            "accent": "#F39200",
        }

    def _get_html_template(self, colors: Dict, logo_url: str = None) -> str:
        """Get HTML template with Vue 3 embedded and branding injected."""
        # Prepare logo HTML
        logo_html = ""
        if logo_url:
            logo_html = '<img src="{}" style="width: 48px; height: 48px; flex-shrink: 0; object-fit: contain; border-radius: 4px;">'.format(logo_url)

        # Build CSS with colors
        gradient_start = colors.get("sidebar_gradient_start", "#667eea")
        gradient_end = colors.get("sidebar_gradient_end", "#764ba2")
        primary = colors.get("primary", "#667eea")
        primary_dark = colors.get("primary_dark", "#764ba2")
        accent = colors.get("accent", "#ffc107")

        template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EA Portal</title>
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body { height: 100%; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif; background: #f5f7fa; }

        #app { display: flex; height: 100vh; background: #fff; }

        .sidebar-left {
            width: 17.5rem;
            min-width: 17.5rem;
            max-width: 17.5rem;
            flex-shrink: 0;
            position: relative;
            background: linear-gradient(135deg, __GRADIENT_START__ 0%, __GRADIENT_END__ 100%);
            color: white;
            border-right: 1px solid #ddd;
            overflow-y: auto;
            box-shadow: 2px 0 8px rgba(0,0,0,0.1);
        }

        .sidebar-header {
            padding: 1rem 1.5rem;
            border-bottom: 1px solid rgba(255,255,255,0.2);
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        .sidebar-header-content {
            flex: 1;
            padding-left: 0.5rem;
        }
        .sidebar-header h1 { font-size: 1.1rem; font-weight: 700; margin: 0; }
        .sidebar-header p { font-size: 0.75rem; opacity: 0.85; margin-top: 0.25rem; }

        .view-list { padding: 1rem; }
        .view-category { margin-bottom: 2rem; }
        .view-category-title { font-size: 0.75rem; font-weight: 700; text-transform: uppercase; opacity: 0.7; padding: 0.75rem 1rem; margin-bottom: 0.5rem; letter-spacing: 0.5px; }
        .view-item {
            padding: 0.875rem 1rem;
            margin-bottom: 0.5rem;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
            border-left: 3px solid transparent;
        }
        .view-item:hover { background: rgba(255,255,255,0.1); border-left-color: __ACCENT__; }
        .view-item.active { background: rgba(255,255,255,0.2); border-left-color: __ACCENT__; }
        .view-item-name { font-weight: 500; font-size: 0.95rem; }
        .view-item-count { font-size: 0.75rem; opacity: 0.8; margin-top: 0.25rem; }

        .main { flex: 1; display: flex; flex-direction: column; }

        .header {
            padding: 1.5rem 2rem;
            border-bottom: 1px solid #e0e0e0;
            background: #fff;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .header h2 { margin: 0; font-size: 1.5rem; color: #333; }

        .diagram-viewer {
            flex: 1;
            background: #f9fafc;
            overflow: auto;
            padding: 1rem;
            position: relative;
        }
        .diagram-viewer svg {
            background: white;
            border-radius: 8px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.1);
            display: block;
            transform-origin: top left;
            transition: transform 0.2s ease;
        }
        .zoom-controls {
            position: absolute;
            bottom: 2rem;
            right: 2rem;
            display: flex;
            gap: 0.5rem;
            z-index: 100;
            background: white;
            padding: 0.5rem;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        .zoom-btn {
            width: 36px;
            height: 36px;
            border: 1px solid #ddd;
            background: white;
            border-radius: 6px;
            cursor: pointer;
            font-size: 1.2rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
            color: __PRIMARY__;
        }
        .zoom-btn:hover {
            background: __PRIMARY__;
            color: white;
            border-color: __PRIMARY__;
        }
        .zoom-btn:disabled {
            opacity: 0.3;
            cursor: not-allowed;
        }
        .zoom-btn:disabled:hover {
            background: white;
            color: __PRIMARY__;
            border-color: #ddd;
        }
        .fit-toggle {
            padding: 0 0.75rem;
            width: auto;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }
        /* Ensure zoom works properly */
        html {
            -webkit-text-size-adjust: 100%;
            font-size: 16px;
        }
        @media (min-width: 1920px) {
            html { font-size: 18px; }
        }

        .catalogue-viewer {
            flex: 1;
            background: #f9fafc;
            overflow: auto;
            padding: 1.5rem;
        }
        .catalogue-search {
            margin-bottom: 1rem;
            padding: 0.75rem;
            background: white;
            border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .catalogue-search input {
            width: 100%;
            padding: 0.5rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 0.8rem;
            font-family: inherit;
        }
        .catalogue-table-wrapper {
            background: white;
            border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            overflow-x: auto;
            overflow-y: visible;
        }
        .catalogue-table {
            width: max-content;
            min-width: 100%;
        }
        .catalogue-table table {
            width: 100%;
            border-collapse: collapse;
        }
        .catalogue-table th {
            color: white;
            padding: 0.5rem 0.75rem;
            text-align: left;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            white-space: normal;
            position: sticky;
            z-index: 10;
            overflow: visible;
        }
        .catalogue-table thead tr:first-child th {
            background: linear-gradient(135deg, __GRADIENT_START__40 0%, __GRADIENT_END__40 100%);
            padding: 0.5rem 0.75rem;
            font-size: 0.7rem;
            font-weight: 600;
            border-bottom: 1px solid rgba(255,255,255,0.5);
            top: 0;
            z-index: 11;
        }
        .catalogue-table thead tr:last-child th {
            background: linear-gradient(135deg, __GRADIENT_START__ 0%, __GRADIENT_END__ 100%);
            padding: 0.5rem 0.75rem;
            top: 2.2rem;
            z-index: 10;
            font-size: 0.75rem;
        }
        .catalogue-table .name-column {
            min-width: 200px;
            width: 200px;
            font-weight: 700;
        }
        .catalogue-table td.name-column {
            color: __PRIMARY__;
            font-weight: 700;
        }
        .catalogue-table td {
            padding: 0.4rem 0.75rem;
            border-bottom: 1px solid #e0e0e0;
            font-size: 0.75rem;
            white-space: nowrap;
        }
        .catalogue-table tbody tr {
            cursor: pointer;
            transition: background 0.2s;
        }
        .catalogue-table tbody tr:hover {
            background: #f5f7fa;
        }
        .catalogue-table tbody tr:last-child td {
            border-bottom: none;
        }

        .sidebar-right {
            width: 21.875rem;
            background: #fff;
            border-left: 1px solid #e0e0e0;
            overflow-y: auto;
            transform: translateX(100%);
            transition: transform 0.3s ease;
            box-shadow: -2px 0 8px rgba(0,0,0,0.1);
            position: fixed;
            top: 0;
            right: 0;
            height: 100vh;
            z-index: 50;
        }
        .sidebar-right.open { transform: translateX(0); }

        .sidebar-close {
            position: absolute;
            top: 1rem;
            right: 1rem;
            background: #f0f0f0;
            border: none;
            width: 32px;
            height: 32px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 1.2rem;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.2s;
        }
        .sidebar-close:hover { background: #e0e0e0; }

        .element-panel {
            padding: 2rem;
        }

        .element-header {
            display: flex;
            align-items: center;
            margin-bottom: 2rem;
            padding-bottom: 1.5rem;
            border-bottom: 2px solid __PRIMARY__;
        }
        .element-icon {
            width: 48px;
            height: 48px;
            border-radius: 8px;
            background: linear-gradient(135deg, __GRADIENT_START__ 0%, __GRADIENT_END__ 100%);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            margin-right: 1rem;
            font-size: 1.2rem;
        }}
        .element-name { flex: 1; }
        .element-name h2 { margin: 0; font-size: 1.25rem; color: #333; }
        .element-type { font-size: 0.85rem; color: #999; margin-top: 0.25rem; }

        .section { margin-bottom: 2rem; }
        .section-title { font-weight: 600; font-size: 0.9rem; color: __PRIMARY__; text-transform: uppercase; margin-bottom: 1rem; letter-spacing: 0.5px; }

        .properties-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
        .properties-table td { padding: 0.5rem 0.75rem; border-bottom: 1px solid #e0e0e0; }
        .properties-table td:first-child { font-weight: 600; color: __PRIMARY__; width: 40%; }
        .properties-table td:last-child { color: #333; }
        .properties-table tr:last-child td { border-bottom: none; }

        .relationships { }
        .rel-group { margin-bottom: 1.5rem; }
        .rel-group-title { font-size: 0.85rem; font-weight: 600; color: #666; margin-bottom: 0.75rem; }
        .rel-item {
            padding: 0.75rem;
            background: #f0f0f0;
            margin-bottom: 0.5rem;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
            border-left: 3px solid transparent;
            font-size: 0.95rem;
        }
        .rel-item:hover { background: #e0e0e0; border-left-color: __PRIMARY__; }

        .appears-in { }
        .appears-in-list { }
        .appears-in-item {
            padding: 0.75rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, __GRADIENT_START__15 0%, __GRADIENT_END__15 100%);
            border-left: 3px solid __PRIMARY__;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 0.95rem;
            color: #333;
        }
        .appears-in-item:hover { background: linear-gradient(135deg, __GRADIENT_START__25 0%, __GRADIENT_END__25 100%); }

        .element-highlighted rect { stroke: #ffc107 !important; stroke-width: 3 !important; }

        .empty-state {
            text-align: center;
            padding: 3rem 2rem;
            color: #999;
        }

        @media (max-width: 1024px) {
            .sidebar-right { width: 100%; z-index: 100; }
        }
    </style>
</head>
<body>
    <div id="app">
        <div class="sidebar-left">
            <div class="sidebar-header">
                __LOGO_HTML__
                <div class="sidebar-header-content">
                    <h1>EA Portal</h1>
                    <p>{{ totalApps }} Apps • {{ totalViews }} Views</p>
                </div>
            </div>
            <div class="view-list">
                <!-- Catalogue as first category -->
                <div class="view-category" v-if="totalApps > 0">
                    <div class="view-category-title">Catalogue</div>
                    <div class="view-item" :class="{ active: viewMode === 'catalogue' }" @click="showCatalogue()">
                        <div class="view-item-name">Application Catalogue</div>
                        <div class="view-item-count">{{ totalApps }} applications</div>
                    </div>
                </div>

                <!-- Diagram categories -->
                <template v-for="(views, category) in viewsByCategory" :key="category">
                    <div class="view-category" v-if="views.length > 0">
                        <div class="view-category-title">{{ category.charAt(0).toUpperCase() + category.slice(1) }}</div>
                        <div v-for="view in views" :key="view.id" class="view-item" :class="{ active: currentView === view.id }" @click="loadView(view.id)">
                            <div class="view-item-name">{{ view.name }}</div>
                            <div class="view-item-count">{{ view.metadata.element_count }} elements</div>
                        </div>
                    </div>
                </template>

                <!-- Empty state -->
                <div v-if="totalApps === 0 && Object.keys(viewsByCategory).length === 0" style="padding: 1rem; opacity: 0.7;">
                    Loading...
                </div>
            </div>
        </div>

        <div class="main">
            <div class="header" v-if="viewMode === 'catalogue'">
                <h2>Application Catalogue</h2>
            </div>
            <div class="header" v-else-if="currentView && views[currentView]">
                <h2>{{ views[currentView].name }}</h2>
            </div>

            <div v-if="viewMode === 'catalogue'" class="catalogue-viewer">
                <div class="catalogue-search">
                    <input type="text" v-model="catalogueSearch" placeholder="Search applications...">
                </div>
                <div class="catalogue-table-wrapper" v-if="filteredCatalogue.length > 0">
                    <div class="catalogue-table">
                        <table>
                            <thead>
                                <tr v-if="getGroupedHeaders().length > 0">
                                    <th v-for="group in getGroupedHeaders()" :key="`group-${group.grouping}`"
                                        :colspan="group.colspan"
                                        :style="{ backgroundColor: getGroupingColor(group.grouping) }">
                                        {{ group.grouping || '' }}
                                    </th>
                                </tr>
                                <tr>
                                    <th v-for="col in catalogueColumns" :key="col"
                                        :class="{ 'name-column': col === catalogueNameColumn }"
                                        :style="{ minWidth: col === catalogueNameColumn ? '200px' : 'auto' }">
                                        {{ col }}
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="(app, index) in filteredCatalogue" :key="`${app.domain}-${app.name}-${index}`" @click="selectCatalogueApp(app)">
                                    <td v-for="col in catalogueColumns" :key="col"
                                        :class="{ 'name-column': col === catalogueNameColumn }">
                                        {{ app[col] || '-' }}
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
                <div v-else class="empty-state">
                    <p>No applications in catalogue</p>
                </div>
            </div>
            <div v-else class="diagram-viewer" @click="deselectElement()">
                <div v-html="diagramHtml"></div>
                <div class="zoom-controls" v-if="currentView">
                    <button class="zoom-btn" @click="zoomOut" :disabled="zoomLevel <= 0.25" title="Zoom Out">−</button>
                    <button class="zoom-btn" @click="zoomReset" title="Reset Zoom">⊙</button>
                    <button class="zoom-btn" @click="zoomIn" :disabled="zoomLevel >= 3" title="Zoom In">+</button>
                    <button class="zoom-btn fit-toggle" @click="toggleFitToWidth" :title="fitToWidth ? 'Actual Size' : 'Fit to Width'">
                        {{ fitToWidth ? '⇲' : '⇱' }}
                    </button>
                </div>
            </div>
        </div>

        <div class="sidebar-right" :class="{ open: sidebarRightOpen }">
            <button class="sidebar-close" @click="closeSidebar()">×</button>

            <!-- Show catalogue app details if no matching ArchiMate element -->
            <div v-if="!selectedElement && selectedCatalogueApp" class="element-panel">
                <div class="element-header">
                    <div class="element-icon">📦</div>
                    <div class="element-name">
                        <h2>{{ selectedCatalogueApp[catalogueNameColumn] }}</h2>
                        <div class="element-type">Application</div>
                    </div>
                </div>

                <div class="section">
                    <div class="section-title">Catalogue Details</div>
                    <table class="properties-table">
                        <tr v-for="(value, key) in selectedCatalogueApp" :key="key">
                            <td>{{ key }}</td>
                            <td>{{ value || '-' }}</td>
                        </tr>
                    </table>
                </div>
            </div>

            <!-- Show ArchiMate element details if matched -->
            <div v-else-if="selectedElement && elements[selectedElement]" class="element-panel">
                <div class="element-header">
                    <div class="element-icon">{{ getElementTypeIcon(elements[selectedElement].type) }}</div>
                    <div class="element-name">
                        <h2>{{ elements[selectedElement].name }}</h2>
                        <div class="element-type">{{ elements[selectedElement].type }}</div>
                    </div>
                </div>

                <div v-if="Object.keys(elements[selectedElement].properties).length > 0" class="section">
                    <div class="section-title">Properties</div>
                    <table class="properties-table">
                        <tr v-for="(value, key) in elements[selectedElement].properties" :key="key">
                            <td>{{ key }}</td>
                            <td>{{ value }}</td>
                        </tr>
                    </table>
                </div>

                <div v-if="(relationships[selectedElement] && relationships[selectedElement].outbound && relationships[selectedElement].outbound.length > 0) || (relationships[selectedElement] && relationships[selectedElement].inbound && relationships[selectedElement].inbound.length > 0)" class="section">
                    <div class="section-title">Relationships</div>
                    <div v-if="relationships[selectedElement] && relationships[selectedElement].outbound && relationships[selectedElement].outbound.length > 0" class="rel-group">
                        <div class="rel-group-title">Serves</div>
                        <div v-for="rel in relationships[selectedElement].outbound" :key="rel.target_id" class="rel-item" @click="selectElement(rel.target_id)">
                            {{ rel.target_name }}
                        </div>
                    </div>

                    <div v-if="relationships[selectedElement] && relationships[selectedElement].inbound && relationships[selectedElement].inbound.length > 0" class="rel-group">
                        <div class="rel-group-title">Served By</div>
                        <div v-for="rel in relationships[selectedElement].inbound" :key="rel.source_id" class="rel-item" @click="selectElement(rel.source_id)">
                            {{ rel.source_name }}
                        </div>
                    </div>
                </div>

                <div v-if="elements[selectedElement] && elements[selectedElement].appears_in && elements[selectedElement].appears_in.length > 0" class="section">
                    <div class="section-title">Appears In</div>
                    <div class="appears-in-list">
                        <div v-for="(view, idx) in elements[selectedElement].appears_in" :key="`${selectedElement}-${view.view_id}-${idx}`" class="appears-in-item" @click="navigateToView(view.view_id, selectedElement)">
                            {{ view.view_name }}
                        </div>
                    </div>
                </div>
            </div>
            <div v-else class="empty-state">
                <p>Click an element to see details</p>
            </div>
        </div>
    </div>

    <script>
        const { createApp } = Vue;

        createApp({
            data() {
                return {
                    views: {},
                    elements: {},
                    relationships: {},
                    catalogue: [],
                    catalogueMetadata: { groupings: {}, columns: [] },
                    catalogueSearch: '',
                    currentView: null,
                    selectedElement: null,
                    selectedCatalogueApp: null,
                    diagramHtml: '',
                    currentSvg: null,
                    viewMode: 'catalogue',
                    sidebarRightOpen: false,
                    zoomLevel: 1,
                    fitToWidth: true
                };
            },
            computed: {
                totalApps() { return this.catalogue.length; },
                totalViews() { return Object.keys(this.views).length; },
                totalElements() { return Object.keys(this.elements).length; },
                catalogueColumns() {
                    if (this.catalogue.length === 0) return [];
                    return Object.keys(this.catalogue[0]);
                },
                catalogueNameColumn() {
                    // Find the column that contains the application name
                    const nameCol = this.catalogueColumns.find(col =>
                        col && (col.toLowerCase() === 'name' ||
                               col.toLowerCase() === 'application name' ||
                               col.toLowerCase().includes('name'))
                    );
                    return nameCol || this.catalogueColumns[0];
                },
                filteredCatalogue() {
                    if (!this.catalogueSearch) return this.catalogue;
                    const search = this.catalogueSearch.toLowerCase();
                    return this.catalogue.filter(app => {
                        return Object.values(app).some(val => {
                            return val && String(val).toLowerCase().includes(search);
                        });
                    });
                },
                viewsByCategory() {
                    const byCategory = {};
                    Object.values(this.views).forEach(view => {
                        const cat = view.category || 'General';
                        if (!byCategory[cat]) byCategory[cat] = [];
                        byCategory[cat].push(view);
                    });
                    // Sort categories alphabetically, with General last
                    const sorted = {};
                    const keys = Object.keys(byCategory).sort((a, b) => {
                        if (a === 'General') return 1;
                        if (b === 'General') return -1;
                        return a.localeCompare(b);
                    });
                    keys.forEach(k => { sorted[k] = byCategory[k]; });
                    return sorted;
                }
            },
            methods: {
                async initialize() {
                    try {
                        console.log('[EA Portal] Initializing...');
                        console.log('[EA Portal] Fetching view registry...');
                        this.views = await fetch('data/view_registry.json').then(r => r.json());
                        console.log('[EA Portal] Fetching element index...');
                        this.elements = await fetch('data/element_index.json').then(r => r.json());
                        console.log('[EA Portal] Fetching relationships...');
                        this.relationships = await fetch('data/relationship_graph.json').then(r => r.json());

                        // Load catalogue if available
                        try {
                            console.log('[EA Portal] Fetching catalogue...');
                            const catalogueData = await fetch('data/catalogue.json').then(r => r.json());
                            // Handle both new format (with metadata) and legacy format (array)
                            if (Array.isArray(catalogueData)) {
                                this.catalogue = catalogueData;
                                this.catalogueMetadata = { groupings: {}, columns: [] };
                            } else if (catalogueData.data && catalogueData.metadata) {
                                this.catalogue = catalogueData.data;
                                this.catalogueMetadata = catalogueData.metadata;
                            }
                            console.log(`[EA Portal] Loaded ${this.catalogue.length} applications from catalogue`);
                            console.log('[EA Portal] Catalogue groupings:', this.catalogueMetadata.groupings);
                        } catch (err) {
                            console.log('[EA Portal] No catalogue file found (optional):', err);
                            this.catalogue = [];
                            this.catalogueMetadata = { groupings: {}, columns: [] };
                        }

                        console.log(`[EA Portal] Loaded ${Object.keys(this.views).length} views, ${Object.keys(this.elements).length} elements`);
                        console.log('[EA Portal] totalApps:', this.totalApps, 'totalViews:', this.totalViews);

                        // Default to catalogue view if available, otherwise load first diagram
                        if (this.catalogue.length > 0) {
                            console.log('[EA Portal] Setting viewMode to catalogue');
                            this.viewMode = 'catalogue';
                        } else {
                            const firstViewId = Object.keys(this.views)[0];
                            if (firstViewId) {
                                console.log('[EA Portal] Loading first view:', firstViewId);
                                this.loadView(firstViewId);
                            }
                        }
                        console.log('[EA Portal] Initialization complete');
                    } catch (err) {
                        console.error('[EA Portal] Initialization failed:', err);
                    }
                },
                showCatalogue() {
                    this.viewMode = 'catalogue';
                    this.currentView = null;
                    this.selectedElement = null;
                    this.selectedCatalogueApp = null;
                    this.sidebarRightOpen = false;
                },
                selectCatalogueApp(app) {
                    // Find the name column - look for column named "NAME", "Application Name", "name", etc.
                    const nameColumn = this.catalogueColumns.find(col =>
                        col && (col.toLowerCase() === 'name' ||
                               col.toLowerCase() === 'application name' ||
                               col.toLowerCase().includes('name'))
                    ) || this.catalogueColumns[0];  // Fallback to first column

                    const appName = app[nameColumn];
                    console.log(`Looking for element matching: ${appName} (from column: ${nameColumn})`);

                    const matchingElement = Object.values(this.elements).find(el =>
                        el.name === appName || el.name.includes(appName) || appName.includes(el.name)
                    );

                    this.selectedCatalogueApp = app;

                    if (matchingElement) {
                        console.log(`Found matching element: ${matchingElement.id}`);
                        this.selectElement(matchingElement.id);
                    } else {
                        // No matching ArchiMate element, but still show sidebar with app info
                        console.log(`No matching element found for: ${appName}`);
                        this.selectedElement = null;
                        this.sidebarRightOpen = true;
                    }
                },
                closeSidebar() {
                    this.sidebarRightOpen = false;
                    this.selectedElement = null;
                    this.selectedCatalogueApp = null;
                },
                async loadView(viewId, keepElement = null) {
                    const view = this.views[viewId];
                    if (!view) return;

                    this.viewMode = 'diagram';
                    this.currentView = viewId;
                    // Only clear selected element if not preserving it
                    if (!keepElement) {
                        this.selectedElement = null;
                        this.selectedCatalogueApp = null;
                        this.sidebarRightOpen = false;
                    }

                    try {
                        const response = await fetch(view.diagram_path);
                        this.diagramHtml = await response.text();

                        this.$nextTick(() => {
                            const viewer = document.querySelector('.diagram-viewer');
                            viewer.querySelectorAll('[data-element-id]').forEach(el => {
                                el.addEventListener('click', (e) => {
                                    e.stopPropagation();
                                    this.selectElement(el.dataset.elementId);
                                });
                            });
                            this.currentSvg = viewer.querySelector('svg');

                            // Remove fixed width/height attributes to allow proper zoom scaling
                            if (this.currentSvg) {
                                // Capture width/height before removing, in case we need to set viewBox
                                const width = this.currentSvg.getAttribute('width') || 1000;
                                const height = this.currentSvg.getAttribute('height') || 1000;

                                // Ensure viewBox exists for proper scaling
                                if (!this.currentSvg.hasAttribute('viewBox')) {
                                    this.currentSvg.setAttribute('viewBox', `0 0 ${width} ${height}`);
                                }

                                // Remove fixed dimensions
                                this.currentSvg.removeAttribute('width');
                                this.currentSvg.removeAttribute('height');

                                // Reset zoom to fit-to-width for new diagrams
                                this.zoomLevel = 1;
                                this.fitToWidth = true;
                                this.applyZoom();
                            }
                        });
                    } catch (err) {
                        console.error('Error loading diagram:', err);
                    }
                },
                async navigateToView(viewId, elementId) {
                    // Navigate to a different view while keeping an element selected
                    await this.loadView(viewId, true);  // Pass true to keep the element
                    this.selectElement(elementId);
                },
                selectElement(elementId) {
                    if (!this.elements[elementId]) return;
                    this.selectedElement = elementId;
                    this.sidebarRightOpen = true;

                    this.$nextTick(() => {
                        if (this.currentSvg) {
                            this.currentSvg.querySelectorAll('[data-element-id]').forEach(el => {
                                el.classList.remove('element-highlighted');
                            });
                            const el = this.currentSvg.querySelector(`[data-element-id="${elementId}"]`);
                            if (el) el.classList.add('element-highlighted');
                        }
                    });
                },
                deselectElement() {
                    this.selectedElement = null;
                    this.selectedCatalogueApp = null;
                    this.sidebarRightOpen = false;
                    if (this.currentSvg) {
                        this.currentSvg.querySelectorAll('[data-element-id]').forEach(el => {
                            el.classList.remove('element-highlighted');
                        });
                    }
                },
                getGroupedHeaders() {
                    if (!this.catalogueMetadata.groupings || Object.keys(this.catalogueMetadata.groupings).length === 0) {
                        return [];
                    }

                    const grouped = [];
                    let currentGroup = null;
                    let currentColspan = 0;

                    for (const col of this.catalogueColumns) {
                        const grouping = this.catalogueMetadata.groupings[col];

                        if (grouping === currentGroup) {
                            currentColspan++;
                        } else {
                            if (currentGroup !== null) {
                                grouped.push({
                                    grouping: currentGroup,
                                    colspan: currentColspan
                                });
                            }
                            currentGroup = grouping;
                            currentColspan = 1;
                        }
                    }

                    // Add the last group
                    if (currentGroup !== null) {
                        grouped.push({
                            grouping: currentGroup,
                            colspan: currentColspan
                        });
                    }

                    return grouped;
                },
                getGroupingColor(grouping) {
                    if (!grouping) return 'rgba(0, 0, 0, 0.05)';
                    // Hash the grouping name to assign consistent colors
                    const colors = [
                        'rgba(70, 130, 180, 0.25)',   // Steel Blue
                        'rgba(255, 140, 0, 0.25)',    // Dark Orange
                        'rgba(34, 139, 34, 0.25)',    // Forest Green
                        'rgba(220, 20, 60, 0.25)',    // Crimson
                        'rgba(75, 0, 130, 0.25)',     // Indigo
                        'rgba(0, 100, 100, 0.25)',    // Dark Cyan
                        'rgba(184, 134, 11, 0.25)',   // Dark Goldenrod
                        'rgba(128, 0, 128, 0.25)',    // Purple
                    ];
                    const hash = grouping.split('').reduce((h, c) => h + c.charCodeAt(0), 0);
                    return colors[hash % colors.length];
                },
                getElementTypeIcon(type) {
                    const icons = {
                        'ApplicationComponent': '📦',
                        'Capability': '🎯',
                        'BusinessProcess': '⚙️',
                        'DataObject': '💾',
                        'TechnologyService': '☁️',
                    };
                    return icons[type] || '📋';
                },
                zoomIn() {
                    this.fitToWidth = false;
                    this.zoomLevel = Math.min(3, this.zoomLevel + 0.25);
                    this.applyZoom();
                },
                zoomOut() {
                    this.fitToWidth = false;
                    this.zoomLevel = Math.max(0.25, this.zoomLevel - 0.25);
                    this.applyZoom();
                },
                zoomReset() {
                    this.fitToWidth = false;
                    this.zoomLevel = 1;
                    this.applyZoom();
                },
                toggleFitToWidth() {
                    this.fitToWidth = !this.fitToWidth;
                    this.applyZoom();
                },
                applyZoom() {
                    if (!this.currentSvg) return;

                    if (this.fitToWidth) {
                        // Fit to width mode: remove transform, set width to 100%
                        this.currentSvg.style.transform = '';
                        this.currentSvg.style.width = '100%';
                        this.currentSvg.style.height = 'auto';
                    } else {
                        // Manual zoom mode: apply scale transform
                        this.currentSvg.style.transform = `scale(${this.zoomLevel})`;
                        this.currentSvg.style.width = 'auto';
                        this.currentSvg.style.height = 'auto';
                    }
                }
            },
            mounted() {
                this.initialize();
            }
        }).mount('#app');
    </script>
</body>
</html>
'''

        # Replace color placeholders
        template = template.replace('__LOGO_HTML__', logo_html)
        template = template.replace('__GRADIENT_START__', gradient_start)
        template = template.replace('__GRADIENT_END__', gradient_end)
        template = template.replace('__PRIMARY__', primary)
        template = template.replace('__ACCENT__', accent)

        return template


if __name__ == "__main__":
    builder = PortalBuilder()
    result = builder.build()

    if not result["success"]:
        print(f"\nErrors: {result['errors']}")
        exit(1)
