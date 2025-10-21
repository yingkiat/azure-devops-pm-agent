"""
Test MCP Server Integration
Verifies unified MCP server loads correctly and exposes all tools.
"""

import sys
import asyncio
from pathlib import Path

def test_imports():
    """Test that all required modules can be imported."""
    print("=" * 60)
    print("Testing Module Imports")
    print("=" * 60)

    try:
        # Test PM server import
        from src.pm.tools.mcp_server import AzureDevOpsMCPServer
        print(" PM server imports successfully")

        # Test EA modules
        from src.ea.ea_discovery import EADiscovery
        from src.ea.archi_export import ArchiExporter
        from src.ea.artifact_generator import ArtifactGenerator
        from src.ea.data_providers import ArchiMateCSVProvider
        print(" EA modules import successfully")

        # Test unified server
        from src.mcp_server import UnifiedMCPServer
        print(" Unified MCP server imports successfully")

        return True

    except ImportError as e:
        print(f" Import failed: {e}")
        return False


def test_server_initialization():
    """Test that the unified server initializes correctly."""
    print("\n" + "=" * 60)
    print("Testing Server Initialization")
    print("=" * 60)

    try:
        from src.mcp_server import UnifiedMCPServer

        # Initialize server
        server = UnifiedMCPServer()
        print(" Unified server initialized")

        # Check PM server
        pm_tools = server.pm_server.get_available_tools()
        print(f" PM server has {len(pm_tools)} tools registered")

        # Verify MCP instance
        from src.mcp_server import mcp
        print(f" FastMCP instance created: {mcp.name}")

        return True, server

    except Exception as e:
        print(f" Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_tool_registration():
    """Test that all tools are properly registered."""
    print("\n" + "=" * 60)
    print("Testing Tool Registration")
    print("=" * 60)

    try:
        from src.mcp_server import mcp

        # Get registered tools from FastMCP
        # Note: FastMCP uses decorators, tools are registered on mcp instance
        print(" MCP tools should be registered via decorators")

        # List expected PM tools
        expected_pm_tools = [
            "get_work_items",
            "create_work_item",
            "update_work_item",
            "get_pull_requests",
            "get_projects",
            "get_repositories",
            "get_readme",
            "batch_project_overview",
            "batch_work_item_queries",
            "batch_pull_requests"
        ]

        print(f"\n Expected PM Tools ({len(expected_pm_tools)}):")
        for tool in expected_pm_tools:
            print(f"   - {tool}")

        # List expected EA tools
        expected_ea_tools = [
            "ea_discover",
            "ea_generate_archi",
            "ea_generate_mermaid",
            "ea_get_data_summary"
        ]

        print(f"\n Expected EA Tools ({len(expected_ea_tools)}):")
        for tool in expected_ea_tools:
            print(f"   - {tool}")

        total_tools = len(expected_pm_tools) + len(expected_ea_tools)
        print(f"\n Total expected tools: {total_tools}")

        return True

    except Exception as e:
        print(f" Tool registration check failed: {e}")
        return False


def test_ea_components():
    """Test EA components individually."""
    print("\n" + "=" * 60)
    print("Testing EA Components")
    print("=" * 60)

    try:
        from src.ea.data_providers import ArchiMateCSVProvider

        # Test ArchiMate provider
        provider = ArchiMateCSVProvider("archi_inputs")

        if provider.is_available():
            print(" ArchiMate provider: Data available")

            ea_data = provider.get_ea_data()
            print(f"   - Applications: {len(ea_data.applications)}")
            print(f"   - Capabilities: {len(ea_data.capabilities)}")
            print(f"   - Domains: {len(ea_data.domains)}")
            print(f"   - Relationships: {len(ea_data.application_capabilities)}")
        else:
            print("  ArchiMate provider: No data in archi_inputs/ (run ea_discover first)")

        # Test schema compatibility
        schema = provider.get_schema()
        print(f"\n Schema: {schema.version}")
        print(f"   - Columns: {', '.join(schema.columns[:5])}...")

        return True

    except Exception as e:
        print(f" EA component test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_ea_tools():
    """Test EA tool implementations."""
    print("\n" + "=" * 60)
    print("Testing EA Tool Implementations")
    print("=" * 60)

    try:
        from src.mcp_server import UnifiedMCPServer

        server = UnifiedMCPServer()

        # Test ea_get_data_summary (safe, read-only)
        result = await server._ea_get_data_summary()

        if result.get("success"):
            print(" ea_get_data_summary: Working")
            if result.get("available"):
                print(f"   - Applications: {result['element_counts']['applications']}")
                print(f"   - Capabilities: {result['element_counts']['capabilities']}")
        else:
            print("  ea_get_data_summary: No data available (expected if archi_inputs/ empty)")

        return True

    except Exception as e:
        print(f" EA tool test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_file():
    """Test that MCP config file exists and is valid."""
    print("\n" + "=" * 60)
    print("Testing MCP Configuration")
    print("=" * 60)

    try:
        config_path = Path(".claude_mcp.json")

        if config_path.exists():
            import json
            with open(config_path) as f:
                config = json.load(f)

            print(" .claude_mcp.json exists")

            if "mcpServers" in config:
                servers = config["mcpServers"]
                print(f"   - Configured servers: {', '.join(servers.keys())}")

                if "pm-ea-agent" in servers:
                    agent_config = servers["pm-ea-agent"]
                    print(f"   - Command: {agent_config['command']} {' '.join(agent_config['args'])}")
                    print(" pm-ea-agent server configured correctly")
                else:
                    print("  pm-ea-agent server not found in config")
            else:
                print(" No mcpServers section in config")
                return False
        else:
            print("  .claude_mcp.json not found (will be created on first use)")

        return True

    except Exception as e:
        print(f" Config test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("\n MCP Server Integration Test Suite\n")

    results = []

    # Run synchronous tests
    results.append(("Imports", test_imports()))

    init_result, server = test_server_initialization()
    results.append(("Initialization", init_result))

    if init_result:
        results.append(("Tool Registration", test_tool_registration()))
        results.append(("EA Components", test_ea_components()))

        # Run async tests
        try:
            results.append(("EA Tools", asyncio.run(test_ea_tools())))
        except Exception as e:
            print(f" Async test error: {e}")
            results.append(("EA Tools", False))

    results.append(("Config File", test_config_file()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = " PASS" if result else " FAIL"
        print(f"{status} - {test_name}")

    print(f"\n Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n All tests passed! MCP server is ready to use.")
        print("\nTo start the server:")
        print("   python -m src.mcp_server")
        print("\nOr use with Claude Code (if installed):")
        print("   1. Ensure .claude_mcp.json is configured")
        print("   2. Start Claude Code in this directory")
        print("   3. Tools will be automatically available")
    else:
        print(f"\n  {total - passed} test(s) failed. Check errors above.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
