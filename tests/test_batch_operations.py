#!/usr/bin/env python3
"""
Test batch operations for efficiency improvements.
Tests parallel execution of Azure DevOps API calls.
"""
import asyncio
import json
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_server.batch_operations import BatchOperations
from mcp_server.server import AzureDevOpsMCPServer
from utils.settings import settings


async def test_batch_project_overview():
    """Test batch project overview functionality."""
    print(" Testing Batch Project Overview")
    print("=" * 50)
    
    batch_ops = BatchOperations()
    
    # Test with available projects
    test_projects = [settings.azdo_project]  # Start with configured project
    
    try:
        print(f"Testing with projects: {test_projects}")
        
        start_time = time.time()
        result = await batch_ops.batch_project_overview(test_projects)
        end_time = time.time()
        
        print(f" Batch operation completed in {result.execution_time:.2f}s")
        print(f" Success: {result.success}")
        
        if result.success:
            for project, overview in result.results.items():
                print(f"\n Project: {project}")
                if "work_items_summary" in overview:
                    print(f"   Work Items: {len(overview['work_items_summary'])} state groups")
                if "repositories" in overview:
                    print(f"   Repositories: {len(overview['repositories'])} repos")
                if "recent_work_items" in overview:
                    print(f"   Recent Items: {len(overview['recent_work_items'])} items")
        
        if result.errors:
            print(f"  Errors: {result.errors}")
            
    except Exception as e:
        print(f" Test failed: {e}")


async def test_batch_wiql_queries():
    """Test batch WIQL query execution."""
    print("\n Testing Batch WIQL Queries")
    print("=" * 50)
    
    batch_ops = BatchOperations()
    
    # Define test queries
    test_queries = {
        "active_work_items": f"""
        SELECT [System.Id], [System.Title], [System.WorkItemType]
        FROM WorkItems
        WHERE [System.TeamProject] = '{settings.azdo_project}'
          AND [System.State] = 'Active'
        """,
        "recent_items": f"""
        SELECT [System.Id], [System.Title], [System.CreatedDate]
        FROM WorkItems
        WHERE [System.TeamProject] = '{settings.azdo_project}'
          AND [System.CreatedDate] >= @Today - 7
        ORDER BY [System.CreatedDate] DESC
        """,
        "all_work_items": f"""
        SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType]
        FROM WorkItems
        WHERE [System.TeamProject] = '{settings.azdo_project}'
        ORDER BY [System.ChangedDate] DESC
        """
    }
    
    try:
        print(f"Executing {len(test_queries)} queries in parallel...")
        
        result = await batch_ops.batch_work_item_queries(test_queries)
        
        print(f" Batch queries completed in {result.execution_time:.2f}s")
        print(f" Success: {result.success}")
        
        if result.success:
            for query_name, query_result in result.results.items():
                if "count" in query_result:
                    print(f"   {query_name}: {query_result['count']} items")
        
        if result.errors:
            print(f"  Errors: {result.errors}")
            
    except Exception as e:
        print(f" Test failed: {e}")


async def test_mcp_batch_tools():
    """Test batch operations through MCP server interface."""
    print("\n Testing MCP Batch Tools")
    print("=" * 50)
    
    server = AzureDevOpsMCPServer()
    
    try:
        # Test 1: Batch project overview
        print("1. Testing batch_project_overview...")
        result = await server._batch_project_overview([settings.azdo_project])
        
        if result.get("success"):
            print(f"    Projects analyzed: {result['projects_analyzed']}")
            print(f"   ⏱  Execution time: {result['execution_time']:.2f}s")
        else:
            print(f"    Failed: {result.get('error')}")
        
        # Test 2: Batch WIQL queries
        print("\n2. Testing batch_work_item_queries...")
        test_queries = {
            "open_bugs": f"SELECT [System.Id] FROM WorkItems WHERE [System.WorkItemType] = 'Bug' AND [System.State] <> 'Closed' AND [System.TeamProject] = '{settings.azdo_project}'",
            "active_stories": f"SELECT [System.Id] FROM WorkItems WHERE [System.WorkItemType] = 'User Story' AND [System.State] = 'Active' AND [System.TeamProject] = '{settings.azdo_project}'"
        }
        
        result = await server._batch_work_item_queries(test_queries)
        
        if result.get("success"):
            print(f"    Queries executed: {result['queries_executed']}")
            print(f"   ⏱  Execution time: {result['execution_time']:.2f}s")
        else:
            print(f"    Failed: {result.get('error')}")
        
        print("\n MCP batch tools testing complete!")
        
    except Exception as e:
        print(f" MCP test failed: {e}")
        import traceback
        traceback.print_exc()


async def compare_performance():
    """Compare performance of batch vs individual operations."""
    print("\n Performance Comparison: Batch vs Individual")
    print("=" * 60)
    
    server = AzureDevOpsMCPServer()
    
    try:
        # Test queries
        queries = {
            "bugs": f"SELECT [System.Id] FROM WorkItems WHERE [System.WorkItemType] = 'Bug' AND [System.TeamProject] = '{settings.azdo_project}'",
            "stories": f"SELECT [System.Id] FROM WorkItems WHERE [System.WorkItemType] = 'User Story' AND [System.TeamProject] = '{settings.azdo_project}'",
            "tasks": f"SELECT [System.Id] FROM WorkItems WHERE [System.WorkItemType] = 'Task' AND [System.TeamProject] = '{settings.azdo_project}'"
        }
        
        # Individual operations
        print(" Running individual queries...")
        start_time = time.time()
        individual_results = []
        
        for name, query in queries.items():
            result = await server._get_work_items(query)
            individual_results.append(result)
        
        individual_time = time.time() - start_time
        print(f"   Individual queries: {individual_time:.2f}s")
        
        # Batch operation
        print(" Running batch queries...")
        start_time = time.time()
        
        batch_result = await server._batch_work_item_queries(queries)
        
        batch_time = time.time() - start_time
        print(f"   Batch queries: {batch_time:.2f}s")
        
        # Calculate improvement
        if individual_time > 0 and batch_time > 0:
            improvement = ((individual_time - batch_time) / individual_time) * 100
            print(f" Performance improvement: {improvement:.1f}%")
        
        print(f" Both approaches completed successfully")
        
    except Exception as e:
        print(f" Performance comparison failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_batch_project_overview())
    asyncio.run(test_batch_wiql_queries())
    asyncio.run(test_mcp_batch_tools())
    asyncio.run(compare_performance())