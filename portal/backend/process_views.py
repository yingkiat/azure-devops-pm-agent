"""Validate and render source-defined project process walkthroughs."""

import csv
import json
import math
from html import escape
from pathlib import Path
from string import Template
from typing import Dict

import yaml
from jsonschema import Draft202012Validator, FormatChecker


SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "ea_inputs" / "04_projects" / "_schema" / "process-view.schema.json"
)


def load_process(path: Path, inputs_dir: Path = Path("ea_inputs")) -> Dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(data)
    indexes = {}
    for collection in ("roles", "services", "phases", "activities"):
        items = data[collection]
        indexes[collection] = {item["id"]: item for item in items}
        if len(indexes[collection]) != len(items):
            raise ValueError(f"{path}: duplicate IDs in {collection}")
    for item in [*data["phases"], *data["activities"]]:
        timing = item["timing"]
        if not all(math.isfinite(timing[key]) for key in ("min_days", "max_days")):
            raise ValueError(f"{path}: non-finite duration range for {item['id']}")
        if timing["min_days"] > timing["max_days"]:
            raise ValueError(f"{path}: inverted duration range for {item['id']}")

    sources = {source["id"]: source for source in data["project"]["sources"]}
    if len(sources) != len(data["project"]["sources"]):
        raise ValueError(f"{path}: duplicate source IDs")
    observations = data["project"]["observations"]
    if len({item["id"] for item in observations}) != len(observations):
        raise ValueError(f"{path}: duplicate observation IDs")

    def require_refs(values, collection, label):
        unknown = set(values) - set(collection)
        if unknown:
            raise ValueError(f"{path}: {label} references unknown IDs: {sorted(unknown)}")

    tickets = {}
    if "ticket_history_file" in data["project"]:
        root = inputs_dir.resolve()
        ticket_path = (root / data["project"]["ticket_history_file"]).resolve()
        if not ticket_path.is_relative_to(root):
            raise ValueError(f"{path}: ticket history reference escapes ea_inputs")
        columns = {
            "Ticket No": "number", "Purpose": "purpose", "System": "system",
            "Request Type": "request_type", "Assigned To": "assigned_to",
        }
        with ticket_path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            if not reader.fieldnames or len(reader.fieldnames) != len(columns) or set(reader.fieldnames) != set(columns):
                raise ValueError(f"{ticket_path}: expected ticket history columns: {', '.join(columns)}")
            for line, row in enumerate(reader, 2):
                if None in row or any(not value or not value.strip() for value in row.values()):
                    raise ValueError(f"{ticket_path}:{line}: incomplete or malformed ticket history row")
                ticket = {field: row[column].strip() for column, field in columns.items()}
                number = ticket["number"]
                if not number.isascii() or not number.isdigit() or number in tickets:
                    raise ValueError(f"{ticket_path}:{line}: invalid or duplicate ticket number {number!r}")
                tickets[number] = ticket

    for activity in data["activities"]:
        label = activity["id"]
        record = activity["record"]
        if "ticket_numbers" in record:
            if "ticket_history_file" not in data["project"]:
                raise ValueError(f"{path}: {label} ticket_numbers require project.ticket_history_file")
            require_refs(record["ticket_numbers"], tickets, f"{label} ticket history")
            record["tickets"] = [tickets[number] for number in record.pop("ticket_numbers")]
        require_refs([activity["phase"]], indexes["phases"], label)
        require_refs([activity["owner"], *activity["contributors"]], indexes["roles"], label)
        require_refs(activity["services"], indexes["services"], label)
        require_refs(activity["depends_on"], indexes["activities"], label)
        children = activity["subprocesses"]
        if len({child["id"] for child in children}) != len(children):
            raise ValueError(f"{path}: duplicate subprocess IDs in {label}")
    for collection, order in (
        ("phases", "phase_order"), ("roles", "role_order"), ("services", "service_order")
    ):
        if set(data["layout"][order]) != set(indexes[collection]):
            raise ValueError(f"{path}: {order} must list every {collection} ID exactly once")

    visiting, visited = set(), set()

    def visit(activity_id):
        if activity_id in visiting:
            raise ValueError(f"{path}: dependency cycle at {activity_id}")
        if activity_id in visited:
            return
        visiting.add(activity_id)
        for predecessor in indexes["activities"][activity_id]["depends_on"]:
            visit(predecessor)
        visiting.remove(activity_id)
        visited.add(activity_id)

    for activity_id in indexes["activities"]:
        visit(activity_id)
    ranks = {phase: rank for rank, phase in enumerate(data["layout"]["phase_order"])}
    for activity in data["activities"]:
        for predecessor in activity["depends_on"]:
            if ranks[indexes["activities"][predecessor]["phase"]] > ranks[activity["phase"]]:
                raise ValueError(f"{path}: layout reverses dependency {predecessor} -> {activity['id']}")
    for phase in indexes["phases"]:
        if not any(activity["phase"] == phase for activity in data["activities"]):
            raise ValueError(f"{path}: empty phase {phase}")

    inventory_evidence = {}
    for observation in observations:
        require_refs(observation["activities"], indexes["activities"], observation["id"])
        require_refs([observation["source"]], sources, observation["id"])
        binding = observation.get("inventory")
        if binding:
            root = inputs_dir.resolve()
            inventory_path = (root / binding["file"]).resolve()
            if not inventory_path.is_relative_to(root):
                raise ValueError(f"{path}: inventory reference escapes ea_inputs")
            inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
            artifacts = {artifact["id"]: artifact for artifact in inventory["artifacts"]}
            require_refs(binding["artifact_ids"], artifacts, observation["id"])
            inventory_evidence[observation["id"]] = {
                "file": binding["file"],
                "environment": inventory["environment"],
                "generated_at": inventory.get("generated_at"),
                "source_commit": inventory.get("source_commit"),
                "artifacts": [
                    {
                        "id": artifacts[artifact_id]["id"],
                        "name": artifacts[artifact_id]["name"],
                        "type": artifacts[artifact_id]["type"],
                        "details": artifacts[artifact_id].get("details", []),
                    }
                    for artifact_id in binding["artifact_ids"]
                ],
            }
    data["inventory_evidence"] = inventory_evidence
    return data


def render_process(data: Dict, project: str, template_path: Path) -> str:
    payload = json.dumps(data, ensure_ascii=False, allow_nan=False).replace("&", "\\u0026")
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e")
    return Template(template_path.read_text(encoding="utf-8")).substitute(
        project=escape(project), process_data=payload
    )
