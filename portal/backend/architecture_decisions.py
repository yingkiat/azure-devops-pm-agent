"""Render source-referenced architectural positions without inferring approval."""

import json
from html import escape
from pathlib import Path
from string import Template
from typing import Dict

from jsonschema import Draft202012Validator, FormatChecker


SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "ea_inputs" / "04_projects" / "_schema" / "architecture-decisions.schema.json"
)
KIND_LABELS = {
    "decision": "Decision",
    "constraint": "Constraint",
    "open_question": "Open question",
}
STATUS_LABELS = {
    "stated": "Stated in design",
    "proposed": "Proposed for endorsement",
    "open": "Open",
    "deferred": "Defined elsewhere",
}
APPROVAL_LABELS = {
    "review_candidate": "Review candidate - not Architecture-approved",
    "approved": "Source marked approved",
    "unknown": "Source approval not established",
}


def load_register(path: Path) -> Dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(data)
    ids = [entry["id"] for entry in data["entries"]]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: duplicate architecture entry IDs")
    return data


def render_register(data: Dict, project: str, template_path: Path) -> str:
    cards = []
    for entry in data["entries"]:
        search_text = " ".join([
            entry["id"], entry["title"], entry["position"],
            entry["rationale"] or "", *entry["systems"], *entry["source_sections"],
        ])
        systems = "".join(
            f'<span class="system">{escape(system)}</span>'
            for system in entry["systems"]
        )
        cards.append(
            f'<article class="entry" id="{escape(entry["id"], quote=True)}" '
            f'data-kind="{entry["kind"]}" data-status="{entry["status"]}" '
            f'data-search="{escape(search_text.lower(), quote=True)}">'
            '<div class="entry-meta">'
            f'<a class="entry-id" href="#{escape(entry["id"], quote=True)}">{escape(entry["id"])}</a>'
            f'<span class="pill">{KIND_LABELS[entry["kind"]]}</span>'
            f'<span class="pill status-{entry["status"]}">{STATUS_LABELS[entry["status"]]}</span>'
            '</div>'
            f'<h2>{escape(entry["title"])}</h2>'
            f'<p class="position">{escape(entry["position"])}</p>'
            f'<div class="systems">{systems}</div>'
            '<dl><dt>Documented rationale</dt>'
            f'<dd>{escape(entry["rationale"] or "Not stated in source.")}</dd>'
            '<dt>Source sections</dt>'
            f'<dd>{escape("; ".join(entry["source_sections"]))}</dd></dl>'
            '</article>'
        )

    source = data["source"]
    return Template(template_path.read_text(encoding="utf-8")).substitute(
        project=escape(project),
        document=escape(source["document"]),
        version=escape(source["version"]),
        source_date=escape(source["date"]),
        approval=APPROVAL_LABELS[source["approval_status"]],
        processed_at=escape(source["processed_at"]),
        sha256=escape(source["sha256"]),
        total=len(data["entries"]),
        decisions=sum(e["kind"] == "decision" for e in data["entries"]),
        constraints=sum(e["kind"] == "constraint" for e in data["entries"]),
        questions=sum(e["kind"] == "open_question" for e in data["entries"]),
        entries="\n".join(cards),
    )
