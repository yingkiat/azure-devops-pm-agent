# Property Schema Control

## Problem
LLM generates speculative fields (Confidence, Maturity, Remaining Years) that flow into properties.csv without filtering.

## Solution
`archi_inputs/property_schema.yaml` acts as an allowlist per ArchiMate type.

## How It Works

1. **ArchiExporter loads schema** on initialization via `_load_property_schema()`
2. **For each property from changes.inserts/updates**, calls `_is_property_allowed(element_type, property_key)`
3. **Only properties in the allowlist** are added to properties.csv
4. **If schema doesn't exist**, all properties allowed (backward compatible)

## Configuration

Edit `archi_inputs/property_schema.yaml`:

```yaml
ApplicationComponent:
  - Domain
  - Strategic Importance
  - Lifecycle Status
  - Rationale
  # Confidence, Maturity, Remaining Years filtered out
```

## Adding Properties

Just add to the list in property_schema.yaml - no code changes needed.
