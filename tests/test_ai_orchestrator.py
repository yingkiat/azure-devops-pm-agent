#!/usr/bin/env python3
"""
Test the complete AI orchestration system.
Tests natural language -> intent classification -> execution planning -> MCP tool execution.
"""
import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ai_orchestrator.orchestrator import AzureDevOpsOrchestrator


async def test_orchestrated_requests():
    """Test the complete orchestration pipeline with various request types."""
    print("🧠 Testing Complete AI Orchestration Pipeline")
    print("=" * 70)
    
    orchestrator = AzureDevOpsOrchestrator()
    
    # Test requests covering different intent types
    test_requests = [
        "What projects do we have?",  # DISCOVERY
        "Show me all critical bugs",  # QUERY  
        "What's in the README of the main repository?",  # DISCOVERY + README
        "How many pull requests were created last week?",  # ANALYSIS
    ]
    
    for i, request in enumerate(test_requests, 1):
        print(f"\n🧪 Test {i}/{len(test_requests)}: '{request}'")
        print("-" * 50)
        
        try:
            result = await orchestrator.handle_request(request)
            
            if result["success"]:
                print("✅ Request completed successfully!")
                
                # Show key insights from the result
                if "execution_result" in result:
                    exec_result = result["execution_result"]
                    for step_result in exec_result["results"]:
                        if step_result.get("success") and "data" in step_result:
                            data = step_result["data"]
                            tool = step_result["tool"]
                            
                            if tool == "get_projects" and "projects" in data:
                                print(f"   📁 Found {data['count']} projects")
                            elif tool == "get_work_items" and "work_items" in data:
                                print(f"   📋 Found {data['count']} work items")
                            elif tool == "get_pull_requests" and "pull_requests" in data:
                                print(f"   🔄 Found {data['count']} pull requests")
                            elif tool == "get_readme" and data.get("success"):
                                content_preview = data["content"][:100] if "content" in data else "No content"
                                print(f"   📖 README found: {content_preview}...")
                
            else:
                print(f"❌ Request failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
        
        print()  # Spacing between tests
    
    print("🎉 AI Orchestration testing complete!")
    print(f"💾 Final context: {json.dumps(orchestrator.context, indent=2)}")


async def test_individual_components():
    """Test individual orchestrator components."""
    print("\n🔧 Testing Individual Components")
    print("=" * 50)
    
    orchestrator = AzureDevOpsOrchestrator()
    test_request = "What projects do we have?"
    
    try:
        # Test 1: Intent Classification
        print("1. Testing Intent Classification...")
        classified_intent = await orchestrator.classify_intent(test_request)
        print(f"   Intent: {classified_intent.intent}")
        print(f"   Confidence: {classified_intent.confidence}")
        print(f"   Actions suggested: {len(classified_intent.suggested_actions)}")
        
        # Test 2: Execution Planning
        print("\n2. Testing Execution Planning...")
        execution_plan = await orchestrator.create_execution_plan(classified_intent, test_request)
        print(f"   Plan steps: {len(execution_plan.execution_plan)}")
        print(f"   Expected outcome: {execution_plan.expected_outcome}")
        
        # Test 3: Plan Execution
        print("\n3. Testing Plan Execution...")
        execution_result = await orchestrator.execute_plan(execution_plan)
        print(f"   Success: {execution_result.success}")
        print(f"   Summary: {execution_result.summary}")
        print(f"   Context learned: {list(execution_result.context_learned.keys())}")
        
        print("\n✅ All components working!")
        
    except Exception as e:
        print(f"❌ Component test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_individual_components())
    asyncio.run(test_orchestrated_requests())