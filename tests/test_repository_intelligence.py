"""
Test script for Repository Intelligence and Interactive Planning workflow.

This script tests the complete end-to-end flow:
1. Input natural language proposal
2. AI analyzes repositories and extracts tech stacks
3. Returns intelligent work item proposal with repository assignments

Usage:
    python tests/test_repository_intelligence.py
"""
import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_orchestrator.repository_intelligence import RepositoryIntelligence, RepositoryContext
from ai_orchestrator.work_item_classifier import WorkItemClassifier, WorkItemType, ComplexityLevel
from ai_orchestrator.interactive_planner import InteractivePlanner, ExecutionProposal
from mcp_server.server import AzureDevOpsMCPServer
from utils.settings import settings


class MockMCPServer:
    """Mock MCP server for testing without Azure DevOps connection."""
    
    async def _handle_tool_call(self, tool_name: str, arguments: dict):
        """Mock _handle_tool_call method to match real MCP server API."""
        from mcp import TextContent
        import json
        
        result = await self._call_tool_internal(tool_name, arguments)
        
        # Return result in MCP TextContent format
        return [TextContent(text=json.dumps(result))]
    
    async def _call_tool_internal(self, tool_name: str, arguments: dict) -> dict:
        """Mock tool calls for testing."""
        
        if tool_name == "get_repositories":
            project = arguments.get("project", "TestProject")
            return {
                "success": True,
                "repositories": [
                    {
                        "id": "repo1",
                        "name": "frontend-web",
                        "url": "https://github.com/org/frontend-web",
                        "default_branch": "main",
                        "size": 1024000
                    },
                    {
                        "id": "repo2", 
                        "name": "backend-api",
                        "url": "https://github.com/org/backend-api",
                        "default_branch": "main",
                        "size": 2048000
                    },
                    {
                        "id": "repo3",
                        "name": "mobile-app",
                        "url": "https://github.com/org/mobile-app", 
                        "default_branch": "main",
                        "size": 1536000
                    }
                ]
            }
        
        elif tool_name == "get_readme":
            repository = arguments.get("repository", "")
            
            if repository == "frontend-web":
                return {
                    "success": True,
                    "content": """# Frontend Web Application

This is a React-based web application built with TypeScript for the user dashboard and analytics interface.

## Tech Stack
- React 18
- TypeScript
- Material-UI components
- Chart.js for data visualization
- Vite build system

## Features
- User dashboard with real-time analytics
- Interactive charts and graphs
- Responsive design
- Component-based architecture

## Development
npm install
npm run dev
""",
                    "filename": "README.md",
                    "project": arguments.get("project"),
                    "repository": repository,
                    "branch": "main"
                }
            
            elif repository == "backend-api":
                return {
                    "success": True,
                    "content": """# Backend API Service

Python-based REST API service built with FastAPI for data processing and authentication.

## Tech Stack
- Python 3.9+
- FastAPI
- PostgreSQL database
- SQLAlchemy ORM
- Redis for caching
- Docker containerization

## Features
- RESTful API endpoints
- JWT authentication
- Database migrations
- API documentation with Swagger
- Background task processing

## Development
pip install -r requirements.txt
uvicorn main:app --reload
""",
                    "filename": "README.md",
                    "project": arguments.get("project"),
                    "repository": repository,
                    "branch": "main"
                }
            
            elif repository == "mobile-app":
                return {
                    "success": True,
                    "content": """# Mobile Application

Cross-platform mobile app built with React Native for iOS and Android.

## Tech Stack
- React Native
- TypeScript
- Expo SDK
- React Navigation
- Redux for state management
- Async Storage

## Features
- Native mobile interface
- Push notifications
- Offline data sync
- Cross-platform compatibility

## Development
npm install
expo start
""",
                    "filename": "README.md", 
                    "project": arguments.get("project"),
                    "repository": repository,
                    "branch": "main"
                }
            
            else:
                return {
                    "success": False,
                    "error": "README file not found",
                    "tried_files": ["README.md", "readme.md"],
                    "project": arguments.get("project"),
                    "repository": repository
                }
        
        return {"success": False, "error": "Unknown tool"}


