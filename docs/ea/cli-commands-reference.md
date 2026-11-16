# EA CLI Commands Reference

## 🎯 Overview

Complete reference for all EA-related CLI commands with practical examples and use cases.

## 📋 Command Summary

| Command | Purpose | MVP | Status |
|---------|---------|-----|--------|
| `ea-discover` | Extract EA objects from natural language | MVP1/MVP2 | ✅ Production |
| `ea-view` | Generate draw.io from a YAML view spec | MVP8/MVP9 | ✅ Production |
| `ea-diagrams` | Generate visual diagrams with Gemini Flash 2.5 | MVP3 | ✅ Production |
| `ea-artifacts` | Generate Mermaid-based diagrams (legacy) | MVP2 | ✅ Legacy Support |

---

## 🔍 EA Discovery Commands

### **`ea-discover` - Core EA Object Discovery**

**Purpose**: Extract Enterprise Architecture objects from natural language descriptions and update EA matrix.

#### **Basic Syntax**
```bash
python -m src.cli.main ea-discover <input> [options]
```

#### **Parameters**
- `<input>`: Natural language description or file path
- `--output, -o`: Output JSON file (optional)
- `--summary, -s`: Display formatted summary
- `--matrix/--no-matrix`: Update EA matrix (default: True)
- `--storage`: Storage type (csv, sqlite, azure)

#### **Examples**

##### **Text Input Discovery**
```bash
# Direct text input
python -m src.cli.main ea-discover "CRM system integrates with ERP via REST API"

# With custom output file
python -m src.cli.main ea-discover "Data pipeline processes customer data" --output customer_analysis.json

# With summary display
python -m src.cli.main ea-discover "Microservices architecture with API gateway" --summary
```

##### **File Input Discovery**
```bash
# Analyze file content
python -m src.cli.main ea-discover system_description.txt

# File input with summary
python -m src.cli.main ea-discover ea_inputs/system_description.txt --summary

# File input without matrix update (JSON only)
python -m src.cli.main ea-discover requirements.txt --no-matrix --output analysis.json
```

##### **Storage Options**
```bash
# Use SQLite storage
python -m src.cli.main ea-discover "Cloud infrastructure setup" --storage sqlite

# Use Azure storage
python -m src.cli.main ea-discover "Enterprise data warehouse" --storage azure
```

#### **Output Examples**

##### **Matrix Mode Output (Default)**
```
=== EA DISCOVERY RESULTS ===

📋 CHANGES APPLIED:
✅ Added: Customer Portal → User Authentication (maturity: 3)
✅ Added: ERP System → Order Processing (maturity: 4)
⚠️  Updated: API Gateway → Request Routing

📊 DATA EXPLORATION:
🔍 Gap Analysis: Missing security controls for payment processing
📈 Maturity Trends: Average application maturity: 3.2/5
🔄 Overlaps: Duplicate customer data validation in CRM and ERP

🎯 RECOMMENDATIONS:
   1. Implement centralized authentication service
   2. Consolidate customer data validation logic
```

##### **JSON Mode Output**
```json
{
  "business": {
    "processes": [
      {
        "name": "Order Processing",
        "description": "End-to-end order fulfillment workflow",
        "stakeholders": ["Sales", "Operations", "Finance"]
      }
    ],
    "capabilities": [
      {
        "name": "Customer Management",
        "maturity_level": "intermediate",
        "criticality": "high"
      }
    ]
  },
  "application": {
    "applications": [
      {
        "name": "CRM System",
        "type": "web",
        "criticality": "critical"
      }
    ]
  }
}
```

---

## 🎨 MVP3: Diagram Generation Commands

### **`ea-view` - Draw.io Generation from YAML View Specs**

**Purpose**: Generate a `.drawio` diagram from a YAML view spec and optionally rebuild the portal.

#### **Basic Syntax**
```bash
python -m src.cli.main ea-view <spec_path> [--portal]
```

#### **Parameters**
- `<spec_path>`: Path to YAML view spec
- `--portal / --no-portal`: Rebuild portal after generating the diagram

#### **Examples**

```bash
# Generate a draw.io diagram from a YAML view spec
python -m src.cli.main ea-view ea_inputs/views/data/data_landscape.yaml

# Generate diagram and rebuild portal
python -m src.cli.main ea-view ea_inputs/views/data/data_landscape.yaml --portal
```

#### **Output**
```text
Generating view from: ea_inputs/views/data/data_landscape.yaml
Generated: ea_diagrams\data\data_landscape.drawio
```

### **`ea-diagrams` - AI-Powered Visual Diagram Generation**

**Purpose**: Generate professional visual diagrams from EA discovery data using Gemini Flash 2.5.

#### **Basic Syntax**
```bash
python -m src.cli.main ea-diagrams <ea_file> [options]
```

