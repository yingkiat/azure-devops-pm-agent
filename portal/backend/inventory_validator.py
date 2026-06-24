"""Validate project infra-inventory JSON against the EA contract.

Two layers:
  A. Structural   - JSON Schema (ea_inputs/04_projects/_schema/infra-inventory.schema.json)
  B. Semantic     - cross-references, catalogue join, secret guard, freshness

Errors block ingest; warnings surface but do not block.
Usable from builder.py and as a CLI: `python -m portal.backend.inventory_validator <file>`.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Set

try:
    from jsonschema import Draft202012Validator
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False

SUPPORTED_VERSIONS = {"1.0"}
FRESHNESS_DAYS = 90
DEFAULT_SCHEMA_PATH = Path("ea_inputs/04_projects/_schema/infra-inventory.schema.json")
DEFAULT_CATALOGUE_JSON = Path("portal/dist/data/catalogue.json")

# Value patterns that almost always indicate a leaked secret.
_SECRET_VALUE_PATTERNS = [
    re.compile(r"password\s*=", re.I),
    re.compile(r"pwd\s*=", re.I),
    re.compile(r"accountkey\s*=", re.I),
    re.compile(r"sharedaccesskey\s*=", re.I),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]
# Key names that should never carry an inline secret value.
_SECRET_KEY_PATTERN = re.compile(r"(password|passwd|pwd|secret|access[_-]?key|sas|token|client[_-]?secret)", re.I)


class ValidationResult:
    def __init__(self, label: str = ""):
        self.label = label
        self.errors: List[str] = []
        self.warnings: List[str] = []

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def report(self) -> str:
        lines = []
        head = f"inventory '{self.label}'" if self.label else "inventory"
        if self.ok and not self.warnings:
            return f"      OK   {head}: valid, no warnings"
        for e in self.errors:
            lines.append(f"      FAIL {head}: {e}")
        for w in self.warnings:
            lines.append(f"      WARN {head}: {w}")
        return "\n".join(lines)


def _load_schema(schema_path: Optional[Path]) -> dict:
    path = schema_path or DEFAULT_SCHEMA_PATH
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_catalogue_names(catalogue_json: Optional[Path] = None) -> Optional[Set[str]]:
    """Best-effort load of Application Catalogue `name` values for the join check.

    Returns None when no catalogue source is available (check is then skipped).
    """
    path = catalogue_json or DEFAULT_CATALOGUE_JSON
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        rows = data.get("data", []) if isinstance(data, dict) else data
        names = {str(r.get("name")).strip() for r in rows if r.get("name")}
        return names or None
    except Exception:
        return None


def _scan_secrets(node, path: str, result: ValidationResult) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            child_path = f"{path}.{key}" if path else str(key)
            if isinstance(value, str):
                if _SECRET_KEY_PATTERN.search(str(key)) and value.strip() \
                        and not value.lower().startswith("https://") and "vault" not in value.lower():
                    result.warn(f"possible secret at '{child_path}' (key looks sensitive with an inline value)")
                for pat in _SECRET_VALUE_PATTERNS:
                    if pat.search(value):
                        result.warn(f"possible secret at '{child_path}' (value matches a credential pattern)")
                        break
            else:
                _scan_secrets(value, child_path, result)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            _scan_secrets(item, f"{path}[{i}]", result)


def validate_inventory(
    data: dict,
    catalogue_names: Optional[Set[str]] = None,
    schema_path: Optional[Path] = None,
    label: str = "",
) -> ValidationResult:
    result = ValidationResult(label)

    # --- Layer A: structural ---
    if JSONSCHEMA_AVAILABLE:
        schema = _load_schema(schema_path)
        for err in sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: e.path):
            loc = "/".join(str(p) for p in err.path) or "(root)"
            result.error(f"schema: {loc}: {err.message}")
        if result.errors:
            return result  # structural failure: downstream checks are unreliable
    else:
        result.warn("schema validation skipped (jsonschema not installed)")

    # --- Layer B: semantic ---
    version = str(data.get("schema_version", ""))
    if version not in SUPPORTED_VERSIONS:
        result.error(f"unsupported schema_version '{version}' (supported: {sorted(SUPPORTED_VERSIONS)})")

    artifacts = data.get("artifacts", [])
    ids: Set[str] = set()
    for art in artifacts:
        aid = art.get("id")
        if aid in ids:
            result.error(f"duplicate artifact id '{aid}'")
        ids.add(aid)
    for art in artifacts:
        for dep in art.get("dependsOn", []) or []:
            if dep not in ids:
                result.error(f"artifact '{art.get('id')}' dependsOn unknown id '{dep}'")

    deployments = data.get("deployments", []) or []
    for dep in deployments:
        target = dep.get("target")
        if target not in ids:
            result.error(f"deployment target '{target}' does not match any artifact id")

    # Identity / join
    application = data.get("application")
    if not application:
        result.warn("missing 'application' (recommended: the catalogue name this inventory binds to)")
    elif catalogue_names is not None and application not in catalogue_names:
        result.warn(f"application '{application}' not found in Application Catalogue (add the entry, "
                    f"or align the name verbatim)")

    # Provenance
    for field in ("generated_at", "source_repo", "source_commit"):
        if not data.get(field):
            result.warn(f"missing provenance field '{field}' (recommended for traceability)")

    # Build provenance
    if not deployments:
        result.warn("no 'deployments' block (recommended: image_digest/base_image/app_commit per workload)")

    # Freshness
    generated_at = data.get("generated_at")
    if generated_at:
        try:
            ts = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age_days = (datetime.now(timezone.utc) - ts).days
            if age_days > FRESHNESS_DAYS:
                result.warn(f"inventory is {age_days} days old (generated_at {generated_at}) - possible drift")
        except ValueError:
            result.warn(f"generated_at '{generated_at}' is not a valid ISO-8601 timestamp")

    # Secret guard
    _scan_secrets(data, "", result)

    return result


def validate_file(path: Path, catalogue_names: Optional[Set[str]] = None,
                  schema_path: Optional[Path] = None) -> ValidationResult:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return validate_inventory(data, catalogue_names=catalogue_names,
                              schema_path=schema_path, label=path.name)


def main(argv: Optional[List[str]] = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("usage: python -m portal.backend.inventory_validator <inventory.json> [...]")
        return 2
    catalogue_names = load_catalogue_names()
    if catalogue_names is None:
        print("      NOTE catalogue not available; skipping application join check")
    exit_code = 0
    for arg in argv:
        result = validate_file(Path(arg), catalogue_names=catalogue_names)
        print(result.report())
        if not result.ok:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