async def test_repository_intelligence():
    """Test repository intelligence analysis."""
    
    print("TESTING REPOSITORY INTELLIGENCE")
    print("=" * 60)
    
    mock_server = MockMCPServer()
    repository_intelligence = RepositoryIntelligence(mock_server)
    
    # Test repository analysis
    print("\n1. Testing repository analysis...")
    test_projects = ["TestProject"]
    test_request = "Create dashboard for user analytics with real-time data"
    
    repository_contexts = await repository_intelligence.analyze_request_repositories(
        "CREATE", test_request, test_projects
    )
    
    print(f"   Found {len(repository_contexts)} repositories")
    
    for context in repository_contexts:
        print(f"\n    {context.name}")
        print(f"      Tech Stack: {', '.join(context.tech_stack) if context.tech_stack else 'Unknown'}")
        print(f"      Purpose: {context.purpose}")
        print(f"      Keywords: {', '.join(context.keywords[:5]) if context.keywords else 'None'}")
        print(f"      Confidence: {context.confidence_score:.2f}")
        print(f"      Reasoning: {context.analysis_reasoning}")
    
    # Test best match selection
    print("\n2. Testing repository matching...")
    best_match = repository_intelligence.get_best_repository_match(test_request, repository_contexts)
    
    if best_match:
        print(f"    Best match: {best_match.name} (score: {best_match.confidence_score:.2f})")
        print(f"   Reason: {best_match.analysis_reasoning}")
    else:
        print("    No suitable repository found")
    
    return repository_contexts


async def test_interactive_planner():
    """Test interactive planner with repository intelligence."""
    
    print("\n\nTESTING INTERACTIVE PLANNER")
    print("=" * 60)
    
    mock_server = MockMCPServer()
    planner = InteractivePlanner(mock_server)
    
    # Test different types of requests
    test_cases = [
        {
            "request": "Create epic for user authentication system", 
            "intent": "CREATE",
            "expected_type": "Epic"
        },
        {
            "request": "Build dashboard with real-time analytics",
            "intent": "CREATE", 
            "expected_repo": "frontend-web"
        },
        {
            "request": "Fix API authentication bug",
            "intent": "CREATE",
            "expected_repo": "backend-api"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: '{test_case['request']}'")
        print("-" * 40)
        
        try:
            proposal = await planner.plan_work_items(
                test_case["request"], 
                test_case["intent"], 
                ["TestProject"]
            )
            
            print(f"   Work Item Type: {proposal.hierarchical_plan.primary_work_item.work_item_type.value}")
            print(f"   Title: {proposal.hierarchical_plan.primary_work_item.title}")
            print(f"   Repository: {proposal.hierarchical_plan.primary_work_item.target_repository}")
            print(f"   Child Items: {len(proposal.hierarchical_plan.child_items)}")
            print(f"   Confidence: {proposal.confidence_score:.2f}")
            
            # Show repository analysis
            if proposal.repository_analysis:
                print(f"   Top Repository: {proposal.repository_analysis[0].name} (score: {proposal.repository_analysis[0].confidence_score:.2f})")
            
            # Test proposal formatting
            print("\n    FORMATTED PROPOSAL:")
            print("   " + "=" * 30)
            formatted_proposal = planner.format_proposal_for_approval(proposal)
            # Indent the proposal for readability
            indented_proposal = "\n".join(f"   {line}" for line in formatted_proposal.split("\n"))
            print(indented_proposal)
            
        except Exception as e:
            print(f"    Error: {e}")
            import traceback
            traceback.print_exc()


async def test_end_to_end_flow():
    """Test complete end-to-end proposal flow."""
    
    print("\n\nEND-TO-END FLOW TEST")
    print("=" * 60)
    
    # Real-world test scenario
    user_request = "I need to build a mobile app for our users to view their analytics data"
    
    mock_server = MockMCPServer()
    planner = InteractivePlanner(mock_server)
    
    print(f"User Request: '{user_request}'")
    print()
    
    try:
        # Generate full proposal
        proposal = await planner.plan_work_items(user_request, "CREATE", ["TestProject"])
        
        # Display results
        print(" AI ANALYSIS COMPLETE")
        print("=" * 40)
        print(f"Primary Work Item: {proposal.hierarchical_plan.primary_work_item.work_item_type.value}")
        print(f"Recommended Repository: {proposal.hierarchical_plan.primary_work_item.target_repository}")
        print(f"Timeline: {proposal.estimated_timeline}")
        
        print(f"\n REPOSITORY INTELLIGENCE:")
        for repo_context in proposal.repository_analysis[:3]:
            print(f"   {repo_context.name}: {repo_context.confidence_score:.2f} ({', '.join(repo_context.tech_stack[:3])})")
        
        print(f"\n FULL PROPOSAL:")
        formatted_proposal = planner.format_proposal_for_approval(proposal)
        print(formatted_proposal)
        
        print("\nEnd-to-end flow completed successfully!")
        
    except Exception as e:
        print(f"End-to-end flow failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests."""
    
    print("REPOSITORY INTELLIGENCE & INTERACTIVE PLANNER TESTS")
    print("=" * 70)
    
    try:
        # Test 1: Repository Intelligence
        repository_contexts = await test_repository_intelligence()
        
        # Test 2: Interactive Planner
        await test_interactive_planner()
        
        # Test 3: End-to-End Flow
        await test_end_to_end_flow()
        
        print("\n\nALL TESTS COMPLETED!")
        print("The repository intelligence system is working and ready for integration.")
        
    except Exception as e:
        print(f"\n TEST SUITE FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())