#### **Parameters**
- `<ea_file>`: Path to EA analysis JSON file
- `--type, -t`: Diagram type (default: overview)
- `--output, -o`: Output file path (optional)
- `--list, -l`: List available diagram types

#### **Available Diagram Types**
- `overview` - High-level EA overview
- `business-process` - Business process flows
- `application` - Application architecture
- `data` - Data architecture and flows
- `infrastructure` - Infrastructure deployment
- `security` - Security controls and boundaries
- `integration` - System integration patterns

#### **Examples**

##### **Basic Diagram Generation**
```bash
# Generate overview diagram
python -m src.cli.main ea-diagrams ea_outputs/ea_analysis.json

# Generate specific diagram type
python -m src.cli.main ea-diagrams ea_outputs/ea_analysis.json --type application

# Generate with custom output
python -m src.cli.main ea-diagrams ea_outputs/ea_analysis.json --type data --output data_architecture.txt
```

##### **List Available Types**
```bash
# Show all supported diagram types
python -m src.cli.main ea-diagrams ea_outputs/ea_analysis.json --list
```

##### **Complete Workflow Examples**
```bash
# 1. Discover EA objects
python -m src.cli.main ea-discover "E-commerce platform with microservices"

# 2. Generate multiple diagram types
python -m src.cli.main ea-diagrams ea_outputs/ea_analysis.json --type overview
python -m src.cli.main ea-diagrams ea_outputs/ea_analysis.json --type application
python -m src.cli.main ea-diagrams ea_outputs/ea_analysis.json --type security
```

#### **Output Examples**

##### **Successful Generation**
```
Generating application diagram using Gemini Flash 2.5...
📸 Found image data: image/png
💾 Image saved to: ea_diagrams\ea-image-20250929-135610.png
📊 Image size: 1,138,793 bytes

EA DIAGRAM GENERATED
==================

Type: application
Generated: 2025-09-29 13:56:10
Output: ea_diagrams\ea-application-20250929-135610.txt

The diagram has been generated using Gemini Flash 2.5's visual capabilities.
You can view the result at: ea_diagrams\ea-application-20250929-135610.txt
```

##### **Generated Files**
```
ea_diagrams/
├── ea-application-20250929-135610.txt    # Text description
├── ea-image-20250929-135610.png          # Visual diagram (1MB+ PNG)
└── ...
```

---

## 🔧 Legacy: Artifact Generation Commands

### **`ea-artifacts` - Mermaid-Based Diagram Generation (Legacy)**

**Purpose**: Generate Mermaid-based diagrams from EA matrix data (legacy system, still supported).

#### **Basic Syntax**
```bash
python -m src.cli.main ea-artifacts [options]
```

#### **Parameters**
- `--data-source, -d`: Path to EA data source (default: data/ea/ea_entities.csv)
- `--output-dir, -o`: Output directory (default: ea_diagrams)
- `--type, -t`: Generate specific diagram type only
- `--preview, -p`: Preview available diagrams
- `--info, -i`: Show data source information
- `--separate, -s`: Generate separate files instead of combined

#### **Examples**

##### **Information and Preview**
```bash
# Show data source information
python -m src.cli.main ea-artifacts --info

# Preview available diagrams
python -m src.cli.main ea-artifacts --preview
```

##### **Diagram Generation**
```bash
# Generate all compatible diagrams (combined)
python -m src.cli.main ea-artifacts

# Generate separate files
python -m src.cli.main ea-artifacts --separate

# Generate specific diagram type
python -m src.cli.main ea-artifacts --type capability_matrix

# Custom output directory
python -m src.cli.main ea-artifacts --output-dir legacy_diagrams
```

#### **Output Examples**

##### **Preview Output**
```
EA Artifact Generation Preview

Data Source: data/ea/ea_entities.csv
Applications: 15
Capabilities: 23
Domains: 5

Available Diagrams (8):
  100 • capability_matrix - Application-Capability matrix
   90 • domain_overview - Business domain structure
   85 • application_landscape - Application portfolio view
```

---

## 🔄 Complete Workflow Examples

### **End-to-End EA Analysis Workflow**

#### **Scenario 1: New System Analysis**
```bash
# Step 1: Create system description
echo "Cloud-native e-commerce platform with microservices architecture, API gateway, and PostgreSQL database" > new_system.txt

# Step 2: Discover EA objects
python -m src.cli.main ea-discover new_system.txt --summary

# Step 3: Generate visual diagrams
python -m src.cli.main ea-diagrams ea_outputs/ea_analysis.json --type overview
python -m src.cli.main ea-diagrams ea_outputs/ea_analysis.json --type application
python -m src.cli.main ea-diagrams ea_outputs/ea_analysis.json --type data

# Step 4: Review outputs
ls ea_diagrams/
```

