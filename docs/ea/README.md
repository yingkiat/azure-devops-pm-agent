# Enterprise Architecture (EA) Tools

The EA module provides intelligent enterprise architecture analysis capabilities using AI-powered prompt-driven discovery.

## Overview

The EA discovery system extracts and analyzes enterprise architecture objects from natural language system descriptions across five standard EA layers:

- **Business Layer**: Processes, capabilities, stakeholders
- **Application Layer**: Applications, interfaces, services
- **Data Layer**: Entities, datastores, flows
- **Infrastructure Layer**: Components, environments, networks
- **Security Layer**: Controls, threats, compliance

## Quick Start

### Basic Usage

```bash
# Analyze a system description with formatted output
python -m src.cli.main ea-discover examples/system_description.txt --summary

# Save analysis to JSON file
python -m src.cli.main ea-discover system_description.txt --output results/ea_analysis.json

# Quick analysis with default output file
python -m src.cli.main ea-discover system_description.txt
```

### Example System Description

Create a text file describing your system:

```text
Customer Order Management System

The system handles order processing from initial placement through fulfillment.
Key components include:
- Web-based customer portal (React)
- Order processing API (Node.js)
- Inventory database (PostgreSQL)
- Payment gateway integration (Stripe)
- Shipping provider APIs (FedEx, UPS)

Users: Customer service reps, warehouse staff, customers
Critical requirements: 99.9% uptime, PCI compliance, real-time inventory
```

## Architecture

### System Flow

```
Text Description → EA Discovery Prompt → LLM Analysis → Structured JSON → EA Objects
```

### Key Components

- **`src/ea/ea_discovery.py`**: Main discovery engine
- **`prompts/ea/ea_discovery.md`**: Comprehensive analysis template
- **CLI Integration**: `ea-discover` command in `src/cli/main.py`

## Output Structure

### JSON Schema

```json
{
  "business": {
    "processes": [...],
    "capabilities": [...],
    "stakeholders": [...]
  },
  "application": {
    "applications": [...],
    "interfaces": [...],
    "services": [...]
  },
  "data": {
    "entities": [...],
    "datastores": [...],
    "flows": [...]
  },
  "infrastructure": {
    "components": [...],
    "environments": [...],
    "networks": [...]
  },
  "security": {
    "controls": [...],
    "threats": [...],
    "compliance": [...]
  }
}
```

### Sample Output

```text
EA DISCOVERY RESULTS
==================================================

[BUS] BUSINESS LAYER
------------------------------

* Processes:
  1. Order Processing
     Handles complete order lifecycle from placement to fulfillment

* Capabilities:
  1. Customer Self-Service
     Enables customers to place and track orders independently

[APP] APPLICATION LAYER
------------------------------

* Applications:
  1. Customer Portal
     React-based web application for customer interactions
  2. Order API
     Node.js service managing order processing logic

[DATA] DATA LAYER
------------------------------

* Entities:
  1. Order
     Represents customer purchase orders
  2. Customer
     Customer information and preferences

[INFRA] INFRASTRUCTURE LAYER
------------------------------

* Components:
  1. Web Server
     Hosts customer portal application
  2. API Server
     Runs order processing services

[SEC] SECURITY LAYER
------------------------------

* Controls:
  1. PCI Compliance
     Ensures secure payment processing
  2. Authentication
     Verifies user identity and authorization
```

## Advanced Usage

### Custom Prompts

The EA discovery uses a comprehensive prompt template at `prompts/ea/ea_discovery.md`. You can customize this template to:

- Focus on specific EA frameworks (TOGAF, Zachman, etc.)
- Add organization-specific analysis criteria
- Include compliance standards relevant to your industry
- Adjust the level of detail for different audiences

### Integration Patterns

```bash
# Pipeline example: Description → Analysis → Further Processing
python -m src.cli.main ea-discover input.txt --output analysis.json
# Then use analysis.json for diagrams, roadmaps, etc.
```

## Troubleshooting

### Common Issues

1. **"File not found" errors**: Ensure input file path is correct and accessible
2. **JSON parsing failures**: Check Azure OpenAI configuration and prompt response format
3. **Empty results**: Verify system description has sufficient detail for analysis

### Debug Mode

Enable verbose output by checking the raw LLM response:

```python
# In ea_discovery.py, uncomment debug lines to see raw AI output
print(f"Raw response: {content}")
```

### Configuration Requirements

Ensure Azure OpenAI is properly configured:

```bash
# Required environment variables
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your-api-key
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
```

## Future Enhancements

### Planned Features

- **EA Diagrams**: Generate PlantUML/Mermaid diagrams from EA objects
- **Impact Analysis**: Assess change implications across architecture layers
- **Roadmap Generation**: Create strategic modernization plans
- **Compliance Mapping**: Gap analysis against enterprise standards

### Extensibility

The prompt-driven architecture makes it easy to add new capabilities:

1. Create new prompt templates in `prompts/ea/`
2. Add corresponding analysis methods in `src/ea/`
3. Integrate with CLI in `src/cli/main.py`

## Best Practices

### Writing System Descriptions

For best results, include:

- **Business context**: Who uses the system and why
- **Technical components**: Applications, databases, integrations
- **Non-functional requirements**: Performance, security, compliance
- **Key processes**: How work flows through the system
- **Stakeholder information**: Roles and responsibilities

### Iterative Analysis

1. Start with high-level description
2. Analyze and review results
3. Add detail to areas needing more depth
4. Re-analyze for comprehensive coverage

### Output Management

- Use descriptive output filenames: `customer-portal-ea-analysis.json`
- Version control EA analysis files for change tracking
- Consider organizing by system/project: `systems/crm/ea-analysis.json`

---

For more information, see the main project documentation in `CLAUDE.md`.