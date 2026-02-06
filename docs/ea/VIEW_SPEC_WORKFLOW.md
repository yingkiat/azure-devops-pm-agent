# View Specification Workflow

## Overview

The YAML view specification is an **iterative storyboard** - a co-working document between Claude and the user that evolves through generate-review-refine cycles.

## Three Core Principles

### 1. YAML as Iterative Storyboard

**Don't aim for perfection on the first draft.**

The normal workflow is:
1. Draft initial spec based on user intent
2. Generate diagram
3. Review output together
4. Refine spec based on what didn't work
5. Regenerate
6. Repeat until the story is right

The `iterations:` section documents this journey:

```yaml
iterations:
  - version: 1
    date: "2025-01-02"
    feedback: "SPT Applications grouped in wrong horizon"
    change: "Added Horizon override to place in H1 (AS-IS)"
  - version: 2
    date: "2025-01-02"
    feedback: "Missing annotation for legacy risk"
    change: "Added annotation about missing source code"
```

**Why this matters:**
- Diagrams tell stories; stories need refinement
- First drafts are hypotheses, not final products
- Documented iterations capture institutional knowledge

### 2. Explicit Selection Over Query Filters

**Prefer `name:` with explicit element list over `where:` property filters.**

#### Why explicit is better:

| Aspect | `where:` (Query) | `name:` (Explicit) |
|--------|------------------|-------------------|
| Reliability | Fragile - requires exact property match | Reliable - element exists or doesn't |
| Clarity | Implicit - "whatever matches" | Explicit - "these specific systems" |
| Maintainability | Hard to debug when elements disappear | Easy to verify list |
| Intent | Technical query | Business narrative |

#### When to use each:

**Use `name:` for:**
- Curated views with specific story to tell
- Transformation roadmaps (specific systems in journey)
- Executive presentations (hand-picked elements)
- Any view where you'd manually select elements

**Use `where:` for:**
- Auto-generated catalogues (all apps in a domain)
- Compliance reports (all systems with property X)
- Views that should automatically include new elements

#### Example - Explicit selection:

```yaml
elements:
  include:
    # Explicit: I know exactly which systems tell this story
    - name: "SPT Applications"
    - name: "Salesforce.com"
    - name: "Microsoft Dynamics CRM"
    - name: "Kit Management System"
```

#### Example - Query selection (use sparingly):

```yaml
elements:
  include:
    # Query: Include all, but fragile if properties change
    - where:
        type: "ApplicationComponent"
        Domain: "Commercial"
        Lifecycle Status: "Strategic"
```

### 3. View Spec = Interpretation Layer

**The view spec is where narrative diverges from raw data.**

```
Discovery (data)     →  View Spec (story)      →  Diagram (output)
─────────────────       ──────────────────        ─────────────────
"What exists"           "What to show & how"      "Visual artifact"
Source of truth         Interpretation layer      Disposable/regenerable
Don't edit for views    Iterate freely            Regenerate anytime
```

#### Why separate layers matter:

- **Data** reflects what was discovered from source documents
- **View** interprets that data for a specific audience and purpose
- Same element can appear in different horizons across different views
- Changing the story shouldn't require changing the source of truth

#### The `override:` feature:

When the story needs an element in a different group than the data suggests:

```yaml
elements:
  include:
    - name: "SPT Applications"
      override:
        Horizon: "H1"    # Data says H2, but story needs it in AS-IS
    - name: "AI Cross Reference Tool"
      override:
        Horizon: "H3"    # Data says H2, but story needs it in TO-BE
```

**Override rules:**
- Overrides are view-local - they don't change `archi_inputs/`
- Each view can override the same element differently
- Use overrides to align grouping with narrative intent
- Document why you're overriding in comments

## Workflow Phases

### Phase 1: Intent Capture

Before writing any YAML, understand:
1. What question should this diagram answer?
2. Who is the audience?
3. What decision should it enable?
4. What's the one takeaway?

### Phase 2: Data Audit

Use MCP tools to understand what exists:

```
ea_list_available_elements(element_type="ApplicationComponent")
ea_get_data_summary()
```

Read the CSV files to see property values:
- `archi_inputs/elements.csv` - what elements exist
- `archi_inputs/properties.csv` - what properties are set

**Note gaps between data and story needs.** These become overrides.

### Phase 3: Draft Spec

Write YAML with explicit element selection. Present summary:

> "Here's my interpretation: [intent summary]. The diagram will [story]. I'll emphasize [visual strategy]."

### Phase 4: Generate & Review

```
ea_generate_diagram("ea_inputs/views/my_view.yaml")
```

Review the output. Ask:
- Does this tell the story?
- Are elements in the right groups?
- What's missing or wrong?

### Phase 5: Refine

Based on review feedback:
1. Add/remove elements from explicit list
2. Add property overrides where grouping is wrong
3. Update annotations to clarify narrative
4. Document changes in `iterations:` section

### Phase 6: Regenerate

Repeat phases 4-5 until the story is right.

## Example: CRM Transformation Roadmap

### Initial Data (from discovery):

| Element | Discovered Horizon | Lifecycle Status |
|---------|-------------------|------------------|
| SPT Applications | H2 | - |
| Salesforce.com | H1 | Sunset |
| Microsoft Dynamics CRM | H3 | Strategic |

### Story Need:

SPT Applications is the legacy chain being replaced. It should be in H1 (AS-IS), not H2.

### Solution - Override in view spec:

```yaml
elements:
  include:
    - name: "SPT Applications"
      override:
        Horizon: "H1"    # Override: legacy chain is AS-IS
    - name: "Salesforce.com"    # Data correct - H1 + Sunset
    - name: "Microsoft Dynamics CRM"  # Data correct - H3 + Strategic
```

### Iteration documented:

```yaml
iterations:
  - version: 1
    date: "2025-01-02"
    feedback: "SPT Applications in H2 instead of H1 - wrong grouping"
    change: "Added Horizon override to correct story alignment"
```

## Best Practices

1. **Start explicit, add queries later** - Begin with named elements, only use queries for catalogue-style views
2. **Document every iteration** - Future you will thank present you
3. **Override rather than edit data** - Keep source of truth intact
4. **Review before sharing** - Never skip the review phase
5. **Version your specs** - Use git to track spec evolution