#### **Scenario 2: Existing System Documentation**
```bash
# Step 1: Analyze existing documentation
python -m src.cli.main ea-discover ea_inputs/system_description.txt

# Step 2: Generate comprehensive diagram set
for type in overview application data infrastructure security; do
    python -m src.cli.main ea-diagrams ea_outputs/ea_analysis.json --type $type
done

# Step 3: Generate legacy Mermaid diagrams for comparison
python -m src.cli.main ea-artifacts --output-dir mermaid_diagrams
```

#### **Scenario 3: Incremental Analysis**
```bash
# Step 1: Add new system component
python -m src.cli.main ea-discover "Payment processing service integrates with existing CRM"

# Step 2: Generate updated overview
python -m src.cli.main ea-diagrams ea_outputs/ea_analysis.json --type overview

# Step 3: Generate security diagram to review new payment component
python -m src.cli.main ea-diagrams ea_outputs/ea_analysis.json --type security
```

### **Batch Processing Workflows**

#### **Multiple File Analysis**
```bash
# Process multiple input files
for file in ea_inputs/*.txt; do
    echo "Processing $file..."
    python -m src.cli.main ea-discover "$file" --summary
done

# Generate diagrams for latest analysis
python -m src.cli.main ea-diagrams ea_outputs/ea_analysis.json --list
```

#### **Comprehensive Documentation Generation**
```bash
#!/bin/bash
# Complete EA documentation generation script

# Define analysis file
EA_FILE="ea_outputs/ea_analysis.json"

# Generate all diagram types
DIAGRAM_TYPES=("overview" "business-process" "application" "data" "infrastructure" "security" "integration")

echo "🚀 Starting comprehensive EA documentation generation..."

for type in "${DIAGRAM_TYPES[@]}"; do
    echo "📊 Generating $type diagram..."
    python -m src.cli.main ea-diagrams "$EA_FILE" --type "$type"
done

echo "✅ Documentation generation complete!"
echo "📁 Check ea_diagrams/ for all generated files"
```

---

## 🛠️ Troubleshooting & Tips

### **Common Issues**

#### **SSL Certificate Errors (Corporate Environments)**
```bash
# For CrowdStrike or corporate SSL issues
# Add to .env file:
GEMINI_DISABLE_SSL_VERIFY=true

# Test connection
python test_gemini_diagrams.py
```

#### **File Encoding Issues**
```bash
# Ensure input files are UTF-8 encoded
file --mime-encoding ea_inputs/system_description.txt

# Convert if needed (Windows)
powershell "Get-Content 'file.txt' | Set-Content -Encoding UTF8 'file_utf8.txt'"
```

#### **Missing Dependencies**
```bash
# Install required packages
pip install google-genai>=1.39.1
pip install httpx>=0.25.0
pip install certifi>=2023.0.0

# Verify installation
python -c "from google import genai; print('✅ Gemini client ready')"
```

### **Performance Tips**

#### **Large File Processing**
```bash
# For large system descriptions, use file input
python -m src.cli.main ea-discover large_system.txt --no-matrix --output analysis.json

# Then update matrix separately
python -m src.cli.main ea-discover analysis.json
```

#### **Batch Diagram Generation**
```bash
# Generate multiple diagrams efficiently
EA_FILE="ea_outputs/ea_analysis.json"
python -m src.cli.main ea-diagrams "$EA_FILE" --type overview &
python -m src.cli.main ea-diagrams "$EA_FILE" --type application &
wait  # Wait for all background jobs to complete
```

### **Environment Configuration**

#### **Required Environment Variables**
```bash
# .env file configuration
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_KEY=your-azure-openai-key
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT=your-deployment-name

# Gemini configuration (MVP3)
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.5-flash-image-preview

# Optional SSL configuration
GEMINI_DISABLE_SSL_VERIFY=true  # For corporate environments
```

---

## 📚 Additional Resources

- **MVP3 Documentation**: `docs/ea/MVP3_gemini-diagram-generation.md`
- **Features Overview**: `docs/ea/current-features-overview.md`
- **Architecture Guide**: `docs/ARCHITECTURE.md`
- **Current configuration**: [Root README](../../README.md#setup)

---

## 🎯 Quick Reference Card

### **Most Common Commands**
```bash
# Discover EA objects from text
python -m src.cli.main ea-discover "Your system description here"

# Generate overview diagram
python -m src.cli.main ea-diagrams ea_outputs/ea_analysis.json

# List available diagram types
python -m src.cli.main ea-diagrams ea_outputs/ea_analysis.json --list

# Test Gemini connection
python test_gemini_diagrams.py
```

### **File Locations**
- **Input Files**: `ea_inputs/`
- **Output JSON**: `ea_outputs/`
- **Generated Diagrams**: `ea_diagrams/`
- **EA Matrix Data**: `data/ea/`
- **Configuration**: `.env`
