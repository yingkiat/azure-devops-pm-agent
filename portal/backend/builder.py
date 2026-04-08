"""Build interactive EA portal from diagrams and model data."""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import yaml
import shutil
import subprocess

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from .converter import DrawioToSvg
from .indexes import PortalIndexGenerator


class PortalBuilder:
    """Build static portal files from diagrams and ArchiMate model."""

    REGION_ORDER = ["JPN", "ANZ", "AEM", "APAC"]
    PREVIEW_WINDOW_SIZE = "2200,1600"

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
        self.preview_browser = self._find_preview_browser()

    def _load_diagram_metadata(self, relative_path: Path) -> Dict[str, str]:
        """Load explicit diagram metadata from matching YAML spec when available."""
        spec_path = self.specs_dir / relative_path.with_suffix(".yaml")
        if not spec_path.exists():
            return {}
        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                spec = yaml.safe_load(f) or {}
            metadata = spec.get("metadata", {}) or {}
            view_meta = spec.get("view", {}) or {}
            return {
                "name": view_meta.get("name") or "",
                "domain": metadata.get("domain") or view_meta.get("domain") or "",
                "region": metadata.get("region") or view_meta.get("region") or "",
            }
        except Exception:
            return {}

    def _is_azure_diagram(self, relative_path: Path) -> bool:
        """Return whether the matching YAML spec is an azure_diagram."""
        spec_path = self.specs_dir / relative_path.with_suffix(".yaml")
        if not spec_path.exists():
            return False
        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                spec = yaml.safe_load(f) or {}
            return spec.get("type") == "azure_diagram"
        except Exception:
            return False

    def _find_preview_browser(self) -> Optional[Path]:
        """Locate a Chromium-compatible browser for SVG to PNG preview rendering."""
        candidates = [
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
            Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _render_svg_preview_png(self, svg_path: Path, png_path: Path) -> bool:
        """Render a PNG preview from an SVG using headless Chromium when available."""
        if not self.preview_browser:
            return False

        png_path.parent.mkdir(parents=True, exist_ok=True)
        svg_uri = svg_path.resolve().as_uri()
        profile_dir = self.output_dir / ".preview-browser-profile"
        profile_dir.mkdir(parents=True, exist_ok=True)
        commands = [
            [
                str(self.preview_browser),
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--no-first-run",
                "--disable-crash-reporter",
                "--hide-scrollbars",
                "--allow-file-access-from-files",
                "--run-all-compositor-stages-before-draw",
                "--virtual-time-budget=3000",
                f"--user-data-dir={profile_dir}",
                f"--window-size={self.PREVIEW_WINDOW_SIZE}",
                f"--screenshot={png_path}",
                svg_uri,
            ],
            [
                str(self.preview_browser),
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--no-first-run",
                "--disable-crash-reporter",
                "--hide-scrollbars",
                "--allow-file-access-from-files",
                "--run-all-compositor-stages-before-draw",
                "--virtual-time-budget=3000",
                f"--user-data-dir={profile_dir}",
                f"--window-size={self.PREVIEW_WINDOW_SIZE}",
                f"--screenshot={png_path}",
                svg_uri,
            ],
        ]

        for command in commands:
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )
                if result.returncode == 0 and png_path.exists():
                    return True
            except Exception:
                continue

        return False

    @staticmethod
    def _default_display_name(drawio_file: Path) -> str:
        """Create a readable fallback display name from the filename."""
        acronym_tokens = {"ANZ", "APAC", "AEM", "ERP", "JPN", "QAD"}
        words = []
        for token in drawio_file.stem.replace("-", "_").split("_"):
            if not token:
                continue
            upper_token = token.upper()
            words.append(upper_token if upper_token in acronym_tokens else token.capitalize())
        return " ".join(words)

    def _infer_region(self, relative_path: Path) -> str:
        """Infer diagram region from filename/path, defaulting to APAC."""
        tokens = {
            token.lower()
            for part in relative_path.with_suffix("").parts
            for token in part.replace("-", "_").split("_")
            if token
        }
        for region in self.REGION_ORDER:
            if region.lower() in tokens:
                return region
        return "APAC"

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

        print(f"      OK Loaded {len(index_gen.elements)} elements\n")

        # Step 2: Convert application catalogue (optional)
        print("[2/5] Converting application catalogue...")
        catalogue_count = self._convert_catalogue()
        if catalogue_count > 0:
            print(f"      OK Converted {catalogue_count} applications from catalogue\n")
        else:
            print(f"      WARN No catalogue file found (optional)\n")

        # Step 3: Convert diagrams to SVG
        print("[3/5] Converting diagrams to SVG...")
        diagrams_info = self._convert_diagrams_to_svg()
        print(f"      OK Converted {len(diagrams_info)} diagrams\n")

        # Step 4: Generate indexes
        print("[4/6] Generating indexes...")
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

        print(f"      OK Indexed {len(element_index)} elements")
        print(f"      OK Mapped {sum(len(v['outbound']) + len(v['inbound']) for v in relationship_graph.values())} relationships")
        print(f"      OK Registered {len(view_registry)} views\n")

        # Step 5: Save indexes
        print("[5/6] Saving indexes...")
        if not index_gen.save_indexes(
            str(self.data_dir), element_index, relationship_graph, view_registry
        ):
            errors.append("Failed to save indexes")

        # Step 6: Generate analytics
        print("[6/6] Generating analytics...")
        analytics_result = self._generate_analytics_data()
        if not analytics_result.get("success"):
            print(f"      WARN Skipped (missing catalogue or elements data)\n")
        else:
            cat_count    = analytics_result["catalogue_count"]
            matched      = analytics_result["matched_count"]
            unmatched    = analytics_result["unmatched"]
            coverage     = analytics_result["property_coverage"]
            domain_sum   = analytics_result["domain_sum"]
            region_sum   = analytics_result["region_sum"]
            match_pct    = round(matched / cat_count * 100, 1) if cat_count else 0

            print(f"      OK Analytics data written")
            print(f"\n      --- Analytics Validation ---")
            match_flag = "OK" if match_pct >= 95 else "FAIL"
            print(f"      Element match rate: {matched}/{cat_count} ({match_pct}%)  {match_flag}")
            if unmatched:
                print(f"      Unmatched ({len(unmatched)}): {', '.join(unmatched[:5])}" +
                      (f" ... +{len(unmatched)-5} more" if len(unmatched) > 5 else ""))

            print(f"\n      Property coverage (matched elements):")
            for prop, count in coverage.items():
                pct = round(count / matched * 100, 1) if matched else 0
                flag = "OK" if pct >= 80 else ("WARN" if pct >= 50 else "FAIL")
                print(f"        {prop:<22} {count:>3}/{matched} ({pct:>5}%)  {flag}")

            print(f"\n      Chart data checks:")
            chart_counts = analytics_result["chart_counts"]
            for chart, count in chart_counts.items():
                flag = "OK" if count > 0 else "FAIL"
                print(f"        {chart:<30} {count:>4} entries  {flag}")
                if count == 0:
                    errors.append(f"Analytics chart '{chart}' has no data.")

            dom_flag = "OK" if domain_sum == cat_count else f"FAIL (got {domain_sum}, expected {cat_count})"
            reg_flag = "OK" if region_sum == cat_count else f"FAIL (got {region_sum}, expected {cat_count})"
            print(f"\n      Sum integrity:")
            print(f"        Domain totals:         {dom_flag}")
            print(f"        Region totals:         {reg_flag}")
            print()

            if match_pct < 95:
                errors.append(
                    f"Analytics match rate too low: {matched}/{cat_count} ({match_pct}%). "
                    "Run ea_import_catalogue to sync all apps."
                )

        # Copy frontend files
        self._copy_frontend_files()

        print(f"\n[Portal Builder] Complete! OK")
        print(f"  Output: {self.output_dir.absolute()}")
        print(f"  Open: file://{self.output_dir.absolute() / 'index.html'}\n")

        return {
            "success": len(errors) == 0,
            "diagrams_processed": len(diagrams_info),
            "elements_indexed": len(element_index),
            "views_registered": len(view_registry),
            "catalogue_apps": catalogue_count,
            "output_path": str(self.output_dir),
            "errors": errors,
        }

    def _generate_analytics_data(self) -> bool:
        """Compute portfolio analytics scoped to the application catalogue.

        Strategy:
        - Scope = catalogue apps (99 rows) — domain/region/tech_standard come from here
          since the catalogue has complete coverage for those fields.
        - Rich attributes (Application Type, Planning Horizon, Lifecycle Status, Criticality) only
          exist in properties.csv, so we match catalogue app names to ArchiMate element IDs
          and pull those properties from there.
        """
        import csv

        catalogue_json = self.data_dir / "catalogue.json"
        elements_file = self.model_dir / "elements.csv"
        properties_file = self.model_dir / "properties.csv"

        if not catalogue_json.exists():
            return {"success": False}

        try:
            with open(catalogue_json, encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            return {"success": False}

        catalogue = raw.get("data", raw) if isinstance(raw, dict) else raw
        if not catalogue:
            return {"success": False}

        # Resolve catalogue column names (they may vary slightly between Excel versions)
        col_keys = list(catalogue[0].keys())
        lower_map = {k.lower().strip(): k for k in col_keys}

        def find_col(*candidates):
            for c in candidates:
                match = lower_map.get(c.lower().strip())
                if match:
                    return match
            return None

        col_name    = find_col("name", "application name", "app name")
        col_domain  = find_col("domain", "business domain")
        col_sub_domain = find_col("sub_domain", "sub-domain", "sub domain", "subdomain")
        col_region  = find_col("region")
        col_tech    = find_col("tech_standard", "tech standard", "technology standard")
        col_biz_crit = find_col("business_criticality", "business criticality")

        _skip = {"", "-", "none", "nan", "n/a"}

        def clean(val):
            return str(val or "").strip()

        # Catalogue app names (our universe)
        catalogue_names = {clean(app.get(col_name, "")) for app in catalogue if col_name}
        catalogue_names.discard("")
        catalogue_names_lower = {n.lower(): n for n in catalogue_names}

        # Match catalogue names → ArchiMate element IDs (single pass)
        matched_ids = set()
        id_to_name  = {}
        name_to_id  = {}
        if elements_file.exists():
            with open(elements_file, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if row["Type"] != "ApplicationComponent":
                        continue
                    ename = row["Name"].strip()
                    if ename in catalogue_names or ename.lower() in catalogue_names_lower:
                        matched_ids.add(row["ID"])
                        id_to_name[row["ID"]] = ename
                        name_to_id[ename] = row["ID"]

        # Load properties only for matched elements
        matched_props = {}  # eid -> {key: value}
        if properties_file.exists() and matched_ids:
            with open(properties_file, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if row["ID"] in matched_ids:
                        matched_props.setdefault(row["ID"], {})[row["Key"]] = row["Value"]

        # Count a property key across matched elements
        def count_prop(prop_key):
            counts = {}
            for props in matched_props.values():
                val = clean(props.get(prop_key, ""))
                if val.lower() not in _skip:
                    counts[val] = counts.get(val, 0) + 1
            return dict(sorted(counts.items(), key=lambda x: -x[1]))

        # Count a catalogue column across all 99 apps (full coverage)
        def count_col(col):
            if not col:
                return {}
            counts = {}
            for app in catalogue:
                val = clean(app.get(col, ""))
                if val.lower() not in _skip:
                    counts[val] = counts.get(val, 0) + 1
            return dict(sorted(counts.items(), key=lambda x: -x[1]))

        # App name lists per property value (for drilldown)
        def apps_by_prop(prop_key):
            result = {}
            for eid, props in matched_props.items():
                val = clean(props.get(prop_key, ""))
                name = id_to_name.get(eid, "")
                if val.lower() not in _skip and name:
                    result.setdefault(val, []).append(name)
            return result

        # App name lists per catalogue column value (for drilldown)
        def apps_by_col(col):
            if not col:
                return {}
            result = {}
            for app in catalogue:
                val = clean(app.get(col, ""))
                name = clean(app.get(col_name, "")) if col_name else ""
                if val.lower() not in _skip and name:
                    result.setdefault(val, []).append(name)
            return result

        # Build per-application analytics records so the UI can filter client-side by domain
        records = []
        for app in catalogue:
            name = clean(app.get(col_name, "")) if col_name else ""
            if not name:
                continue
            elem_id = name_to_id.get(name) or name_to_id.get(catalogue_names_lower.get(name.lower(), ""))
            props = matched_props.get(elem_id, {}) if elem_id else {}
            records.append({
                "name": name,
                "domain": clean(app.get(col_domain, "")) if col_domain else "",
                "sub_domain": clean(app.get(col_sub_domain, "")) if col_sub_domain else "",
                "region": clean(app.get(col_region, "")) if col_region else "",
                "catalogue_tech_standard": clean(app.get(col_tech, "")) if col_tech else "",
                "business_criticality": clean(app.get(col_biz_crit, "")) if col_biz_crit else "",
                "hosting_type": clean(props.get("Hosting Type", "")),
                "tech_standard": clean(props.get("Tech Standard", "")),
                "lifecycle_status": clean(props.get("Lifecycle Status", "")),
                "roadmap_disposition": clean(props.get("Roadmap Disposition", "")),
                "planning_horizon": clean(props.get("Planning Horizon", "")) or clean(props.get("Horizon", "")),
            })

        # Rich attributes from properties.csv (scoped to catalogue-matched elements)
        app_type  = count_prop("Hosting Type")
        tech_std_props = count_prop("Tech Standard")
        lifecycle = count_prop("Lifecycle Status")
        roadmap_disposition = count_prop("Roadmap Disposition")
        planning_horizon_raw = count_prop("Planning Horizon")
        if not planning_horizon_raw:
            planning_horizon_raw = count_prop("Horizon")

        planning_horizon_apps = apps_by_prop("Planning Horizon")
        if not planning_horizon_apps:
            planning_horizon_apps = apps_by_prop("Horizon")
        planning_horizon = {
            "labels": ["Baseline", "In Progress", "In Review"],
            "values": [
                planning_horizon_raw.get("Baseline", 0),
                planning_horizon_raw.get("In Progress", 0),
                planning_horizon_raw.get("In Review", 0)
            ],
            "apps": {
                "Baseline": planning_horizon_apps.get("Baseline", []),
                "In Progress": planning_horizon_apps.get("In Progress", []),
                "In Review": planning_horizon_apps.get("In Review", []),
            },
        }

        # Legacy by sub-domain — use catalogue sub-domain for matched legacy apps
        cat_name_to_domain = {}
        cat_name_to_sub_domain = {}
        if col_domain and col_name:
            for app in catalogue:
                n = clean(app.get(col_name, ""))
                d = clean(app.get(col_domain, ""))
                if n and d.lower() not in _skip:
                    cat_name_to_domain[n] = d
        if col_sub_domain and col_name:
            for app in catalogue:
                n = clean(app.get(col_name, ""))
                sd = clean(app.get(col_sub_domain, ""))
                if n and sd.lower() not in _skip:
                    cat_name_to_sub_domain[n] = sd

        legacy_by_sub_domain = {}
        legacy_sub_domain_apps = {}
        for eid, props in matched_props.items():
            if props.get("Tech Standard") == "Legacy":
                ename = id_to_name.get(eid, "")
                sub_domain_val = cat_name_to_sub_domain.get(ename) or clean(props.get("Sub-Domain", ""))
                if sub_domain_val and sub_domain_val.lower() not in _skip:
                    legacy_by_sub_domain[sub_domain_val] = legacy_by_sub_domain.get(sub_domain_val, 0) + 1
                    if ename:
                        legacy_sub_domain_apps.setdefault(sub_domain_val, []).append(ename)
        legacy_by_sub_domain = dict(sorted(legacy_by_sub_domain.items(), key=lambda x: (-x[1], x[0])))

        # Structural attributes from catalogue (complete coverage for all 99 apps)
        domain = count_col(col_domain)
        region = count_col(col_region)
        tech_std = count_col(col_tech)
        criticality = count_col(col_biz_crit)

        total  = len(catalogue) or 1
        saas   = app_type.get("SaaS", 0)
        legacy = tech_std_props.get("Legacy", 0)
        custom = app_type.get("Home-grown", 0) + app_type.get("COTS", 0) + app_type.get("Excel", 0)

        analytics = {
            "summary": {
                "total_apps": len(catalogue),
                "legacy_count": legacy,
                "legacy_pct": round(legacy / total * 100, 1),
                "saas_count": saas,
                "saas_pct": round(saas / total * 100, 1),
                "custom_count": custom,
                "custom_pct": round(custom / total * 100, 1),
                "tech_standard_approved": tech_std.get("Approved", 0),
                "strategic_count": lifecycle.get("Strategic", 0),
                "sunset_count": lifecycle.get("Sunset", 0),
            },
            "application_type": {"labels": list(app_type.keys()), "values": list(app_type.values()), "apps": apps_by_prop("Hosting Type")},
            "planning_horizon": planning_horizon,
            "roadmap_disposition": {"labels": list(roadmap_disposition.keys()), "values": list(roadmap_disposition.values()), "apps": apps_by_prop("Roadmap Disposition")},
            "lifecycle_status": {"labels": list(lifecycle.keys()), "values": list(lifecycle.values()), "apps": apps_by_prop("Lifecycle Status")},
            "domain": {"labels": list(domain.keys()), "values": list(domain.values()), "apps": apps_by_col(col_domain)},
            "region": {"labels": list(region.keys()), "values": list(region.values()), "apps": apps_by_col(col_region)},
            "criticality": {"labels": list(criticality.keys()), "values": list(criticality.values()), "apps": apps_by_col(col_biz_crit)},
            "legacy_by_sub_domain": {"labels": list(legacy_by_sub_domain.keys()), "values": list(legacy_by_sub_domain.values()), "apps": legacy_sub_domain_apps},
            "tech_standard": {"labels": list(tech_std.keys()), "values": list(tech_std.values()), "apps": apps_by_col(col_tech)},
            "filters": {
                "domains": ["ALL"] + sorted([k for k in domain.keys() if k and k.lower() not in _skip])
            },
            "records": records,
        }

        with open(self.data_dir / "analytics.json", "w", encoding="utf-8") as f:
            json.dump(analytics, f, indent=2)

        # Compute validation stats
        rich_props = ["Hosting Type", "Tech Standard", "GXP"]
        property_coverage = {
            prop: sum(1 for p in matched_props.values() if clean(p.get(prop, "")))
            for prop in rich_props
        }
        unmatched_names = sorted(catalogue_names - {n for n in id_to_name.values()})

        return {
            "success": True,
            "catalogue_count": len(catalogue),
            "matched_count": len(matched_ids),
            "unmatched": unmatched_names,
            "property_coverage": property_coverage,
            "domain_sum": sum(domain.values()),
            "region_sum": sum(region.values()),
            "chart_counts": {
                "Application Type Breakdown": sum(app_type.values()),
                "Legacy Applications":        legacy,
                "SaaS Applications":          saas,
                "Legacy by Sub-Domain":       len(legacy_by_sub_domain),
                "Business Criticality":       sum(criticality.values()),
                "Tech Standard":              sum(tech_std.values()),
                "Domain Breakdown":           sum(domain.values()),
                "Region Breakdown":           sum(region.values()),
            },
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
            path_parts = relative_path.parts[:-1]
            explicit_meta = self._load_diagram_metadata(relative_path)
            domain = explicit_meta.get("domain") or (path_parts[0] if path_parts else "")
            region = explicit_meta.get("region") or self._infer_region(relative_path)

            # Use full relative path (without extension) as view_id for uniqueness
            view_id = relative_path.with_suffix("").as_posix().replace("/", "_")

            is_azure_diagram = self._is_azure_diagram(relative_path)

            # For azure_diagram views, require a sibling PNG and publish that directly.
            if is_azure_diagram:
                sibling_png = drawio_file.with_suffix(".png")
                if not sibling_png.exists():
                    print(f"      SKIP {view_id:45s} missing sibling PNG for azure_diagram")
                    continue

                png_output = self.diagrams_output_dir / relative_path.with_suffix(".png")
                png_output.parent.mkdir(parents=True, exist_ok=True)

                temp_svg_output = self.diagrams_output_dir / relative_path.with_suffix(".generated.svg")
                result = converter.convert(str(drawio_file), str(temp_svg_output))
                if result["success"]:
                    shutil.copy2(str(sibling_png), str(png_output))
                    if temp_svg_output.exists():
                        temp_svg_output.unlink()
                else:
                    if temp_svg_output.exists():
                        temp_svg_output.unlink()
                diagram_file = f"diagrams/{relative_path.with_suffix('.png').as_posix()}"
                preview_file = diagram_file
            else:
                svg_output = self.diagrams_output_dir / relative_path.with_suffix(".svg")
                svg_output.parent.mkdir(parents=True, exist_ok=True)
                result = converter.convert(str(drawio_file), str(svg_output))
                diagram_file = f"diagrams/{relative_path.with_suffix('.svg').as_posix()}"

                png_output = self.diagrams_output_dir / relative_path.with_suffix(".png")
                if result["success"] and self._render_svg_preview_png(svg_output, png_output):
                    preview_file = f"diagrams/{relative_path.with_suffix('.png').as_posix()}"
                else:
                    preview_file = diagram_file
                    print(f"      WARN {view_id:45s} PNG preview generation unavailable, falling back to SVG preview")

            if result["success"]:
                element_ids = [e["id"] for e in result.get("elements", [])]

                # Prefer explicit view name from spec; fall back to filename formatting.
                display_name = explicit_meta.get("name") or self._default_display_name(drawio_file)

                diagrams_info.append(
                    {
                        "view_id": view_id,
                        "name": display_name,
                        "diagram_file": diagram_file,
                        "preview_file": preview_file,
                        "category": category,
                        "domain": domain,
                        "region": region,
                        "elements": element_ids,
                        "element_count": len(element_ids),
                        "created": datetime.now().isoformat(),
                        "updated_at": datetime.fromtimestamp(drawio_file.stat().st_mtime).isoformat(),
                    }
                )
                print(f"      OK {view_id:45s} ({len(element_ids):2d} elements)")
            else:
                print(f"      FAIL {view_id:45s} {result.get('error', 'Unknown error')}")

        return diagrams_info

    def _convert_catalogue(self) -> int:
        """
        Convert Excel application catalogue to JSON.

        Returns:
            Number of applications converted (0 if catalogue not found or pandas not available)
        """
        if not PANDAS_AVAILABLE:
            print(f"      WARN pandas not installed, skipping catalogue conversion")
            return 0

        if not self.catalogue_file.exists():
            print(f"      WARN Catalogue file not found: {self.catalogue_file}")
            return 0

        try:
            # Read Excel file with groupings (row 0) and column names (row 1)
            df_all = pd.read_excel(str(self.catalogue_file), header=None)

            # Extract groupings from row 0 and column names from row 1
            groupings = {}
            if len(df_all) > 0:
                # Forward-fill NaN values in grouping row (row 0) to handle merged cells
                grouping_row = df_all.iloc[0].copy()
                grouping_row = grouping_row.ffill()

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
                if cleaned_record.get("it_owner"):
                    v = str(cleaned_record["it_owner"])
                    first, _ = v.split(".", 1) if "." in v else (v, "")
                    cleaned_record["it_owner"] = first[:3] + ("*.***" if "." in v else "***")
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
            print(f"      FAIL Error converting catalogue: {e}")
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
        print(f"      OK Created index.html with branding")

    def _load_branding_colors(self) -> Dict:
        """Load color scheme from branding/colors.json."""
        colors_file = self.branding_dir / "colors.json"
        if colors_file.exists():
            try:
                return json.loads(colors_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                print(f"      WARN Failed to load colors.json, using defaults")
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
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
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
        .view-category { margin-bottom: 1.5rem; }
        .view-category-title {
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            opacity: 0.55;
            padding: 0.5rem 1rem;
            margin-bottom: 0.25rem;
            letter-spacing: 0.8px;
        }
        .sidebar-section-divider {
            height: 1px;
            background: rgba(255,255,255,0.2);
            margin: 0.75rem 1rem 1.25rem;
        }
        .view-subcategory-title {
            font-size: 0.65rem;
            font-weight: 600;
            text-transform: uppercase;
            opacity: 0.45;
            padding: 0.4rem 1rem 0.25rem 1.75rem;
            letter-spacing: 0.6px;
        }
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
        .primary-view-item {
            border: 1px solid rgba(255,255,255,0.14);
            background: rgba(255,255,255,0.08);
            border-left-width: 4px;
            padding: 1rem;
        }
        .primary-view-item:hover {
            background: rgba(255,255,255,0.14);
            transform: translateX(2px);
        }
        .primary-view-item.active {
            background: rgba(255,255,255,0.22);
            box-shadow: 0 10px 24px rgba(0,0,0,0.14);
        }
        .primary-view-item.catalogue-item { border-left-color: #7dd3fc; }
        .primary-view-item.analytics-item { border-left-color: #86efac; }
        .view-item-topline {
            font-size: 0.64rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.7px;
            opacity: 0.72;
            margin-bottom: 0.55rem;
        }
        .view-item-row {
            display: block;
        }
        .view-item-copy { min-width: 0; }
        .library-hub {
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.12);
            border-left: 4px solid #fdba74;
            margin-bottom: 0.85rem;
        }
        .library-hub:hover {
            background: rgba(255,255,255,0.12);
        }
        .library-hub.active {
            background: rgba(255,255,255,0.16);
            border-left-color: #fb923c;
        }
        .library-hub .view-item-name {
            font-size: 1rem;
        }
        .library-hub-note {
            margin-top: 0.3rem;
            font-size: 0.76rem;
            line-height: 1.35;
            opacity: 0.75;
        }
        .library-subcategory-title {
            opacity: 0.62;
            padding-left: 1rem;
        }
        .library-children {
            margin-left: 0.95rem;
            padding-left: 0.8rem;
            border-left: 1px solid rgba(255,255,255,0.14);
        }
        .library-children .view-item {
            margin-bottom: 0.35rem;
        }

        .main {
            flex: 1;
            display: flex;
            flex-direction: column;
            min-width: 0;
            min-height: 0;
        }

        .header {
            padding: 1.5rem 2rem;
            border-bottom: 1px solid #e0e0e0;
            background: #fff;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .header h2 { margin: 0; font-size: 1.5rem; color: #333; }
        .page-hero {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1.5rem;
            border-radius: 1rem;
            padding: 1.1rem 1.35rem;
            border: 1px solid #e5e7eb;
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        }
        .page-hero-copy {
            min-width: 0;
        }
        .page-hero-kicker {
            font-size: 0.7rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            margin-bottom: 0.4rem;
        }
        .page-hero-subtitle {
            margin-top: 0.35rem;
            font-size: 0.9rem;
            color: #4b5563;
        }
        .page-hero-badge {
            min-width: 3rem;
            height: 3rem;
            border-radius: 1rem;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
            font-weight: 700;
            flex-shrink: 0;
            box-shadow: inset 0 0 0 1px rgba(15,23,42,0.06);
        }
        .page-hero.catalogue-hero {
            background: linear-gradient(135deg, #f0f9ff 0%, #ffffff 100%);
            border-color: #bae6fd;
        }
        .page-hero.catalogue-hero .page-hero-kicker { color: #0369a1; }
        .page-hero.catalogue-hero .page-hero-badge { background: #e0f2fe; color: #0369a1; }
        .page-hero.analytics-hero {
            background: linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%);
            border-color: #bbf7d0;
        }
        .page-hero.analytics-hero .page-hero-kicker { color: #15803d; }
        .page-hero.analytics-hero .page-hero-badge { background: #dcfce7; color: #166534; }
        .page-hero.library-hero {
            background: linear-gradient(135deg, #fff7ed 0%, #ffffff 100%);
            border-color: #fed7aa;
        }
        .page-hero.library-hero .page-hero-kicker { color: #c2410c; }
        .page-hero.library-hero .page-hero-badge { background: #ffedd5; color: #c2410c; }
        .diagram-hero {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 1.25rem;
            border-radius: 1rem;
            padding: 1.15rem 1.35rem;
            border: 1px solid #cfe9e2;
            background: linear-gradient(135deg, #f0fdfa 0%, #ffffff 100%);
        }
        .diagram-hero-copy {
            min-width: 0;
        }
        .diagram-hero-kicker {
            font-size: 0.7rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            margin-bottom: 0.4rem;
            color: #0f766e;
        }
        .diagram-hero h2 {
            margin: 0;
            font-size: 1.5rem;
            color: #1f2937;
        }
        .diagram-meta-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            margin-top: 0.55rem;
        }
        .diagram-meta-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.38rem 0.68rem;
            border-radius: 999px;
            background: rgba(255,255,255,0.95);
            border: 1px solid #dbe7f0;
            color: #334155;
            font-size: 0.77rem;
            font-weight: 700;
            letter-spacing: 0.03em;
        }
        .diagram-hero-actions {
            flex-shrink: 0;
            display: flex;
            align-items: center;
        }
        .diagram-back-button {
            border: 1px solid #cbd5e1;
            background: white;
            color: #0f172a;
            border-radius: 999px;
            padding: 0.7rem 1rem;
            cursor: pointer;
            font-size: 0.8rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            transition: all 0.2s;
        }
        .diagram-back-button:hover {
            border-color: __PRIMARY__;
            color: __PRIMARY__;
            box-shadow: 0 8px 18px rgba(0,0,0,0.08);
            transform: translateY(-1px);
        }

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
        .diagram-viewer img {
            background: white;
            border-radius: 8px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.1);
            display: block;
            transform-origin: top left;
            transition: transform 0.2s ease;
            max-width: none;
        }
        .diagram-stage {
            position: relative;
            min-height: 100%;
        }
        .diagram-preview {
            position: relative;
            z-index: 1;
        }
        .diagram-interactive {
            position: relative;
            z-index: 2;
        }
        .diagram-loading-overlay {
            position: absolute;
            inset: 1rem;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(249, 250, 252, 0.78);
            backdrop-filter: blur(2px);
            border-radius: 12px;
            z-index: 5;
            pointer-events: none;
        }
        .diagram-loading-pill {
            background: rgba(15, 23, 42, 0.88);
            color: white;
            padding: 0.7rem 1rem;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.25);
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
            min-height: 0;
            display: flex;
            flex-direction: column;
            gap: 1rem;
            background: #f9fafc;
            overflow: hidden;
            padding: 1.5rem;
        }
        .catalogue-search {
            flex-shrink: 0;
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
            flex: 1;
            min-height: 0;
            background: white;
            border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            overflow: auto;
            position: relative;
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
            cursor: pointer;
            user-select: none;
        }
        .catalogue-table th:hover { opacity: 0.85; }
        .sort-indicator { margin-left: 0.3rem; font-size: 0.6rem; }
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
        .drilldown-list { margin-top: 0.5rem; }
        .drilldown-item {
            padding: 0.6rem 0.75rem;
            margin-bottom: 0.25rem;
            border-radius: 6px;
            cursor: pointer;
            transition: background 0.15s;
            border-left: 3px solid transparent;
            font-size: 0.9rem;
        }
        .drilldown-item:hover { background: #f5f7fa; border-left-color: __PRIMARY__; }
        .drilldown-item-sub { font-size: 0.72rem; color: #999; margin-top: 0.1rem; }

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

        .analytics-viewer {
            flex: 1;
            background: #f9fafc;
            overflow: auto;
            padding: 1.5rem;
        }
        .analytics-filter-bar {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1rem;
            padding: 1rem 1.25rem;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .analytics-filter-bar label {
            font-size: 0.8rem;
            font-weight: 700;
            color: #555;
            text-transform: uppercase;
            letter-spacing: 0.4px;
        }
        .analytics-filter-bar select {
            min-width: 220px;
            padding: 0.55rem 0.75rem;
            border: 1px solid #d7dce3;
            border-radius: 6px;
            background: #fff;
            font: inherit;
            color: #333;
        }
        .analytics-filter-meta {
            font-size: 0.78rem;
            color: #666;
        }
        .analytics-stat-row {
            display: flex;
            gap: 1rem;
            margin-bottom: 1rem;
            flex-wrap: wrap;
        }
        .analytics-stat-card {
            flex: 1;
            min-width: 120px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            padding: 1.25rem;
            text-align: center;
            border-top: 3px solid __PRIMARY__;
            cursor: pointer;
            transition: box-shadow 0.2s, transform 0.15s;
        }
        .analytics-stat-card:hover {
            box-shadow: 0 6px 20px rgba(0,0,0,0.14);
            transform: translateY(-2px);
        }
        .analytics-stat-value {
            font-size: 2rem;
            font-weight: 700;
            color: __PRIMARY__;
            line-height: 1;
        }
        .analytics-stat-label {
            font-size: 0.75rem;
            color: #666;
            margin-top: 0.4rem;
            text-transform: uppercase;
            letter-spacing: 0.4px;
            font-weight: 600;
        }
        .analytics-stat-sub {
            font-size: 0.7rem;
            color: #999;
            margin-top: 0.2rem;
        }
        .analytics-chart-row {
            display: flex;
            gap: 1rem;
            margin-bottom: 1rem;
        }
        .analytics-chart-card {
            flex: 1;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            padding: 1.25rem;
        }
        .analytics-chart-title {
            font-size: 0.8rem;
            font-weight: 700;
            color: #333;
            margin-bottom: 1rem;
            text-transform: uppercase;
            letter-spacing: 0.4px;
        }
        .analytics-chart-wrap {
            position: relative;
            height: 220px;
        }
        .diagram-map-view {
            padding: 1.5rem;
            overflow: auto;
        }
        .diagram-map-stack {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }
        .diagram-map-toolbar {
            display: flex;
            gap: 0.75rem;
            align-items: center;
            flex-wrap: wrap;
            margin-bottom: 1rem;
        }
        .diagram-map-layer-band {
            border-radius: 14px;
            border: 1px solid transparent;
            padding: 0.95rem 1.1rem;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.55);
        }
        .diagram-map-layer-band.business {
            background: linear-gradient(180deg, #fff8cf 0%, #f6e49c 100%);
            border-color: #e5cb63;
        }
        .diagram-map-layer-band.technology {
            background: linear-gradient(180deg, #e0f3df 0%, #b9dfb7 100%);
            border-color: #7eb77b;
        }
        .diagram-map-layer-header {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            gap: 1rem;
            flex-wrap: wrap;
        }
        .diagram-map-layer-title {
            font-size: 0.82rem;
            font-weight: 800;
            color: #233142;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }
        .diagram-map-layer-subtitle {
            font-size: 0.76rem;
            color: #4d5a68;
        }
        .diagram-map-layer-placeholders {
            display: flex;
            flex-wrap: wrap;
            gap: 0.65rem;
            margin-top: 0.85rem;
        }
        .diagram-map-layer-pill {
            border-radius: 999px;
            padding: 0.4rem 0.75rem;
            font-size: 0.73rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            border: 1px dashed rgba(35, 49, 66, 0.2);
            color: #314154;
            background: rgba(255,255,255,0.45);
        }
        .diagram-map-application-shell {
            border-radius: 16px;
            border: 1px solid #8fb5de;
            background: linear-gradient(180deg, #eef6ff 0%, #dfeefe 100%);
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.6);
            padding: 1rem;
        }
        .diagram-map-application-shell .diagram-map-layer-header {
            margin-bottom: 0.9rem;
        }
        .diagram-map-toolbar input,
        .diagram-map-toolbar select {
            border: 1px solid #d0d7de;
            border-radius: 8px;
            padding: 0.55rem 0.75rem;
            font-size: 0.9rem;
            background: white;
        }
        .diagram-map-toolbar input {
            min-width: 260px;
        }
        .diagram-map-summary {
            margin-left: auto;
            font-size: 0.76rem;
            color: #6b7785;
        }
        .diagram-map-grid {
            display: grid;
            gap: 1px;
            background: #a9c4e3;
            border: 1px solid #a9c4e3;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 12px 28px rgba(31, 73, 125, 0.08);
        }
        .diagram-map-cell,
        .diagram-map-header,
        .diagram-map-region {
            background: #f7fbff;
            min-height: 120px;
            padding: 0.9rem;
        }
        .diagram-map-corner {
            background: linear-gradient(180deg, #dcecff 0%, #c9ddf4 100%);
            min-height: 72px;
            padding: 0.9rem;
            font-size: 0.78rem;
            font-weight: 700;
            color: #35506d;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }
        .diagram-map-header {
            background: linear-gradient(180deg, #dcecff 0%, #c9ddf4 100%);
            min-height: 72px;
        }
        .diagram-map-header-title,
        .diagram-map-region-title {
            font-size: 0.85rem;
            font-weight: 700;
            color: #233142;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
        .diagram-map-header-sub,
        .diagram-map-region-sub {
            margin-top: 0.35rem;
            font-size: 0.74rem;
            color: #6b7785;
        }
        .diagram-map-region {
            background: linear-gradient(180deg, #edf5ff 0%, #dfedfb 100%);
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        .diagram-map-cell {
            background: linear-gradient(180deg, #f8fbff 0%, #edf5fe 100%);
        }
        .diagram-map-empty {
            height: 100%;
            min-height: 90px;
            border: 1px dashed #b8cde4;
            border-radius: 10px;
            background: linear-gradient(180deg, #fafdff 0%, #edf5fe 100%);
        }
        .diagram-map-cards {
            display: flex;
            flex-direction: column;
            gap: 0.65rem;
        }
        .diagram-map-card {
            border: 1px solid #c4d7ea;
            border-radius: 10px;
            background: linear-gradient(180deg, #ffffff 0%, #f3f8fe 100%);
            padding: 0.8rem 0.9rem;
            cursor: pointer;
            transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
        }
        .diagram-map-card:hover {
            border-color: __PRIMARY__;
            box-shadow: 0 8px 20px rgba(0,0,0,0.08);
            transform: translateY(-1px);
        }
        .diagram-map-card-name {
            font-size: 0.9rem;
            font-weight: 700;
            color: #1f2933;
            line-height: 1.3;
        }
        .diagram-map-card-meta {
            margin-top: 0.45rem;
            font-size: 0.74rem;
            color: #6b7785;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        @media (max-width: 1024px) {
            .sidebar-right { width: 100%; z-index: 100; }
            .diagram-map-toolbar {
                flex-direction: column;
                align-items: stretch;
            }
            .diagram-map-toolbar input {
                min-width: 0;
            }
            .diagram-hero {
                flex-direction: column;
            }
            .diagram-hero-actions {
                width: 100%;
            }
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
                    <div class="view-item primary-view-item catalogue-item" :class="{ active: viewMode === 'catalogue' }" @click="showCatalogue()">
                        <div class="view-item-topline">Core Workspace</div>
                        <div class="view-item-row">
                            <div class="view-item-copy">
                                <div class="view-item-name">Application Catalogue</div>
                                <div class="view-item-count">{{ totalApps }} applications</div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Analytics -->
                <div class="view-category" v-if="analyticsData">
                    <div class="view-category-title">Insights</div>
                    <div class="view-item primary-view-item analytics-item" :class="{ active: viewMode === 'analytics' }" @click="showAnalytics()">
                        <div class="view-item-topline">Decision Support</div>
                        <div class="view-item-row">
                            <div class="view-item-copy">
                                <div class="view-item-name">Portfolio Analytics</div>
                                <div class="view-item-count">{{ analyticsData.summary.total_apps }} apps analysed</div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="view-category" v-if="totalViews > 0">
                    <div class="sidebar-section-divider"></div>
                    <div class="view-category-title" style="margin-bottom: 0.75rem;">Architecture</div>
                    <div class="view-item library-hub" :class="{ active: viewMode === 'diagram-map' }" @click="showDiagramMap()">
                        <div class="view-item-name">Architecture Library</div>
                        <div class="view-item-count">{{ totalViews }} views across domains</div>
                        <div class="library-hub-note">Browse the full library by region and domain, or jump directly into a folder below.</div>
                    </div>
                </div>

                <!-- Diagram categories -->
                <template v-for="(views, category) in viewsByCategory" :key="category">
                    <div class="view-category" v-if="views.length > 0">
                        <div class="view-subcategory-title library-subcategory-title">{{ category.charAt(0).toUpperCase() + category.slice(1) }}</div>
                        <div class="library-children">
                            <div v-for="view in views" :key="view.id" class="view-item" :class="{ active: currentView === view.id }" @click="loadView(view.id)">
                                <div class="view-item-name">{{ view.name }}</div>
                                <div class="view-item-count">{{ view.metadata.element_count }} elements</div>
                            </div>
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
                <div class="page-hero catalogue-hero">
                    <div class="page-hero-copy">
                        <div class="page-hero-kicker">Catalogue</div>
                        <h2>Application Catalogue</h2>
                        <div class="page-hero-subtitle">Browse the application inventory and inspect individual records.</div>
                    </div>
                    <div class="page-hero-badge">📚</div>
                </div>
            </div>
            <div class="header" v-else-if="viewMode === 'analytics'">
                <div class="page-hero analytics-hero">
                    <div class="page-hero-copy">
                        <div class="page-hero-kicker">Insights</div>
                        <h2>Portfolio Analytics</h2>
                        <div class="page-hero-subtitle">Track mix, lifecycle, standards and domain-level portfolio signals.</div>
                    </div>
                    <div class="page-hero-badge">📈</div>
                </div>
            </div>
            <div class="header" v-else-if="viewMode === 'diagram-map'">
                <div class="page-hero library-hero">
                    <div class="page-hero-copy">
                        <div class="page-hero-kicker">Library</div>
                        <h2>Architecture Library</h2>
                        <div class="page-hero-subtitle">Navigate architecture views by region and domain from one place.</div>
                    </div>
                    <div class="page-hero-badge">🗂️</div>
                </div>
            </div>
            <div class="header" v-else-if="currentViewData">
                <div class="diagram-hero">
                    <div class="diagram-hero-copy">
                        <div class="diagram-hero-kicker">Diagram Workspace</div>
                        <h2>{{ currentViewData.name }}</h2>
                        <div class="diagram-meta-row">
                            <div class="diagram-meta-chip" v-if="currentViewData.domain">Domain: {{ formatDomainLabel(currentViewData.domain) }}</div>
                            <div class="diagram-meta-chip" v-if="currentViewData.region">Region: {{ currentViewData.region }}</div>
                            <div class="diagram-meta-chip">{{ currentViewData.metadata.element_count }} elements</div>
                            <div class="diagram-meta-chip" v-if="currentViewData.category">Category: {{ currentViewData.category }}</div>
                            <div class="diagram-meta-chip" v-if="currentViewData.metadata.updated_at">Updated: {{ formatTimestamp(currentViewData.metadata.updated_at) }}</div>
                        </div>
                    </div>
                    <div class="diagram-hero-actions">
                        <button class="diagram-back-button" @click="showDiagramMap()">Back to Architecture Library</button>
                    </div>
                </div>
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
                                        :style="{ minWidth: col === catalogueNameColumn ? '200px' : 'auto' }"
                                        @click="sortBy(col)">
                                        {{ col }}<span class="sort-indicator" v-if="sortColumn === col">{{ sortDir === 1 ? '▲' : '▼' }}</span>
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
            <div v-else-if="viewMode === 'analytics'" class="analytics-viewer">
                <div v-if="!analyticsData" class="empty-state">
                    <p>No analytics data. Rebuild the portal to generate analytics.</p>
                </div>
                <div v-else>
                    <div class="analytics-filter-bar">
                        <label for="analytics-domain-filter">Domain</label>
                        <select id="analytics-domain-filter" v-model="selectedAnalyticsDomain" @change="refreshAnalyticsCharts()">
                            <option v-for="domain in availableAnalyticsDomains" :key="domain" :value="domain">{{ domain }}</option>
                        </select>
                        <div class="analytics-filter-meta">{{ filteredAnalyticsData.summary.total_apps }} applications in scope</div>
                    </div>
                    <!-- Stat Cards -->
                    <div class="analytics-stat-row">
                        <div class="analytics-stat-card" @click="showDrilldown('All Applications', cardApps('total'))">
                            <div class="analytics-stat-value">{{ filteredAnalyticsData.summary.total_apps }}</div>
                            <div class="analytics-stat-label">Total Applications</div>
                        </div>
                        <div class="analytics-stat-card" style="border-top-color:#dc3545;" @click="showDrilldown('Legacy', cardApps('legacy'))">
                            <div class="analytics-stat-value" style="color:#dc3545;">{{ filteredAnalyticsData.summary.legacy_pct }}%</div>
                            <div class="analytics-stat-label">Legacy</div>
                            <div class="analytics-stat-sub">{{ filteredAnalyticsData.summary.legacy_count }} apps</div>
                        </div>
                        <div class="analytics-stat-card" style="border-top-color:#28a745;" @click="showDrilldown('SaaS', cardApps('saas'))">
                            <div class="analytics-stat-value" style="color:#28a745;">{{ filteredAnalyticsData.summary.saas_pct }}%</div>
                            <div class="analytics-stat-label">SaaS</div>
                            <div class="analytics-stat-sub">{{ filteredAnalyticsData.summary.saas_count }} apps</div>
                        </div>
<div class="analytics-stat-card" style="border-top-color:#ffc107;" @click="showDrilldown('Tech Standard Approved', cardApps('tech_approved'))">
                            <div class="analytics-stat-value" style="color:#ffc107;">{{ filteredAnalyticsData.summary.tech_standard_approved }}</div>
                            <div class="analytics-stat-label">Tech Std Approved</div>
                            <div class="analytics-stat-sub">of {{ filteredAnalyticsData.summary.total_apps }} apps</div>
                        </div>
                    </div>

                    <!-- Charts Row 1: App Type + Criticality -->
                    <div class="analytics-chart-row">
                        <div class="analytics-chart-card" style="flex:1;">
                            <div class="analytics-chart-title">Application Type Breakdown</div>
                            <div class="analytics-chart-wrap"><canvas id="chartAppType"></canvas></div>
                        </div>
                        <div class="analytics-chart-card" style="flex:1;">
                            <div class="analytics-chart-title">Business Criticality</div>
                            <div class="analytics-chart-wrap"><canvas id="chartCriticality"></canvas></div>
                        </div>
                    </div>

                    <!-- Charts Row 2: Domain + Region -->
                    <div class="analytics-chart-row">
                        <div class="analytics-chart-card" style="flex:2;">
                            <div class="analytics-chart-title">{{ selectedAnalyticsDomain === 'ALL' ? 'Applications by Domain' : 'Applications by Sub-Domain' }}</div>
                            <div class="analytics-chart-wrap"><canvas id="chartDomain"></canvas></div>
                        </div>
                        <div class="analytics-chart-card" style="flex:1;">
                            <div class="analytics-chart-title">Region Distribution</div>
                            <div class="analytics-chart-wrap"><canvas id="chartRegion"></canvas></div>
                        </div>
                    </div>

                    <!-- Charts Row 3: Legacy by Domain -->
                    <div class="analytics-chart-row">
                        <div class="analytics-chart-card" style="flex:1;">
                            <div class="analytics-chart-title">{{ selectedAnalyticsDomain === 'ALL' ? 'Legacy Applications by Domain' : 'Legacy Applications by Sub-Domain' }}</div>
                            <div class="analytics-chart-wrap"><canvas id="chartLegacyDomain"></canvas></div>
                        </div>
                    </div>
                </div>
            </div>
            <div v-else-if="viewMode === 'diagram-map'" class="diagram-map-view">
                <div class="diagram-map-toolbar">
                    <input type="text" v-model="diagramMapSearch" placeholder="Search architecture views...">
                    <select v-model="selectedMapRegion">
                        <option value="ALL">All regions</option>
                        <option v-for="region in regionRows" :key="region" :value="region">{{ region }}</option>
                    </select>
                    <select v-model="selectedMapDomain">
                        <option value="ALL">All domains</option>
                        <option v-for="domain in diagramMapDomains" :key="domain" :value="domain">{{ formatDomainLabel(domain) }}</option>
                    </select>
                    <div class="diagram-map-summary">{{ filteredDiagramMapViews.length }} visible views</div>
                </div>
                <div class="diagram-map-stack">
                    <div class="diagram-map-layer-band business">
                        <div class="diagram-map-layer-header">
                            <div class="diagram-map-layer-title">Business Architecture</div>
                            <div class="diagram-map-layer-subtitle">Placeholder layer for capability, process and value-stream views</div>
                        </div>
                        <div class="diagram-map-layer-placeholders">
                            <div class="diagram-map-layer-pill">Capability maps</div>
                            <div class="diagram-map-layer-pill">Business processes</div>
                            <div class="diagram-map-layer-pill">Value streams</div>
                            <div class="diagram-map-layer-pill">Organisation overlays</div>
                        </div>
                    </div>

                    <div class="diagram-map-application-shell">
                        <div class="diagram-map-layer-header">
                            <div class="diagram-map-layer-title">Application Architecture</div>
                            <div class="diagram-map-layer-subtitle">Current diagram inventory shown in the active middle layer</div>
                        </div>
                        <div class="diagram-map-grid" :style="{ gridTemplateColumns: `180px repeat(${diagramMapDomains.length}, minmax(220px, 1fr))` }">
                            <div class="diagram-map-corner">Region / Domain</div>
                            <div v-for="domain in diagramMapDomains" :key="`head-${domain}`" class="diagram-map-header">
                                <div class="diagram-map-header-title">{{ formatDomainLabel(domain) }}</div>
                                <div class="diagram-map-header-sub">{{ diagramCountForDomain(domain) }} views</div>
                            </div>

                            <template v-for="region in regionRows" :key="`row-${region}`">
                                <div class="diagram-map-region">
                                    <div class="diagram-map-region-title">{{ region }}</div>
                                    <div class="diagram-map-region-sub">{{ diagramCountForRegion(region) }} views</div>
                                </div>
                                <div v-for="domain in diagramMapDomains" :key="`${region}-${domain}`" class="diagram-map-cell">
                                    <div v-if="diagramMapCellViews(region, domain).length === 0" class="diagram-map-empty"></div>
                                    <div v-else class="diagram-map-cards">
                                        <div v-for="view in diagramMapCellViews(region, domain)" :key="view.id" class="diagram-map-card" @click="loadView(view.id)">
                                            <div class="diagram-map-card-name">{{ view.name }}</div>
                                            <div class="diagram-map-card-meta">{{ view.metadata.element_count }} elements</div>
                                        </div>
                                    </div>
                                </div>
                            </template>
                        </div>
                    </div>

                    <div class="diagram-map-layer-band technology">
                        <div class="diagram-map-layer-header">
                            <div class="diagram-map-layer-title">Technology Architecture</div>
                            <div class="diagram-map-layer-subtitle">Placeholder layer for platform, infrastructure and integration views</div>
                        </div>
                        <div class="diagram-map-layer-placeholders">
                            <div class="diagram-map-layer-pill">Infrastructure platforms</div>
                            <div class="diagram-map-layer-pill">Hosting and network</div>
                            <div class="diagram-map-layer-pill">Integration runtime</div>
                            <div class="diagram-map-layer-pill">Technology standards</div>
                        </div>
                    </div>
                </div>
            </div>
            <div v-else class="diagram-viewer" @click="deselectElement()">
                <div class="diagram-stage">
                    <img v-if="diagramPreviewPath && !diagramHtml" class="diagram-preview" :src="diagramPreviewPath" alt="Diagram preview" />
                    <div v-if="diagramHtml" class="diagram-interactive" v-html="diagramHtml"></div>
                    <div v-if="diagramLoading" class="diagram-loading-overlay">
                        <div class="diagram-loading-pill">Loading Interactive Diagram</div>
                    </div>
                </div>
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

            <!-- Analytics drilldown app list -->
            <div v-if="drilldownApps.length > 0 && !selectedElement && !selectedCatalogueApp" class="element-panel">
                <div class="element-header">
                    <div class="element-icon">📊</div>
                    <div class="element-name">
                        <h2>{{ drilldownTitle }}</h2>
                        <div class="element-type">{{ drilldownApps.length }} applications</div>
                    </div>
                </div>
                <div class="drilldown-list">
                    <div v-for="app in drilldownApps" :key="app[catalogueNameColumn]"
                         class="drilldown-item" @click="selectDrilldownApp(app)">
                        {{ app[catalogueNameColumn] }}
                        <div class="drilldown-item-sub">{{ [app.domain, app.region].filter(Boolean).join(' · ') }}</div>
                    </div>
                </div>
            </div>

            <!-- Show catalogue app details if no matching ArchiMate element -->
            <div v-else-if="!selectedElement && selectedCatalogueApp" class="element-panel">
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
                    diagramImagePath: '',
                    diagramPreviewPath: '',
                    diagramLoading: false,
                    diagramSvgCache: {},
                    diagramRequestToken: 0,
                    currentSvg: null,
                    viewMode: 'catalogue',
                    diagramMapSearch: '',
                    selectedMapDomain: 'ALL',
                    selectedMapRegion: 'ALL',
                    sidebarRightOpen: false,
                    zoomLevel: 1,
                    fitToWidth: false,
                    analyticsData: null,
                    selectedAnalyticsDomain: 'ALL',
                    analyticsCharts: {},
                    sortColumn: null,
                    sortDir: 1,
                    drilldownTitle: '',
                    drilldownApps: []
                };
            },
            computed: {
                totalApps() { return this.catalogue.length; },
                totalViews() { return Object.keys(this.views).length; },
                totalElements() { return Object.keys(this.elements).length; },
                currentViewData() {
                    return this.currentView ? this.views[this.currentView] || null : null;
                },
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
                    let result = this.catalogue;
                    if (this.catalogueSearch) {
                        const search = this.catalogueSearch.toLowerCase();
                        result = result.filter(app =>
                            Object.values(app).some(val => val && String(val).toLowerCase().includes(search))
                        );
                    }
                    if (this.sortColumn) {
                        result = [...result].sort((a, b) => {
                            const va = String(a[this.sortColumn] ?? '');
                            const vb = String(b[this.sortColumn] ?? '');
                            return va.localeCompare(vb, undefined, { numeric: true }) * this.sortDir;
                        });
                    }
                    return result;
                },
                diagramMapDomains() {
                    const preferred = ['commercial', 'ERP', 'operations', 'infrastructure', 'data'];
                    const found = new Set(Object.values(this.views).map(view => view.domain).filter(Boolean));
                    const ordered = preferred.filter(domain => found.has(domain));
                    const remainder = Array.from(found)
                        .filter(domain => !preferred.includes(domain))
                        .sort((a, b) => a.localeCompare(b));
                    return [...ordered, ...remainder];
                },
                regionRows() {
                    return ['JPN', 'ANZ', 'AEM', 'APAC'];
                },
                filteredDiagramMapViews() {
                    const search = this.diagramMapSearch.trim().toLowerCase();
                    return Object.values(this.views).filter(view => {
                        if (this.selectedMapDomain !== 'ALL' && view.domain !== this.selectedMapDomain) return false;
                        if (this.selectedMapRegion !== 'ALL' && view.region !== this.selectedMapRegion) return false;
                        if (search && !String(view.name || '').toLowerCase().includes(search)) return false;
                        return true;
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
                },
                availableAnalyticsDomains() {
                    const domains = this.analyticsData?.filters?.domains;
                    if (Array.isArray(domains) && domains.length) return domains;
                    const found = new Set(['ALL']);
                    (this.analyticsData?.records || []).forEach(r => {
                        const d = String(r.domain || '').trim();
                        if (d) found.add(d);
                    });
                    return Array.from(found).sort((a, b) => {
                        if (a === 'ALL') return -1;
                        if (b === 'ALL') return 1;
                        return a.localeCompare(b);
                    });
                },
                filteredAnalyticsRecords() {
                    const records = this.analyticsData?.records || [];
                    if (this.selectedAnalyticsDomain === 'ALL') return records;
                    return records.filter(r => String(r.domain || '').trim() === this.selectedAnalyticsDomain);
                },
                filteredAnalyticsData() {
                    const records = this.filteredAnalyticsRecords;
                    const countBy = (key, options = {}) => {
                        const counts = {};
                        const apps = {};
                        for (const rec of records) {
                            const raw = rec[key];
                            const val = String(raw || '').trim();
                            if (!val) continue;
                            if (options.filter && !options.filter(rec, val)) continue;
                            counts[val] = (counts[val] || 0) + 1;
                            apps[val] = apps[val] || [];
                            apps[val].push(rec.name);
                        }
                        const entries = Object.entries(counts).sort((a, b) => {
                            if (b[1] !== a[1]) return b[1] - a[1];
                            return a[0].localeCompare(b[0]);
                        });
                        return {
                            labels: entries.map(([label]) => label),
                            values: entries.map(([, value]) => value),
                            apps
                        };
                    };
                    const total = records.length;
                    const legacyApps = records.filter(r => r.tech_standard === 'Legacy').map(r => r.name);
                    const saasApps = records.filter(r => r.hosting_type === 'SaaS').map(r => r.name);
                    const approvedApps = records.filter(r => r.catalogue_tech_standard === 'Approved').map(r => r.name);
                    return {
                        summary: {
                            total_apps: total,
                            legacy_count: legacyApps.length,
                            legacy_pct: total ? Math.round((legacyApps.length / total) * 1000) / 10 : 0,
                            saas_count: saasApps.length,
                            saas_pct: total ? Math.round((saasApps.length / total) * 1000) / 10 : 0,
                            tech_standard_approved: approvedApps.length
                        },
                        application_type: countBy('hosting_type'),
                        criticality: countBy('business_criticality'),
                        domain: countBy('domain'),
                        sub_domain: countBy('sub_domain'),
                        region: countBy('region'),
                        legacy_by_domain: countBy('domain', { filter: (rec) => rec.tech_standard === 'Legacy' }),
                        legacy_by_sub_domain: countBy('sub_domain', { filter: (rec) => rec.tech_standard === 'Legacy' }),
                        lifecycle_status: countBy('lifecycle_status'),
                        tech_standard: countBy('tech_standard')
                    };
                }
            },
            methods: {
                async initialize() {
                    try {
                        console.log('[EA Portal] Initializing...');
                        const fetchJson = (path) => fetch(path, { cache: 'no-store' }).then(r => r.json());
                        console.log('[EA Portal] Fetching view registry...');
                        this.views = await fetchJson('data/view_registry.json');
                        console.log('[EA Portal] Fetching element index...');
                        this.elements = await fetchJson('data/element_index.json');
                        console.log('[EA Portal] Fetching relationships...');
                        this.relationships = await fetchJson('data/relationship_graph.json');

                        // Load catalogue if available
                        try {
                            console.log('[EA Portal] Fetching catalogue...');
                            const catalogueData = await fetchJson('data/catalogue.json');
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

                        // Load analytics if available
                        try {
                            this.analyticsData = await fetchJson('data/analytics.json');
                            this.selectedAnalyticsDomain = 'ALL';
                            console.log('[EA Portal] Loaded analytics data');
                        } catch (err) {
                            console.log('[EA Portal] No analytics data found (optional):', err);
                        }

                        console.log(`[EA Portal] Loaded ${Object.keys(this.views).length} views, ${Object.keys(this.elements).length} elements`);
                        console.log('[EA Portal] totalApps:', this.totalApps, 'totalViews:', this.totalViews);

                        // Default landing page is the application catalogue when available.
                        if (this.catalogue.length > 0) {
                            console.log('[EA Portal] Setting viewMode to catalogue');
                            this.viewMode = 'catalogue';
                        } else if (Object.keys(this.views).length > 0) {
                            console.log('[EA Portal] Setting viewMode to diagram-map');
                            this.viewMode = 'diagram-map';
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
                showAnalytics() {
                    this.viewMode = 'analytics';
                    this.currentView = null;
                    this.selectedElement = null;
                    this.selectedCatalogueApp = null;
                    this.sidebarRightOpen = false;
                    this.$nextTick(() => { this.initAnalyticsCharts(); });
                },
                showDiagramMap() {
                    this.viewMode = 'diagram-map';
                    this.currentView = null;
                    this.selectedElement = null;
                    this.selectedCatalogueApp = null;
                    this.sidebarRightOpen = false;
                },
                formatDomainLabel(domain) {
                    if (!domain) return 'General';
                    if (domain === 'ERP') return 'ERP';
                    return domain.charAt(0).toUpperCase() + domain.slice(1);
                },
                diagramMapCellViews(region, domain) {
                    return this.filteredDiagramMapViews
                        .filter(view => view.region === region && view.domain === domain)
                        .sort((a, b) => a.name.localeCompare(b.name));
                },
                diagramCountForDomain(domain) {
                    return this.filteredDiagramMapViews.filter(view => view.domain === domain).length;
                },
                diagramCountForRegion(region) {
                    return this.filteredDiagramMapViews.filter(view => view.region === region).length;
                },
                refreshAnalyticsCharts() {
                    if (this.viewMode === 'analytics') {
                        this.$nextTick(() => { this.initAnalyticsCharts(); });
                    }
                },
                initAnalyticsCharts() {
                    if (!this.analyticsData) return;
                    Object.values(this.analyticsCharts).forEach(c => c.destroy());
                    this.analyticsCharts = {};
                    const dashboard = this.filteredAnalyticsData;

                    const appTypeColors = {
                        'SaaS': '#28a745', 'Cloud': '#17a2b8', 'OnPrem': '#ffc107',
                        'Azure': '#0052CC', 'Hybrid': '#6f42c1', 'IaaS': '#20c997',
                        'Home-grown': '#fd7e14', 'COTS': '#e83e8c'
                    };
                    const primaryColor = '__PRIMARY__';
                    const paletteBar = ['#0052CC','#1E5FD9','#00A651','#F39200','#6f42c1','#17a2b8','#dc3545','#fd7e14','#20c997','#e83e8c'];

                    const make = (id, config) => {
                        const el = document.getElementById(id);
                        if (el) this.analyticsCharts[id] = new Chart(el, config);
                    };

                    // Shared click/hover helpers
                    const clickFor = (dataKey) => (evt, elements, chart) => {
                        if (!elements.length) return;
                        const label = chart.data.labels[elements[0].index];
                        const apps = dashboard[dataKey]?.apps?.[label] || [];
                        if (apps.length) this.showDrilldown(label, apps);
                    };
                    const hoverCursor = (evt, elements) => {
                        evt.native.target.style.cursor = elements.length ? 'pointer' : 'default';
                    };

                    // Application Type — doughnut
                    make('chartAppType', {
                        type: 'doughnut',
                        data: {
                            labels: dashboard.application_type.labels,
                            datasets: [{ data: dashboard.application_type.values,
                                backgroundColor: dashboard.application_type.labels.map(l => appTypeColors[l] || '#aaa'),
                                borderWidth: 2 }]
                        },
                        options: { responsive: true, maintainAspectRatio: false,
                            onHover: hoverCursor, onClick: clickFor('application_type'),
                            plugins: { legend: { position: 'right', labels: { font: { size: 11 } } } } }
                    });



                    // Legacy by Domain — horizontal bar
                    const legacyBreakdownKey = this.selectedAnalyticsDomain === 'ALL' ? 'legacy_by_domain' : 'legacy_by_sub_domain';
                    make('chartLegacyDomain', {
                        type: 'bar',
                        data: {
                            labels: dashboard[legacyBreakdownKey].labels,
                            datasets: [{ label: 'Legacy Apps', data: dashboard[legacyBreakdownKey].values,
                                backgroundColor: '#dc3545', borderRadius: 4 }]
                        },
                        options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false,
                            onHover: hoverCursor, onClick: clickFor(legacyBreakdownKey),
                            plugins: { legend: { display: false } },
                            scales: { x: { beginAtZero: true, ticks: { stepSize: 1 } } } }
                    });

                    // Business Criticality — doughnut (Tier 1-4 from catalogue)
                    const critColors = {
                        'Tier 1 - Mission Critical': '#dc3545',
                        'Tier 2 - Business Critical': '#F39200',
                        'Tier 3 - Business Operational': '#ffc107',
                        'Tier 4 - Support Services': '#28a745'
                    };
                    make('chartCriticality', {
                        type: 'doughnut',
                        data: {
                            labels: dashboard.criticality.labels,
                            datasets: [{ data: dashboard.criticality.values,
                                backgroundColor: dashboard.criticality.labels.map(l => critColors[l] || '#aaa'),
                                borderWidth: 2 }]
                        },
                        options: { responsive: true, maintainAspectRatio: false,
                            onHover: hoverCursor, onClick: clickFor('criticality'),
                            plugins: { legend: { position: 'bottom', labels: { font: { size: 11 } } } } }
                    });

                    // Domain — horizontal bar
                    const domainBreakdownKey = this.selectedAnalyticsDomain === 'ALL' ? 'domain' : 'sub_domain';
                    make('chartDomain', {
                        type: 'bar',
                        data: {
                            labels: dashboard[domainBreakdownKey].labels,
                            datasets: [{ label: 'Apps', data: dashboard[domainBreakdownKey].values,
                                backgroundColor: dashboard[domainBreakdownKey].labels.map((_, i) => paletteBar[i % paletteBar.length]),
                                borderRadius: 4 }]
                        },
                        options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false,
                            onHover: hoverCursor, onClick: clickFor(domainBreakdownKey),
                            plugins: { legend: { display: false } },
                            scales: { x: { beginAtZero: true, ticks: { stepSize: 1 } } } }
                    });

                    // Region — bar
                    make('chartRegion', {
                        type: 'bar',
                        data: {
                            labels: dashboard.region.labels,
                            datasets: [{ label: 'Apps', data: dashboard.region.values,
                                backgroundColor: dashboard.region.labels.map((_, i) => paletteBar[i % paletteBar.length]), borderRadius: 4 }]
                        },
                        options: { responsive: true, maintainAspectRatio: false,
                            onHover: hoverCursor, onClick: clickFor('region'),
                            plugins: { legend: { display: false } },
                            scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } }
                    });
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
                sortBy(col) {
                    if (this.sortColumn === col) {
                        this.sortDir = this.sortDir === 1 ? -1 : 1;
                    } else {
                        this.sortColumn = col;
                        this.sortDir = 1;
                    }
                },
                cardApps(key) {
                    const d = this.filteredAnalyticsData;
                    if (!d) return [];
                    const at = d.application_type?.apps || {};
                    const lc = d.lifecycle_status?.apps || {};
                    const ts = d.tech_standard?.apps || {};
                    switch (key) {
                        case 'total':        return this.filteredAnalyticsRecords.map(r => r.name);
                        case 'legacy':       return ts['Legacy'] || [];
                        case 'saas':         return at['SaaS'] || [];
                        case 'custom':       return [...(at['Home-grown'] || []), ...(at['COTS'] || []), ...(at['Excel'] || [])];
                        case 'tech_approved': return ts['Approved'] || [];
                        case 'strategic':    return lc['Strategic'] || [];
                        case 'sunset':       return lc['Sunset'] || [];
                        default:             return [];
                    }
                },
                showDrilldown(title, appNames) {
                    const nameCol = this.catalogueNameColumn;
                    const nameSet = new Set(appNames);
                    this.drilldownTitle = title;
                    this.drilldownApps = this.catalogue.filter(app => nameSet.has(String(app[nameCol] || '').trim()));
                    this.selectedElement = null;
                    this.selectedCatalogueApp = null;
                    this.sidebarRightOpen = true;
                },
                selectDrilldownApp(app) {
                    this.drilldownApps = [];
                    this.drilldownTitle = '';
                    this.selectCatalogueApp(app);
                },
                closeSidebar() {
                    this.sidebarRightOpen = false;
                    this.selectedElement = null;
                    this.selectedCatalogueApp = null;
                    this.drilldownApps = [];
                    this.drilldownTitle = '';
                },
                wireDiagramInteractions() {
                    const viewer = document.querySelector('.diagram-viewer');
                    if (!viewer) return;

                    viewer.querySelectorAll('[data-element-id]').forEach(el => {
                        el.addEventListener('click', (e) => {
                            e.stopPropagation();
                            this.selectElement(el.dataset.elementId);
                        });
                    });

                    this.currentSvg = viewer.querySelector('.diagram-interactive svg')
                        || viewer.querySelector('.diagram-preview')
                        || viewer.querySelector('img');

                    if (this.currentSvg && this.currentSvg.tagName && this.currentSvg.tagName.toLowerCase() === 'svg') {
                        const width = this.currentSvg.getAttribute('width') || 1000;
                        const height = this.currentSvg.getAttribute('height') || 1000;

                        if (!this.currentSvg.hasAttribute('viewBox')) {
                            this.currentSvg.setAttribute('viewBox', `0 0 ${width} ${height}`);
                        }

                        this.currentSvg.removeAttribute('width');
                        this.currentSvg.removeAttribute('height');
                    }

                    this.zoomLevel = 1;
                    this.fitToWidth = false;
                    this.applyZoom();

                    if (this.selectedElement && this.diagramHtml) {
                        this.selectElement(this.selectedElement);
                    }
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
                        const requestToken = ++this.diagramRequestToken;
                        this.diagramLoading = true;
                        this.diagramHtml = '';
                        this.diagramImagePath = '';
                        this.diagramPreviewPath = view.preview_path || view.diagram_path;
                        this.currentSvg = null;

                        if (view.diagram_path.toLowerCase().endsWith('.png')) {
                            this.diagramImagePath = view.diagram_path;
                            this.diagramPreviewPath = view.preview_path || view.diagram_path;
                            this.diagramLoading = false;
                            this.$nextTick(() => {
                                this.wireDiagramInteractions();
                            });
                        } else {
                            this.$nextTick(() => {
                                this.wireDiagramInteractions();
                            });

                            let svgText = this.diagramSvgCache[view.diagram_path];
                            if (!svgText) {
                                const response = await fetch(view.diagram_path, { cache: 'force-cache' });
                                svgText = await response.text();
                                this.diagramSvgCache[view.diagram_path] = svgText;
                            }

                            if (requestToken !== this.diagramRequestToken) return;

                            this.diagramHtml = svgText;
                            this.diagramLoading = false;
                            this.$nextTick(() => {
                                this.wireDiagramInteractions();
                            });
                        }
                    } catch (err) {
                        console.error('Error loading diagram:', err);
                        this.diagramLoading = false;
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
                formatTimestamp(value) {
                    if (!value) return '';
                    const dt = new Date(value);
                    if (Number.isNaN(dt.getTime())) return value;
                    return dt.toLocaleString(undefined, {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                        hour: 'numeric',
                        minute: '2-digit'
                    });
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
