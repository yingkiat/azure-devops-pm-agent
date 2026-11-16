import copy
import json
import runpy
import shutil
from pathlib import Path

import pytest
from jsonschema import ValidationError

from portal.backend.architecture_decisions import load_register, render_register
from portal.backend.builder import PortalBuilder
from portal.backend.indexes import PortalIndexGenerator


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "portal" / "assets" / "architecture-decisions.html"


@pytest.fixture
def register():
    return {
        "source": {
            "document": "design-v0.7.docx",
            "version": "0.7",
            "date": "2026-11-05",
            "approval_status": "review_candidate",
            "sha256": "a" * 64,
            "processed_at": "2026-11-12",
        },
        "entries": [{
            "id": "SAMPLE-001",
            "title": "Keep database writes in the application",
            "kind": "decision",
            "status": "stated",
            "position": "Boomi must not write application SQL.",
            "systems": ["Boomi", "SQL"],
            "rationale": None,
            "source_sections": ["3 Integration Overview"],
        }],
    }


def test_project_level_view_uses_spec_metadata_without_environment(tmp_path, monkeypatch, register):
    monkeypatch.chdir(tmp_path)
    project = Path("ea_inputs/04_projects/operations/sample-folder")
    design = project / "design"
    design.mkdir(parents=True)
    (design / "architecture-decisions.json").write_text(json.dumps(register), encoding="utf-8")
    specs = Path("ea_inputs/views")
    specs.mkdir(parents=True)
    (specs / "sample.yaml").write_text(
        "type: json_inventory\n"
        "inventory: 04_projects/operations/sample-folder\n"
        "metadata:\n"
        "  project: Sample Project\n"
        "  project_key: stable-key\n"
        "  region: JPN\n",
        encoding="utf-8",
    )
    template = Path("portal/assets/architecture-decisions.html")
    template.parent.mkdir(parents=True)
    shutil.copyfile(TEMPLATE, template)

    builder = PortalBuilder(output_dir=str(tmp_path / "dist"))
    views = builder._collect_architecture_decision_views()
    view = views[0]
    assert view["project_key"] == "stable-key"
    assert view["project"] == "Sample Project"
    assert view["region"] == "JPN"
    assert view["category"] == "operations"
    assert view["environment"] == ""
    assert view["view_kind"] == "project"
    assert view["artifact_label"] == "Architecture Decisions"
    registry = PortalIndexGenerator().generate_view_registry(views)
    registered = registry[view["view_id"]]
    assert registered["iframe_src"] == "projects/stable-key/architecture-decisions/"
    page = (builder.output_dir / registered["iframe_src"] / "index.html").read_text(encoding="utf-8")
    assert "Sample Project / Design" in page
    assert "Review candidate - not Architecture-approved" in page
    assert "Not stated in source." in page
    assert 'data-status="stated"' in page
    assert "3 Integration Overview" in page


@pytest.mark.parametrize("invalid", ["missing_evidence", "duplicate_id", "invalid_date"])
def test_invalid_register_is_rejected(tmp_path, register, invalid):
    if invalid == "missing_evidence":
        del register["entries"][0]["source_sections"]
    elif invalid == "duplicate_id":
        register["entries"].append(copy.deepcopy(register["entries"][0]))
    else:
        register["source"]["date"] = "2026-99-99"
    path = tmp_path / "architecture-decisions.json"
    path.write_text(json.dumps(register), encoding="utf-8")
    with pytest.raises((ValidationError, ValueError)):
        load_register(path)


def test_render_escapes_document_and_entry_text(register):
    attack = '</script><img src=x onerror="alert(1)">'
    register["source"]["document"] = attack
    register["entries"][0]["title"] = attack
    register["entries"][0]["position"] = attack
    register["entries"][0]["systems"] = [attack]
    register["entries"][0]["source_sections"] = [attack]
    page = render_register(register, attack, TEMPLATE)
    assert "<img" not in page
    assert "&lt;/script&gt;&lt;img" in page
    assert 'data-search="sample-001 &lt;/script&gt;' in page


def test_model_file_monitor_excludes_design_but_preserves_environment_inputs(tmp_path):
    # Avoid the core package initializer's unrelated orchestrator imports.
    FileChangeMonitor = runpy.run_path(str(ROOT / "src" / "core" / "file_monitor.py"))["FileChangeMonitor"]
    project = tmp_path / "ea_inputs" / "04_projects" / "operations" / "sample"
    design = project / "design"
    design.mkdir(parents=True)
    for name in ("architecture-decisions.json", "sources.local.yaml", "notes.md"):
        (design / name).write_text("candidate design", encoding="utf-8")
    env = project / "dev"
    env.mkdir()
    inventory = env / "app-inventory.dev.json"
    inventory.write_text("{}", encoding="utf-8")
    monitor = FileChangeMonitor(journal_dir=str(tmp_path / "journal"))
    changes = monitor.detect_changes(str(project.parent.parent))
    assert changes.total_files == 1
    assert Path(changes.new_files[0]).name == inventory.name
    assert len(monitor.tracked_files) == 1
