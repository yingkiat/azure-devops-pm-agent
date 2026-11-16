import copy
import json
import re
import shutil
from pathlib import Path

import pytest
import yaml
from jsonschema import ValidationError

from portal.backend.builder import PortalBuilder
from portal.backend.indexes import PortalIndexGenerator
from portal.backend.process_views import load_process, render_process


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "ea_inputs" / "04_projects" / "operations" / "PSS2" / "design" / "infrastructure-onboarding.yaml"
TEMPLATE = ROOT / "portal" / "assets" / "process-view.html"


@pytest.fixture
def process():
    data = load_process(SOURCE, ROOT / "ea_inputs")
    del data["inventory_evidence"]
    data["project"].pop("ticket_history_file", None)
    data["project"]["observations"] = []
    return data


def write_process(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_pss_source_keeps_assumptions_and_inventory_timestamps_separate():
    data = load_process(SOURCE, ROOT / "ea_inputs")
    assert all(activity["timing"]["basis"] == "assumption" for activity in data["activities"])
    evidence = data["inventory_evidence"]["foundation-reference"]
    assert evidence["generated_at"] == "2026-09-16T08:32:26Z"
    observation = next(item for item in data["project"]["observations"] if item["id"] == "foundation-reference")
    assert observation["date"] is None
    assert len(evidence["artifacts"]) == 4


def test_environment_stage_preserves_cab_approval_before_production_release():
    data = load_process(SOURCE, ROOT / "ea_inputs")
    activities = {activity["id"]: activity for activity in data["activities"]}
    assert activities["apply-settings"]["phase"] == activities["validate-service"]["phase"]
    assert activities["validate-service"]["depends_on"] == ["apply-settings"]
    assert activities["approve-production"]["depends_on"] == ["validate-service"]
    assert activities["release-service"]["depends_on"] == ["approve-production"]
    assert activities["approve-production"]["owner"] != activities["release-service"]["owner"]
    assert "verify-handover" not in activities
    assert all(activity["owner"] not in activity["contributors"] for activity in activities.values())


@pytest.mark.parametrize("invalid", [None, "headers", "duplicate", "incomplete", "unknown", "missing_source", "both"])
def test_ticket_csv_resolves_only_valid_activity_references(tmp_path, process, invalid):
    inputs = tmp_path / "ea_inputs"
    relative = "04_projects/operations/sample/design/ticket-history.csv"
    csv_path = inputs / relative
    csv_path.parent.mkdir(parents=True)
    header = "Ticket No,Purpose,System,Request Type,Assigned To\n"
    row = '123,"API registration, OIDC",Service Catalog,App Registration,CloudOps\n'
    if invalid == "headers":
        header = "Ticket,Purpose,System,Request Type,Assigned To\n"
    elif invalid == "duplicate":
        row += row
    elif invalid == "incomplete":
        row = "123,API registration,Service Catalog,App Registration\n"
    csv_path.write_text(header + row, encoding="utf-8-sig")
    process["project"]["ticket_history_file"] = relative
    record = process["activities"][0]["record"]
    record["ticket_numbers"] = ["999" if invalid == "unknown" else "123"]
    if invalid == "missing_source":
        del process["project"]["ticket_history_file"]
    elif invalid == "both":
        record["tickets"] = [{"number": "123", "purpose": "Conflicting copy", "system": "Ticket",
                              "request_type": "Request", "assigned_to": "Another team"}]
    path = write_process(csv_path.parent / "infrastructure-onboarding.yaml", process)
    if invalid:
        with pytest.raises((ValueError, ValidationError)):
            load_process(path, inputs)
    else:
        loaded = load_process(path, inputs)
        assert loaded["activities"][0]["record"]["tickets"] == [{
            "number": "123", "purpose": "API registration, OIDC", "system": "Service Catalog",
            "request_type": "App Registration", "assigned_to": "CloudOps",
        }]
        assert "tickets" not in yaml.safe_load(path.read_text(encoding="utf-8"))["activities"][0]["record"]
        csv_path.write_text(header + row.replace("CloudOps", "Network"), encoding="utf-8")
        refreshed = load_process(path, inputs)
        assert refreshed["activities"][0]["record"]["tickets"][0]["assigned_to"] == "Network"


@pytest.mark.parametrize("collection,invalid", [
    ("phases", "inverted"), ("activities", "inverted"), ("activities", "non_finite")
])
def test_invalid_duration_ranges_are_rejected(tmp_path, process, collection, invalid):
    timing = process[collection][0]["timing"]
    if invalid == "inverted":
        timing["min_days"], timing["max_days"] = 10, 2
    else:
        timing["max_days"] = float("nan")
    with pytest.raises(ValueError, match="duration range"):
        load_process(write_process(tmp_path / "process.yaml", process))


@pytest.mark.parametrize("invalid", ["duplicate", "unknown_role", "cycle", "negative_wait", "unsafe_record", "incomplete_ticket", "incomplete_layout"])
def test_invalid_process_cannot_be_published(tmp_path, process, invalid):
    if invalid == "duplicate":
        process["activities"].append(copy.deepcopy(process["activities"][0]))
    elif invalid == "unknown_role":
        process["activities"][0]["owner"] = "unknown"
    elif invalid == "cycle":
        process["activities"][0]["depends_on"] = [process["activities"][-1]["id"]]
    elif invalid == "negative_wait":
        process["activities"][0]["timing"]["queue_days"] = -1
    elif invalid == "unsafe_record":
        process["activities"][0]["record"]["url"] = "javascript:alert(1)"
    elif invalid == "incomplete_ticket":
        record = next(activity["record"] for activity in process["activities"] if activity["record"].get("tickets"))
        del record["tickets"][0]["assigned_to"]
    else:
        process["layout"]["phase_order"].pop()
    with pytest.raises((ValueError, ValidationError)):
        load_process(write_process(tmp_path / "process.yaml", process))


def test_unknown_inventory_binding_fails_instead_of_implying_evidence(tmp_path, process):
    inputs = tmp_path / "ea_inputs"
    inventory = inputs / "04_projects" / "operations" / "sample" / "test" / "infra-inventory.test.json"
    inventory.parent.mkdir(parents=True)
    inventory.write_text(json.dumps({"environment": "test", "artifacts": [{"id": "known"}]}), encoding="utf-8")
    process["project"]["observations"] = [{
        "id": "missing-resource", "activities": ["provision-workload"], "source": "test-inventory",
        "classification": "inventory_reference", "date": None, "text": "Inventory reference",
        "inventory": {"file": inventory.relative_to(inputs).as_posix(), "artifact_ids": ["unknown"]},
    }]
    path = inputs / "04_projects" / "operations" / "sample" / "design" / "infrastructure-onboarding.yaml"
    with pytest.raises(ValueError, match="unknown IDs"):
        load_process(write_process(path, process), inputs)


def test_process_payload_and_heading_cannot_break_out_of_html(process):
    attack = '</script><img src=x onerror="alert(1)">'
    process["activities"][0]["name"] = attack
    ticket = next(activity["record"]["tickets"][0] for activity in process["activities"] if activity["record"].get("tickets"))
    ticket["purpose"] = attack
    page = render_process(process, attack, TEMPLATE)
    assert attack not in page
    assert "&lt;/script&gt;&lt;img" in page
    payload = re.search(r'<script id="process-data" type="application/json">(.*?)</script>', page, re.S).group(1)
    decoded = json.loads(payload)
    assert decoded["activities"][0]["name"] == attack
    rendered_ticket = next(activity["record"]["tickets"][0] for activity in decoded["activities"] if activity["record"].get("tickets"))
    assert rendered_ticket == ticket


def test_process_page_joins_existing_project_navigation(tmp_path, monkeypatch, process):
    monkeypatch.chdir(tmp_path)
    write_process(Path("ea_inputs/04_projects/operations/sample/design/infrastructure-onboarding.yaml"), process)
    specs = Path("ea_inputs/views")
    specs.mkdir(parents=True)
    (specs / "sample.yaml").write_text(
        "type: json_inventory\ninventory: 04_projects/operations/sample\nmetadata:\n"
        "  project: Sample project\n  project_key: stable-key\n  region: ANZ\n",
        encoding="utf-8",
    )
    template = Path("portal/assets/process-view.html")
    template.parent.mkdir(parents=True)
    shutil.copyfile(TEMPLATE, template)
    builder = PortalBuilder(output_dir=str(tmp_path / "dist"))
    views = builder._collect_process_views()
    view = views[0]
    assert view["project_key"] == "stable-key"
    assert view["environment"] == ""
    assert view["view_kind"] == "project"
    registry = PortalIndexGenerator().generate_view_registry(views)
    assert registry[view["view_id"]]["iframe_src"] == "projects/stable-key/infrastructure-onboarding/"
    assert (builder.output_dir / registry[view["view_id"]]["iframe_src"] / "index.html").is_file()
