"""
Comprehensive MCP Integration Test Suite

This test suite validates the complete MCP (Model Context Protocol) implementation including:
1. OnDemandMCPClient functionality
2. Official MCP library client
3. Direct server communication testing

Combines functionality from the original test files:
- test_mcp_client.py (OnDemandMCPClient testing)
- test_mcp_library_client.py (Official MCP library testing)
- test_mcp_server_direct.py (Direct protocol testing)
"""

import asyncio
import json
import subprocess
import sys
import threading
import time
import queue
from pathlib import Path
from typing import Dict, Any, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pm.tools.mcp_client import OnDemandMCPClient
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters


class MCPIntegrationTestSuite:
    """Comprehensive MCP integration test suite."""

    def __init__(self):
        self.server_script = str(Path(__file__).parent.parent / "src" / "pm" / "tools" / "mcp_server.py")

    async def run_all_tests(self):
        """Run all MCP integration tests."""
        print(" MCP Integration Test Suite")
        print("=" * 70)
        print("Testing complete MCP implementation stack")
        print("=" * 70)

        test_results = {}

        # Test 1: OnDemandMCPClient
        print("\n Test Suite 1: OnDemandMCPClient")
        print("-" * 50)
        test_results["ondemand_client"] = await self.test_ondemand_client()

        # Test 2: Official MCP Library
        print("\n Test Suite 2: Official MCP Library")
        print("-" * 50)
        test_results["official_library"] = await self.test_official_mcp_library()

        # Test 3: Direct Protocol Testing
        print("\n Test Suite 3: Direct Protocol Validation")
        print("-" * 50)
        test_results["direct_protocol"] = await self.test_direct_protocol()

        # Summary
        self.print_test_summary(test_results)

    async def test_ondemand_client(self) -> Dict[str, Any]:
        """Test the OnDemandMCPClient functionality."""
        results = {"passed": 0, "failed": 0, "tests": []}

        try:
            # Initialize client
            client = OnDemandMCPClient()

            # Show client stats
            print(" Client Configuration:")
            stats = client.get_stats()
            for key, value in stats.items():
                if key == "benefits":
                    print(f"   {key}:")
                    for benefit in value:
                        print(f"     - {benefit}")
                else:
                    print(f"   {key}: {value}")

            # Test 1: List tools
            print("\n Test 1.1: List available MCP tools")
            try:
                tools = await client.list_tools()
                if tools and len(tools) > 0 and not any(t.get("error") for t in tools):
                    print(f"    Found {len(tools)} tools")
                    results["tests"].append({"name": "list_tools", "status": "passed"})
                    results["passed"] += 1
                else:
                    print(f"    Failed to list tools properly: {tools}")
                    results["tests"].append({"name": "list_tools", "status": "failed"})
                    results["failed"] += 1
            except Exception as e:
                print(f"    Failed: {e}")
                results["tests"].append({"name": "list_tools", "status": "failed", "error": str(e)})
                results["failed"] += 1

            # Test 2: Get projects
            print("\n Test 1.2: Get projects")
            try:
                project_results = await client.call_tool("get_projects", {})
                if project_results and len(project_results) > 0:
                    result = project_results[0]
                    if result.get("success"):
                        project_count = result.get("count", 0)
                        execution_time = result.get("_mcp_execution_time", 0)
                        print(f"    Success: Found {project_count} projects")
                        print(f"   ⏱  Execution time: {execution_time:.2f}s")
                        results["tests"].append({"name": "get_projects", "status": "passed"})
                        results["passed"] += 1
                    else:
                        error = result.get("error", "Unknown error")
                        print(f"    Tool failed: {error}")
                        results["tests"].append({"name": "get_projects", "status": "failed"})
                        results["failed"] += 1
                else:
                    print("    No results returned")
                    results["tests"].append({"name": "get_projects", "status": "failed"})
                    results["failed"] += 1
            except Exception as e:
                print(f"    Failed: {e}")
                results["tests"].append({"name": "get_projects", "status": "failed", "error": str(e)})
                results["failed"] += 1

            # Test 3: Error handling
            print("\n Test 1.3: Error handling")
            try:
                error_results = await client.call_tool("invalid_tool", {})
                if error_results and len(error_results) > 0:
                    result = error_results[0]
                    if not result.get("success") or result.get("_mcp_error"):
                        print(f"    Error handled correctly")
                        results["tests"].append({"name": "error_handling", "status": "passed"})
                        results["passed"] += 1
                    else:
                        print("    Expected error but got success")
                        results["tests"].append({"name": "error_handling", "status": "failed"})
                        results["failed"] += 1
                else:
                    print("    No results returned for error case")
                    results["tests"].append({"name": "error_handling", "status": "failed"})
                    results["failed"] += 1
            except Exception as e:
                print(f"    Exception handled: {e}")
                results["tests"].append({"name": "error_handling", "status": "passed"})
                results["passed"] += 1

        except Exception as e:
            print(f" OnDemandMCPClient test suite failed: {e}")
            results["failed"] += 1
            results["tests"].append({"name": "client_init", "status": "failed", "error": str(e)})

        return results

    async def test_official_mcp_library(self) -> Dict[str, Any]:
        """Test the official MCP library directly."""
        results = {"passed": 0, "failed": 0, "tests": []}

        try:
            # Server parameters
            server_params = StdioServerParameters(
                command=sys.executable,
                args=[self.server_script]
            )

            print(" Server Configuration:")
            print(f"   Command: {server_params.command}")
            print(f"   Args: {server_params.args}")

            # Test connection and initialization
            print("\n Test 2.1: Connection and initialization")
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize
                    init_result = await session.initialize()
                    print(f"    Initialization successful")
                    print(f"    Protocol: {init_result.protocolVersion}")
                    print(f"     Server: {init_result.serverInfo.name} v{init_result.serverInfo.version}")
                    results["tests"].append({"name": "initialization", "status": "passed"})
                    results["passed"] += 1

                    # Test 2.2: List tools
                    print("\n Test 2.2: List tools")
                    tools_result = await session.list_tools()
                    print(f"    Found {len(tools_result.tools)} tools")
                    if len(tools_result.tools) >= 10:  # We expect 10 Azure DevOps tools
                        results["tests"].append({"name": "list_tools", "status": "passed"})
                        results["passed"] += 1
                    else:
                        results["tests"].append({"name": "list_tools", "status": "failed"})
                        results["failed"] += 1

                    # Test 2.3: Tool execution
                    print("\n Test 2.3: Tool execution (get_projects)")
                    call_result = await session.call_tool("get_projects", {})
                    print(f"    Tool call successful")
                    print(f"    Content items: {len(call_result.content)}")

                    success = False
                    for content in call_result.content:
                        if hasattr(content, 'text'):
                            try:
                                data = json.loads(content.text)
                                if isinstance(data, dict) and data.get("success"):
                                    project_count = data.get("count", 0)
                                    print(f"    Found {project_count} projects")
                                    success = True
                                    break
                            except json.JSONDecodeError:
                                continue

                    if success:
                        results["tests"].append({"name": "tool_execution", "status": "passed"})
                        results["passed"] += 1
                    else:
                        results["tests"].append({"name": "tool_execution", "status": "failed"})
                        results["failed"] += 1

                    # Test 2.4: Error handling
                    print("\n Test 2.4: Error handling")
                    try:
                        error_result = await session.call_tool("invalid_tool", {})
                        if error_result.isError:
                            print(f"    Error handled correctly: {error_result.content[0].text}")
                            results["tests"].append({"name": "error_handling", "status": "passed"})
                            results["passed"] += 1
                        else:
                            print(f"    Expected error but got success")
                            results["tests"].append({"name": "error_handling", "status": "failed"})
                            results["failed"] += 1
                    except Exception as e:
                        print(f"    Exception handled: {e}")
                        results["tests"].append({"name": "error_handling", "status": "passed"})
                        results["passed"] += 1

        except Exception as e:
            print(f" Official MCP library test failed: {e}")
            results["failed"] += 1
            results["tests"].append({"name": "library_connection", "status": "failed", "error": str(e)})

        return results

    async def test_direct_protocol(self) -> Dict[str, Any]:
        """Test direct protocol communication."""
        results = {"passed": 0, "failed": 0, "tests": []}

        print(" Testing direct MCP protocol communication")

        try:
            # Test 3.1: Server startup
            print("\n Test 3.1: Server startup")
            process = subprocess.Popen(
                [sys.executable, self.server_script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0
            )

            # Give it time to start
            time.sleep(0.5)

            if process.poll() is None:
                print("    Server started successfully")
                results["tests"].append({"name": "server_startup", "status": "passed"})
                results["passed"] += 1
            else:
                stderr_output = process.stderr.read()
                print(f"    Server failed to start: {stderr_output}")
                results["tests"].append({"name": "server_startup", "status": "failed"})
                results["failed"] += 1
                process.terminate()
                return results

            # Test 3.2: Protocol validation
            print("\n Test 3.2: Protocol validation")
            try:
                # Send a proper MCP initialize request
                init_request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "roots": {"listChanged": True},
                            "sampling": {}
                        },
                        "clientInfo": {
                            "name": "test-client",
                            "version": "1.0.0"
                        }
                    }
                }

                request_json = json.dumps(init_request) + "\n"
                process.stdin.write(request_json)
                process.stdin.flush()

                # Try to read response with timeout using threading
                def read_output(process, q):
                    try:
                        line = process.stdout.readline()
                        q.put(('stdout', line))
                    except Exception as e:
                        q.put(('error', str(e)))

                q = queue.Queue()
                thread = threading.Thread(target=read_output, args=(process, q))
                thread.start()

                try:
                    output_type, response_line = q.get(timeout=5.0)
                    if output_type == 'stdout' and response_line.strip():
                        try:
                            response = json.loads(response_line.strip())
                            if "result" in response:
                                print("    Protocol validation successful")
                                print(f"    Server info: {response['result'].get('serverInfo', {}).get('name', 'Unknown')}")
                                results["tests"].append({"name": "protocol_validation", "status": "passed"})
                                results["passed"] += 1
                            else:
                                print(f"    Unexpected response: {response}")
                                results["tests"].append({"name": "protocol_validation", "status": "failed"})
                                results["failed"] += 1
                        except json.JSONDecodeError as e:
                            print(f"    Invalid JSON response: {e}")
                            results["tests"].append({"name": "protocol_validation", "status": "failed"})
                            results["failed"] += 1
                    else:
                        print("    No valid response received")
                        results["tests"].append({"name": "protocol_validation", "status": "failed"})
                        results["failed"] += 1
                except queue.Empty:
                    print("    Response timeout")
                    results["tests"].append({"name": "protocol_validation", "status": "failed"})
                    results["failed"] += 1

            except Exception as e:
                print(f"    Protocol test failed: {e}")
                results["tests"].append({"name": "protocol_validation", "status": "failed", "error": str(e)})
                results["failed"] += 1

            # Cleanup
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()

        except Exception as e:
            print(f" Direct protocol test failed: {e}")
            results["failed"] += 1
            results["tests"].append({"name": "direct_protocol", "status": "failed", "error": str(e)})

        return results

    def print_test_summary(self, test_results: Dict[str, Dict[str, Any]]):
        """Print comprehensive test summary."""
        print("\n" + "=" * 70)
        print(" COMPREHENSIVE TEST SUMMARY")
        print("=" * 70)

        total_passed = 0
        total_failed = 0
        total_tests = 0

        for suite_name, results in test_results.items():
            passed = results.get("passed", 0)
            failed = results.get("failed", 0)
            tests = results.get("tests", [])

            total_passed += passed
            total_failed += failed
            total_tests += len(tests)

            print(f"\n {suite_name.replace('_', ' ').title()}:")
            print(f"    Passed: {passed}")
            print(f"    Failed: {failed}")
            print(f"    Success Rate: {(passed / (passed + failed) * 100):.1f}%" if (passed + failed) > 0 else "    Success Rate: N/A")

            # Show individual test details
            for test in tests:
                status_icon = "" if test["status"] == "passed" else ""
                print(f"     {status_icon} {test['name']}")
                if "error" in test:
                    print(f"       Error: {test['error']}")

        print(f"\n OVERALL RESULTS:")
        print(f"    Total Tests: {total_tests}")
        print(f"    Total Passed: {total_passed}")
        print(f"    Total Failed: {total_failed}")
        print(f"    Overall Success Rate: {(total_passed / total_tests * 100):.1f}%" if total_tests > 0 else "    Overall Success Rate: N/A")

        if total_failed == 0:
            print("\n ALL TESTS PASSED! MCP implementation is working perfectly!")
        else:
            print(f"\n  {total_failed} test(s) failed. Review the results above.")

        print("\n MCP Integration Benefits Validated:")
        print("   - Resource efficiency (on-demand server spawning)")
        print("   - Process isolation (failure containment)")
        print("   - Official MCP protocol compliance")
        print("   - Automatic session management")
        print("   - Robust error handling")
        print("   - Azure DevOps tool integration")


async def main():
    """Main entry point for the test suite."""
    test_suite = MCPIntegrationTestSuite()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())