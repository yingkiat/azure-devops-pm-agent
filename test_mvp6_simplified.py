"""
MVP6 Simplified Testing
Demonstrates the correct architecture: Claude Code writes YAML directly
"""

import asyncio
import yaml
from pathlib import Path
from src.mcp_server import UnifiedMCPServer


async def test_mvp6_simplified():
    """Test MVP6 with simplified architecture - Claude Code writes YAML directly"""

    print("\n" + "="*60)
    print("MVP6 SIMPLIFIED ARCHITECTURE TEST")
    print("="*60)

    # Initialize server
    server = UnifiedMCPServer()

    # Test 1: List available elements (MCP tool - read operation)
    print("\n[TEST 1] List Available Elements (MCP Tool)")
    print("-" * 60)
    result = await server._ea_list_available_elements()
    if result['success']:
        print(f" Found {result['count']} elements")
        print(f"   Examples: {result['elements'][:3]}")

    # Test 2: Claude Code writes YAML file directly (no MCP tool needed!)
    print("\n[TEST 2] Claude Code Writes View Spec YAML Directly")
    print("-" * 60)

    # Simulate what Claude Code would do: write YAML file directly
    view_spec = {
        'view': {
            'name': 'CRM Integration View',
            'documentation': 'Shows CRM systems and their integrations',
            'viewpoint': 'application_cooperation'
        },
        'elements': {
            'include': [
                {'name': 'Microsoft Dynamics (ANZ)'},
                {'name': 'SFDC (ANZ)'},
                {'name': 'QAD EE (ANZ)'}
            ]
        },
        'relationships': {
            'include': [
                {
                    'type': ['Serving', 'Flow'],
                    'between': 'included_elements'
                }
            ]
        },
        'layout': {
            'algorithm': 'layered',
            'spacing_x': 50,
            'spacing_y': 80
        }
    }

    # Write YAML file
    specs_dir = Path("ea_inputs/views")
    specs_dir.mkdir(parents=True, exist_ok=True)

    spec_file = specs_dir / "crm_integration.yaml"
    with open(spec_file, 'w', encoding='utf-8') as f:
        yaml.dump(view_spec, f, default_flow_style=False, sort_keys=False, indent=2)

    print(f" Claude Code wrote: {spec_file}")
    print(f"   Elements: {len(view_spec['elements']['include'])}")

    # Test 3: List view specs (MCP tool - read operation)
    print("\n[TEST 3] List View Specs (MCP Tool)")
    print("-" * 60)
    result = await server._ea_list_view_specs()
    if result['success']:
        print(f" Found {result['count']} view specs:")
        for spec in result['specs']:
            print(f"   - {spec['name']} ({spec['elements_count']} elements)")

    # Test 4: Claude Code edits YAML file directly (no MCP tool needed!)
    print("\n[TEST 4] Claude Code Edits View Spec YAML Directly")
    print("-" * 60)

    # Read existing spec
    with open(spec_file, 'r', encoding='utf-8') as f:
        spec = yaml.safe_load(f)

    # Add another element
    spec['elements']['include'].append({'name': 'Tableau (AEM)'})

    # Write back
    with open(spec_file, 'w', encoding='utf-8') as f:
        yaml.dump(spec, f, default_flow_style=False, sort_keys=False, indent=2)

    print(f" Claude Code edited: {spec_file}")
    print(f"   Added element: Tableau (AEM)")
    print(f"   Total elements: {len(spec['elements']['include'])}")

    # Test 5: Generate views.csv from specs (MCP tool - generation operation)
    print("\n[TEST 5] Generate Views from Specs (MCP Tool)")
    print("-" * 60)
    result = await server._ea_generate_views_from_specs()
    if result['success']:
        print(f" Generated views.csv")
        print(f"   Views created: {result.get('views_generated', 0)}")
        print(f"   Specs processed: {result.get('specs_processed', 0)}")

    # Test 6: Verify views.csv
    print("\n[TEST 6] Verify views.csv Output")
    print("-" * 60)
    views_csv = Path("archi_inputs/views.csv")
    if views_csv.exists():
        with open(views_csv, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        print(f" views.csv created: {len(lines)} lines")

    # Summary
    print("\n" + "="*60)
    print("MVP6 SIMPLIFIED ARCHITECTURE SUMMARY")
    print("="*60)
    print("\n Correct Architecture:")
    print("   1. Claude Code reads available elements (MCP tool)")
    print("   2. Claude Code writes YAML specs directly (no MCP tool)")
    print("   3. Claude Code edits YAML specs directly (no MCP tool)")
    print("   4. Claude Code generates views.csv (MCP tool)")
    print("\n No hardcoded parsing logic")
    print(" LLM has full control over YAML content")
    print(" MCP tools only for read/generate operations")
    print("\n" + "="*60)


if __name__ == "__main__":
    asyncio.run(test_mvp6_simplified())
