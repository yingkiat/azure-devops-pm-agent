# EA Inputs

This directory contains input files for Enterprise Architecture (EA) discovery.

## Purpose
- **System Descriptions**: Text files containing natural language descriptions of systems, processes, or architecture changes
- **Documentation**: CSV files, Word docs, spreadsheets with EA content to analyze
- **Input Examples**: Sample files demonstrating proper format for EA discovery

## File Types
- **Text Files (.txt)**: Natural language descriptions that will be analyzed by the EA discovery system
- **CSV Files (.csv)**: Structured data with applications, capabilities, or other EA content
- **Documents (.docx, .doc)**: Business documents containing EA information
- **Spreadsheets (.xlsx, .xls)**: EA matrices or application inventories
- **Encoding**: UTF-8 recommended

## Discovery Workflow
1. **Add Content**: Place any EA-related files in this directory
2. **Run Discovery**: System analyzes ALL files in ea_inputs/ plus current working matrix
3. **Matrix Update**: Current working matrix (`data/ea_matrix.csv`) gets updated
4. **Backups**: Automatic backups saved to `data/backups/`

## Usage
```bash
# Analyze ALL files in ea_inputs/ directory
python -m src.cli.main ea-discover

# Analyze specific file plus current matrix context
python -m src.cli.main ea-discover ea_inputs/system_description.txt

# View with summary
python -m src.cli.main ea-discover ea_inputs/system_description.txt --summary

# Use specific data source
python -m src.cli.main ea-discover "new system" --data-source path/to/specific.csv
```

## Example Files
- `system_description.txt` - Sample CRM/Doc AI/ERP integration description