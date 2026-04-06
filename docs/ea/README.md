# Enterprise Architecture (EA) Agent

AI-powered enterprise architecture discovery and diagram generation, integrated with Claude Code via MCP (Model Context Protocol).

## What It Does

1. **Discovers EA objects** from natural language system descriptions
2. **Generates ArchiMate models** (CSV/XML) for import into Archi tool
3. **Creates draw.io diagrams** with intelligent layout
4. **Supports relationship-based views** (capabilities with their applications)

## Quick Start

### Prerequisites

```bash
# Install dependencies
pip install -e .

# Configure environment (.env file)
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com
AZURE_OPENAI_KEY=your-key
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

### Basic Workflow

```
1. Put system descriptions in ea_inputs/*.txt
2. Run: ea_discover_directory()
3. Output: archi_inputs/model.xml (import into Archi)
4. Create YAML view spec in ea_inputs/views/
5. Run: `python -m src.cli.main ea-view ea_inputs/views/myview.yaml`
6. Output: ea_diagrams/myview.drawio (open in draw.io)
```

## Architecture

```
ea_inputs/                  # Your input files
├── 01_company_context/     # Company background
├── 02_IT_systems/          # System descriptions (*.txt)
└── views/                  # View specifications (*.yaml)

archi_inputs/               # Generated ArchiMate model
├── elements.csv            # Applications, Capabilities, etc.
├── relations.csv           # Serving, Flow, Composition
├── properties.csv          # Region, Domain, Lifecycle Status
└── model.xml               # Complete model for Archi import

ea_diagrams/                # Generated diagrams
└── *.drawio                # Open in draw.io
```

## MCP Tools

All interaction is via Claude Code MCP interface. Available tools:

| Tool | Purpose |
|------|---------|
| `ea_discover_directory` | Process all files in ea_inputs/, generate model |
| `ea_discover` | Process single text, add to model |
| `ea_get_data_summary` | Show current model statistics |
| `ea_generate_diagram` | MCP tool for generating draw.io from YAML view spec |
| `ea_generate_views_from_specs` | Generate views.csv from all YAML specs |

## View Specifications (YAML)

Views define what to show and how to organize it.

### Basic View (Group by Property)

```yaml
view:
  name: "Operations Applications"

elements:
  include:
    - where:
        type: "ApplicationComponent"
        Domain: "Operations"

grouping:
  by_property: "Region"
  order: ["ANZ", "JPN", "AEM"]

layout:
  algorithm: grid
  columns: 4

output:
  format: drawio
```

### Advanced View (Relationship-Based Structure)

Show capabilities with their supporting applications:

```yaml
view:
  name: "Capability Realization Map"

elements:
  include:
    - where:
        type: "Capability"
        Domain: ["Operations", "IT Security"]

# NEW: Parent-child via relationships
structure:
  parent:
    type: "Capability"
  children:
    type: "ApplicationComponent"
    via: "Serving"
    direction: "inbound"    # Apps point TO capabilities
  layout: column

# Group the parent containers
grouping:
  by_property: "Domain"

# Add text labels
annotations:
  - text: "Strategic"
    near: "UDW Agent"
  - text: "Sunset 2025"
    near: "Legacy System"

output:
  format: drawio
```

### YAML Schema Reference

| Section | Purpose |
|---------|---------|
| `view` | Name and documentation |
| `elements` | What to include (WHERE clauses) |
| `structure` | Parent-child hierarchy via relationships |
| `grouping` | How to group elements (by property) |
| `annotations` | Text labels near elements |
| `layout` | Layout algorithm and spacing |
| `output` | Output format (drawio, archi, both) |

For `layout.text_boxes`, use source-level placement rules:
- Keep short labels close to the relevant stage or section.
- Put long notes such as principles, assumptions, and explanatory text at the bottom center of the diagram.
- Prefer plain multiline text over HTML bullet lists for long callouts.
- Prefer `kind: stacked_lines` when a note needs one header box plus multiple equal-width statement rows.

## ArchiMate Types

The system uses standard ArchiMate 3.0 types:

| Layer | Types |
|-------|-------|
| Strategy | Capability, Resource, CourseOfAction |
| Business | BusinessProcess, BusinessFunction, BusinessService |
| Application | ApplicationComponent, ApplicationService, DataObject |
| Technology | Node, Device, SystemSoftware, TechnologyService |

### Relationships

| Type | Meaning |
|------|---------|
| Serving | Source provides functionality to Target |
| Flow | Data/material flows from Source to Target |
| Composition | Source is composed of Target |
| Realization | Source realizes/implements Target |

## Diagram Generation

### How It Works

```
YAML Spec → Element Selection → Relationship Filtering → Layout → draw.io XML
```

### CLI Command

Generate a draw.io diagram from a YAML view spec with:

```bash
python -m src.cli.main ea-view ea_inputs/views/myview.yaml
```

Optionally rebuild the portal at the same time:

```bash
python -m src.cli.main ea-view ea_inputs/views/myview.yaml --portal
```

1. **Element Selection**: WHERE clauses filter elements.csv
2. **Structure Building**: Find children via relationships (if specified)
3. **Grouping**: Organize into containers by property
4. **Layout**: AI or fallback deterministic layout
5. **Rendering**: Generate draw.io XML with colors, edges, annotations

### Color Coding

Elements are colored by:
- **Lifecycle Status** (if color_by specified):
  - Green (#81C784) = Strategic
  - Orange (#FFB74D) = Maintain
  - Red (#E57373) = Sunset
  - Blue (#64B5F6) = New

- **ArchiMate Layer** (default):
  - Yellow (#F5DEAA) = Strategy (Capabilities)
  - Light Blue (#B5D4E8) = Application
  - Green (#C9E7CB) = Technology

### Diagram Features

- **Swimlane containers** for groups
- **Relationship edges** with ArchiMate-style arrows
- **Annotations** as small text labels
- **Narrative textbox** with summary statistics

## Draw.io Generator Maintenance

For current guidance on maintaining the generator without rewriting it, see:

- [DRAWIO_GENERATOR_MAINTENANCE.md](DRAWIO_GENERATOR_MAINTENANCE.md)
- [AZURE_DIAGRAM_MODE_PLANNING.md](AZURE_DIAGRAM_MODE_PLANNING.md)

This note captures the agreed position that:

- the current generator is tangled but still viable
- common diagramming rules are generic, not diagram-specific hacks
- behavior-preserving incremental detangling is preferred over a rewrite
- visual behavior changes and structural refactors should be committed separately

The Azure planning note adds a separate `azure_diagram` mode for Azure-native solution diagrams
that should be implemented beside the current EA-oriented generator rather than inside it.

## Example Outputs

### Narrative Textbox

```
📊 Capability Realization Map

Elements: 28 | Relationships: 27

Groups:
  • Operations: 17 elements
  • IT Security: 3 elements
  • Business Intelligence: 5 elements

Lifecycle Status:
  • Strategic: 2 systems
  • Maintain: 2 systems

Relationships:
  • Serving: 25 connections
  • Composition: 2 connections
```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "No elements selected" | Check WHERE clause matches properties.csv values |
| AI layout truncates | >15 elements uses fallback (by design) |
| Duplicate edge IDs | Fixed in latest version |
| Missing annotations | Element name must match (partial match supported) |

### Debug Tips

```python
# Check what elements exist
from src.ea.diagram_generator import DiagramGenerator
gen = DiagramGenerator()
print([e['name'] for e in gen.elements if e['type'] == 'Capability'])

# Check properties
print([p for p in gen.properties if p['key'] == 'Domain'])
```

## File Reference

| File | Purpose |
|------|---------|
| `src/ea/diagram_generator.py` | Main diagram generation |
| `src/ea/view_builder.py` | YAML spec parsing |
| `src/ea/drawio_export.py` | Draw.io XML generation |
| `src/ea/ea_discovery.py` | Text → ArchiMate extraction |
| `prompts/ea/drawio_diagram_layout.md` | AI layout prompt |
| `prompts/ea/ea_discovery.md` | EA extraction prompt |

## Version History

| Version | Features |
|---------|----------|
| MVP1-5 | EA discovery, Mermaid diagrams, context awareness |
| MVP6 | YAML view specs, deterministic views |
| MVP7 | AI-driven layout, draw.io export |
| MVP8 | ArchiMate colors, relationship styles, dynamic sizing |
| MVP8.1 | Structure hierarchy, annotations, fallback improvements |

## Integration with Archi

1. Generate model: `ea_discover_directory()`
2. Open Archi tool
3. File → Import → Open Exchange File
4. Select `archi_inputs/model.xml`
5. View imported elements and relationships

---

For project-level documentation, see `CLAUDE.md` in the project root.
