"""Summarise what changed between two infra-inventory snapshots.

Diffs by stable id/target (not by text line), so reordering produces no noise.
Output is markdown, suitable for a fold-back PR body or a CI comment.

CLI:
  python -m portal.backend.inventory_diff <new.json> [old.json]
If old.json is omitted, the previous committed version (git HEAD) is used.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ARTIFACT_FIELDS = ["name", "type", "layer", "pillar", "group", "ownership", "dependsOn", "details"]
DEPLOYMENT_FIELDS = ["image", "image_digest", "base_image", "runtime", "app_repo",
                     "app_commit", "built_at", "package", "db_migration"]


def _normalise(value):
    """Make list fields order-insensitive and stringify for stable comparison."""
    if isinstance(value, list):
        return sorted(str(v) for v in value)
    return value


def _index(items: List[dict], key: str) -> Dict[str, dict]:
    return {str(it.get(key)): it for it in items if it.get(key) is not None}


def _diff_collection(old_items: List[dict], new_items: List[dict], key: str,
                     fields: List[str]) -> Dict[str, list]:
    old_idx, new_idx = _index(old_items, key), _index(new_items, key)
    added = [new_idx[k] for k in new_idx if k not in old_idx]
    removed = [old_idx[k] for k in old_idx if k not in new_idx]
    changed = []
    for k in new_idx:
        if k not in old_idx:
            continue
        deltas = []
        for field in fields:
            ov, nv = _normalise(old_idx[k].get(field)), _normalise(new_idx[k].get(field))
            if ov != nv:
                deltas.append((field, old_idx[k].get(field), new_idx[k].get(field)))
        if deltas:
            changed.append((k, deltas))
    return {"added": added, "removed": removed, "changed": changed}


def diff_inventories(old: dict, new: dict) -> dict:
    return {
        "provenance": {
            "source_commit": (old.get("source_commit"), new.get("source_commit")),
            "generated_at": (old.get("generated_at"), new.get("generated_at")),
            "environment": (old.get("environment"), new.get("environment")),
        },
        "artifacts": _diff_collection(old.get("artifacts", []), new.get("artifacts", []),
                                       "id", ARTIFACT_FIELDS),
        "deployments": _diff_collection(old.get("deployments", []), new.get("deployments", []),
                                        "target", DEPLOYMENT_FIELDS),
    }


def _fmt(value) -> str:
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) or "(none)"
    return "(none)" if value is None else str(value)


def _render_section(title: str, key: str, section: dict) -> List[str]:
    added, removed, changed = section["added"], section["removed"], section["changed"]
    if not (added or removed or changed):
        return []
    lines = [f"**{title}**"]
    for it in added:
        label = it.get(key)
        name = it.get("name") or it.get("image_digest") or ""
        lines.append(f"+ `{label}`{(' — ' + name) if name else ''}")
    for ident, deltas in changed:
        lines.append(f"~ `{ident}`")
        for field, ov, nv in deltas:
            lines.append(f"    {field}: {_fmt(ov)} → {_fmt(nv)}")
    for it in removed:
        lines.append(f"- `{it.get(key)}`")
    lines.append("")
    return lines


def render_markdown(diff: dict, application: str = "", environment: str = "") -> str:
    prov = diff["provenance"]
    old_sha, new_sha = prov["source_commit"]
    env = environment or _fmt(prov["environment"][1])
    head = f"### {application or 'Inventory'} {env} — changes vs last published"
    if old_sha or new_sha:
        head += f" (infra {_fmt(old_sha)} → {_fmt(new_sha)})"

    body: List[str] = [head, ""]
    sections = [
        _render_section("Artifacts", "id", diff["artifacts"]),
        _render_section("Deployments", "target", diff["deployments"]),
    ]
    rendered = [line for section in sections for line in section]
    if not rendered:
        body.append("_No artifact or deployment changes._")
    else:
        body.extend(rendered)
    return "\n".join(body).rstrip() + "\n"


def load_git_version(path: Path, ref: str = "HEAD") -> Optional[dict]:
    """Load the committed version of `path` at `ref`, or None if unavailable."""
    try:
        root = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                              capture_output=True, text=True, check=True).stdout.strip()
        rel = path.resolve().relative_to(Path(root).resolve()).as_posix()
        out = subprocess.run(["git", "show", f"{ref}:{rel}"],
                             capture_output=True, text=True, check=True).stdout
        return json.loads(out)
    except (subprocess.CalledProcessError, ValueError, json.JSONDecodeError):
        return None


def _load(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(argv: Optional[List[str]] = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("usage: python -m portal.backend.inventory_diff <new.json> [old.json]")
        return 2

    new_path = Path(argv[0])
    new = _load(new_path)
    if len(argv) > 1:
        old = _load(Path(argv[1]))
    else:
        old = load_git_version(new_path)
        if old is None:
            print(f"_No previous committed version of {new_path.name}; treating all entries as new._\n")
            old = {}

    diff = diff_inventories(old, new)
    print(render_markdown(diff, application=new.get("application", ""),
                          environment=new.get("environment", "")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
