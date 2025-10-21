#!/usr/bin/env python3
"""
Test the smart query building system.
Tests natural language parsing into WIQL queries with domain knowledge.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ai_orchestrator.query_builder import SmartWIQLBuilder, QueryContext
from ai_orchestrator.orchestrator import AzureDevOpsOrchestrator


def test_query_context_parsing():
    """Test parsing natural language into QueryContext."""
    print(" Testing Natural Language → QueryContext Parsing")
    print("=" * 60)
    
    builder = SmartWIQLBuilder()
    
    test_cases = [
        ("Show me all critical bugs assigned to John", {
            "work_item_types": ["Bug"],
            "priority_level": "critical", 
            "person": "john"
        }),
        ("What stories were created last week?", {
            "work_item_types": ["User Story"],
            "timeframe_days": 7
        }),
        ("Find high priority features for the data project", {
            "work_item_types": ["Feature"],
            "priority_level": "high"
        }),
        ("Show all open work items", {
            "states": ["New", "Active"],
            "work_item_types": ["Epic", "Feature", "User Story", "Task", "Bug"]
        })
    ]
    
    for i, (request, expected) in enumerate(test_cases, 1):
        print(f"\n Test {i}: '{request}'")
        
        context = builder.parse_natural_language_to_context(request, ["Data Platform", "Web Frontend"])
        
        print(f"   Work Item Types: {context.work_item_types}")
        print(f"   Priority Level: {context.priority_level}")
        print(f"   Person: {context.person}")
        print(f"   Timeframe: {context.timeframe_days} days")
        print(f"   States: {context.states}")
        
        # Verify key expectations
        for key, expected_value in expected.items():
            actual_value = getattr(context, key)
            if actual_value == expected_value:
                print(f"    {key}: {actual_value}")
            else:
                print(f"    {key}: expected {expected_value}, got {actual_value}")


def test_wiql_generation():
    """Test WIQL query generation from context."""
    print("\n\n  Testing WIQL Query Generation")
    print("=" * 60)
    
    builder = SmartWIQLBuilder()
    
    # Test case 1: Critical bugs
    print("\n Test 1: Critical bugs assigned to John")
    context1 = QueryContext(
        projects=["TestProject"],
        work_item_types=["Bug"],
        priority_level="critical",
        person="John",
        include_closed=False
    )
    
    query1 = builder.build_work_items_query(context1, "critical bugs assigned to John")
    print("Generated WIQL:")
    print(query1)
    
    # Test case 2: Summary query
    print("\n Test 2: Summary query for features")
    context2 = QueryContext(
        projects=["TestProject"],
        work_item_types=["Feature"]
    )
    
    summary_query = builder.build_summary_query(context2)
    print("Generated WIQL:")
    print(summary_query)
    
    # Test case 3: Team workload
    print("\n Test 3: Team workload analysis")
    workload_query = builder.build_team_workload_query(context2)
    print("Generated WIQL:")
    print(workload_query)


async def test_enhanced_orchestration():
    """Test the enhanced orchestration with smart queries."""
    print("\n\n Testing Enhanced Orchestration with Smart Queries")
    print("=" * 60)
    
    orchestrator = AzureDevOpsOrchestrator()
    
    # Add some mock context
    orchestrator.context = {
        "available_projects": ["Data Platform", "Web Frontend", "Mobile App"]
    }
    
    test_requests = [
        "Show me critical bugs in the data platform project",
        "What high priority features do we have?",
        "Find all stories assigned to Sarah from last week"
    ]
    
    for i, request in enumerate(test_requests, 1):
        print(f"\n Test {i}: '{request}'")
        
        try:
            # Test classification
            classified = await orchestrator.classify_intent(request)
            print(f"   Original confidence: {classified.confidence:.2f}")
            
            # Test enhancement  
            enhanced = await orchestrator.enhance_with_smart_queries(classified, request)
            print(f"   Enhanced confidence: {enhanced.confidence:.2f}")
            
            if enhanced.suggested_actions != classified.suggested_actions:
                print("    Queries enhanced with domain knowledge")
                for action in enhanced.suggested_actions:
                    if "wiql_query" in action.get("parameters", {}):
                        print(f"   WIQL: {action['parameters']['wiql_query'][:100]}...")
            else:
                print("    No query enhancement applied")
                
        except Exception as e:
            print(f"    Test failed: {e}")


def test_query_suggestions():
    """Test suggested queries feature."""
    print("\n\n Testing Query Suggestions")
    print("=" * 50)
    
    builder = SmartWIQLBuilder()
    
    context = QueryContext(
        projects=["TestProject"],
        timeframe_days=7
    )
    
    suggestions = builder.get_suggested_queries(context)
    
    for name, query in suggestions.items():
        print(f"\n {name.upper()}:")
        print(query)


if __name__ == "__main__":
    test_query_context_parsing()
    test_wiql_generation()
    test_query_suggestions()
    asyncio.run(test_enhanced_orchestration())