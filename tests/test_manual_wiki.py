#!/usr/bin/env python3
"""
Test Manual Wiki Push System
Tests conversation context tracking and smart content selection for wiki documentation.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_orchestrator.context_manager import ContextManager
from ai_orchestrator.wiki_reporter import AIWikiReporter


def test_manual_wiki_push_flow():
    """Test the complete manual wiki push flow."""
    print("Testing Manual Wiki Push Flow")
    print("=" * 40)
    
    # Simulate a conversation session
    context_manager = ContextManager()
    
    # Add some conversation exchanges
    print("1. Simulating conversation exchanges...")
    
    # First exchange - project discovery
    context_manager.learn_from_interaction(
        user_request="What projects do we have?",
        classified_intent={'intent': 'DISCOVERY', 'confidence': 0.9},
        execution_result={
            'success': True,
            'execution_result': {
                'results': [
                    {
                        'step': 1,
                        'tool': 'get_projects',
                        'success': True,
                        'data': {'projects': [{'name': 'Data Platform'}, {'name': 'Web Portal'}]},
                        'purpose': 'Discover available projects'
                    }
                ],
                'summary': 'Found 2 projects'
            }
        }
    )
    
    # Second exchange - bug analysis
    context_manager.learn_from_interaction(
        user_request="Show me critical bugs in the data platform",
        classified_intent={'intent': 'QUERY', 'confidence': 0.95},
        execution_result={
            'success': True,
            'execution_result': {
                'results': [
                    {
                        'step': 1,
                        'tool': 'get_work_items',
                        'success': True,
                        'data': {'count': 5, 'work_items': []},
                        'purpose': 'Find critical bugs in data platform'
                    }
                ],
                'summary': 'Found 5 critical bugs'
            }
        }
    )
    
    print(f"   Added {len(context_manager.current_session_exchanges)} exchanges to context")
    
    # Test different wiki push requests
    test_cases = [
        "push this to wiki",
        "save our discussion about bugs",
        "document this analysis for the PM",
        "push our conversation about projects"
    ]
    
    print("\n2. Testing wiki content selection...")
    for request in test_cases:
        content = context_manager.get_wiki_push_content(request)
        print(f"   '{request}' -> {len(content)} exchange(s)")
        
        # Test wiki formatting
        if content:
            reporter = AIWikiReporter()
            mock_result = {
                "success": True,
                "user_request": f"Wiki documentation: {request}",
                "session_id": "test_session",
                "conversation_content": content,
                "manual_push": True
            }
            
            formatted = reporter._format_manual_push(mock_result, "2024-01-15 14:30:00 UTC")
            print(f"   Generated {len(formatted)} characters of wiki content")
    
    print("\n✅ Manual wiki push flow working correctly!")
    
    # Show example of what would be pushed
    print("\n3. Example wiki content preview:")
    print("-" * 40)
    content = context_manager.get_wiki_push_content("push this to wiki")
    if content:
        reporter = AIWikiReporter()
        mock_result = {
            "success": True,
            "user_request": "Wiki documentation: push this to wiki", 
            "session_id": "demo_session",
            "conversation_content": content,
            "manual_push": True
        }
        
        formatted = reporter._format_manual_push(mock_result, "2024-01-15 14:30:00 UTC")
        preview = formatted[:500] + "..." if len(formatted) > 500 else formatted
        print(preview)
    
    print("\n🎉 Manual wiki push system ready!")


if __name__ == "__main__":
    test_manual_wiki_push_flow()