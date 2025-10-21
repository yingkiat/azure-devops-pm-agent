"""
Test batch discovery on ea_inputs/ folder

This will process all .txt files in ea_inputs/ and populate archi_inputs/
"""

import asyncio
from src.mcp_server import UnifiedMCPServer


async def test_batch_discovery():
    """Test batch discovery on actual ea_inputs folder."""

    print("=" * 80)
    print("BATCH DISCOVERY TEST - ea_inputs/ → archi_inputs/")
    print("=" * 80)

    # Initialize server
    server = UnifiedMCPServer()

    # Clear existing test data from archi_inputs
    print("\n  Clearing test data from archi_inputs/...")
    import shutil
    from pathlib import Path

    archi_dir = Path("archi_inputs")
    if archi_dir.exists():
        backup_dir = Path("archi_inputs_test_backup")
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        shutil.copytree(archi_dir, backup_dir)
        print(f"   Backed up to: {backup_dir}")
        shutil.rmtree(archi_dir)
        print(f"   Cleared: {archi_dir}")

    # Run batch discovery
    print("\n" + "=" * 80)
    print("RUNNING BATCH DISCOVERY")
    print("=" * 80)

    result = await server._ea_discover_directory("ea_inputs", "*.txt")

    # Display results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    if result.get("success"):
        print(f" Batch discovery completed successfully!")
        print(f"\n Directory: {result['directory']}")
        print(f" Pattern: {result['pattern']}")
        print(f" Total files found: {result['total_files']}")
        print(f" Files processed: {len(result['files_processed'])}")

        print(f"\n Aggregated Counts (sum of all discoveries):")
        agg = result['aggregated_counts']
        print(f"   Applications discovered: {agg['total_applications']}")
        print(f"   Capabilities discovered: {agg['total_capabilities']}")
        print(f"   Relationships discovered: {agg['total_relationships']}")

        if "final_model_state" in result:
            print(f"\n  Final Model State (in archi_inputs/, after deduplication):")
            final = result['final_model_state']
            print(f"   Applications: {final['applications']}")
            print(f"   Capabilities: {final['capabilities']}")
            print(f"   App-Capability Links: {final['app_capability_links']}")

        # Show per-file results
        print(f"\n Per-File Results:")
        for i, file_result in enumerate(result['files_processed'], 1):
            status_icon = "" if file_result['status'] == 'success' else ""
            print(f"\n   {i}. {status_icon} {file_result['file']}")
            if file_result['status'] == 'success':
                counts = file_result.get('counts', {})
                print(f"      Apps: {counts.get('applications', 0)}, "
                      f"Caps: {counts.get('capabilities', 0)}, "
                      f"Rels: {counts.get('relationships', 0)}")
                print(f"      {file_result.get('summary', '')}")
            else:
                print(f"      Error: {file_result.get('error', 'Unknown error')}")

        if result.get('errors'):
            print(f"\n  Errors encountered: {len(result['errors'])}")
            for error in result['errors']:
                print(f"   - {error}")

        print(f"\n SUCCESS: All files processed and merged into archi_inputs/")
        print(f"   You can now:")
        print(f"   1. Open Archi → File → Open → Model from File → archi_inputs/model.xml")
        print(f"   2. Or use ea_generate_mermaid() to create diagrams")

    else:
        print(f" Batch discovery failed!")
        print(f"   Error: {result.get('error', 'Unknown error')}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(test_batch_discovery())
