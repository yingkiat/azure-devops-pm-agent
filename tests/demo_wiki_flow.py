#!/usr/bin/env python3
"""
Demo: PM Workflow with Manual Wiki Push
Realistic demonstration of natural language wiki documentation workflow.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_orchestrator.orchestrator import AzureDevOpsOrchestrator


async def demo_pm_workflow():
    """
    Realistic PM workflow:
    1. PM asks about project health
    2. Follows up with specific questions  
    3. Decides to document findings for stakeholders
    """
    print("=== PM WORKFLOW DEMO ===")
    print("Scenario: Weekly project review meeting preparation\n")
    
    orchestrator = AzureDevOpsOrchestrator()
    
    # Conversation 1: Initial project health check
    print(" PM: 'What's the overall health of our data platform project?'")
    print("   (This would normally query Azure DevOps and generate business intelligence)")
    
    # Simulate the AI learning this exchange
    orchestrator.context_manager.learn_from_interaction(
        user_request="What's the overall health of our data platform project?",
        classified_intent={'intent': 'ANALYSIS', 'confidence': 0.92, 'description': 'Project health analysis'},
        execution_result={
            'success': True,
            'execution_result': {
                'results': [
                    {
                        'step': 1,
                        'tool': 'batch_project_overview',
                        'success': True,
                        'data': {
                            'project_overviews': {
                                'Data Platform': {
                                    'health_score': 0.72,
                                    'repositories': [{'name': 'data-api'}, {'name': 'etl-pipeline'}],
                                    'work_items_summary': [
                                        {'fields': {'System.AssignedTo': 'Alice Johnson', 'System.State': 'Active'}},
                                        {'fields': {'System.AssignedTo': '', 'System.State': 'New'}}
                                    ]
                                }
                            }
                        },
                        'purpose': 'Analyze project health and team workload'
                    }
                ],
                'summary': 'Project health: 72% - Some unassigned items need attention'
            },
            'business_intelligence': {
                'executive_summary': 'Data Platform project at moderate health (0.72/1.0) with workload distribution concerns',
                'projects': [{
                    'project_name': 'Data Platform',
                    'health_score': 0.72,
                    'key_metrics': {'total_work_items': 25, 'repositories': 2, 'recent_activity': 8},
                    'recommendations': [
                        'Assign unassigned work items to reduce bottlenecks',
                        'Review sprint capacity vs. current workload'
                    ]
                }]
            }
        }
    )
    print(" AI Response: Project health 72% - moderate risk, unassigned items need attention\n")
    
    # Conversation 2: Follow-up on specific issues
    print(" PM: 'Show me the critical bugs that are blocking the release'")
    
    orchestrator.context_manager.learn_from_interaction(
        user_request="Show me the critical bugs that are blocking the release",
        classified_intent={'intent': 'QUERY', 'confidence': 0.89, 'description': 'Critical bug query for release'},
        execution_result={
            'success': True,
            'execution_result': {
                'results': [
                    {
                        'step': 1,
                        'tool': 'get_work_items',
                        'success': True,
                        'data': {
                            'count': 3,
                            'work_items': [
                                {'id': 1234, 'fields': {'System.Title': 'Authentication timeout in prod', 'System.AssignedTo': 'Bob Smith'}},
                                {'id': 1235, 'fields': {'System.Title': 'Data sync failure with external API', 'System.AssignedTo': 'Carol Lee'}},
                                {'id': 1236, 'fields': {'System.Title': 'Memory leak in ETL pipeline', 'System.AssignedTo': ''}}
                            ]
                        },
                        'purpose': 'Find release-blocking critical bugs'
                    }
                ],
                'summary': 'Found 3 critical bugs, 1 unassigned'
            }
        }
    )
    print(" AI Response: Found 3 critical bugs - 1 unassigned memory leak needs immediate attention\n")
    
    # Conversation 3: Team workload check
    print(" PM: 'Who has the highest workload right now?'")
    
    orchestrator.context_manager.learn_from_interaction(
        user_request="Who has the highest workload right now?",
        classified_intent={'intent': 'ANALYSIS', 'confidence': 0.85, 'description': 'Team workload analysis'},
        execution_result={
            'success': True,
            'execution_result': {
                'results': [
                    {
                        'step': 1,
                        'tool': 'batch_work_item_queries',
                        'success': True,
                        'data': {
                            'team_workload': {
                                'Alice Johnson': 8,
                                'Bob Smith': 12,
                                'Carol Lee': 6,
                                'Dave Wilson': 4
                            }
                        },
                        'purpose': 'Analyze current team workload distribution'
                    }
                ],
                'summary': 'Bob Smith has highest workload (12 items), Dave Wilson has capacity (4 items)'
            }
        }
    )
    print(" AI Response: Bob Smith overloaded (12 items), Dave Wilson has capacity (4 items)\n")
    
    print("=" * 60)
    print(" PM DECISION: This analysis needs to be documented for the executive meeting")
    print("\n PM: 'Save this project analysis to wiki for the executive review'")
    
    # Test the wiki save functionality
    try:
        result = await orchestrator.handle_request("Save this project analysis to wiki for the executive review")
        
        if result.get("success"):
            wiki_path = result.get("wiki_report")
            if wiki_path:
                print(f" SUCCESS: Wiki entry created at {wiki_path}")
                print(f"    Content: {len(orchestrator.context_manager.current_session_exchanges)} conversation exchanges documented")
                print(f"    Available at: Azure DevOps Wiki → {wiki_path}")
            else:
                print("  Wiki creation completed but path not returned (would work with real Azure DevOps)")
        else:
            error = result.get("error", "Unknown error")
            print(f" Wiki creation failed: {error}")
    
    except Exception as e:
        print(f"  Demo limitation: {e}")
        print("   (This would work with real Azure DevOps credentials and wiki access)")
    
    print("\n" + "=" * 60)
    print(" DEMO COMPLETE")
    print("\n What happened:")
    print("1.  PM had natural conversation about project health")
    print("2.  AI tracked all exchanges with full context") 
    print("3.  PM used natural language to request wiki documentation")
    print("4.  AI intelligently selected relevant conversation content")
    print("5.  System would create structured wiki entry for stakeholders")
    
    print(f"\n Context captured: {len(orchestrator.context_manager.current_session_exchanges)} exchanges")
    
    # Show what would be in the wiki
    content = orchestrator.context_manager.get_wiki_push_content("Save this project analysis to wiki")
    print(f" Wiki content would include {len(content)} detailed conversation exchanges")
    
    print("\n READY FOR PRODUCTION:")
    print("   python -m src.cli.ai_cli chat")
    print("    What would you like to know? [your question]")
    print("    Push this analysis to wiki")


if __name__ == "__main__":
    asyncio.run(demo_pm_workflow())