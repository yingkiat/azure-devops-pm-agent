#!/usr/bin/env python3
"""
Test the insights engine and business intelligence generation.
Tests data analysis, health scoring, and recommendation generation.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ai_orchestrator.insights_engine import InsightsEngine, ProjectInsight
from ai_orchestrator.orchestrator import AzureDevOpsOrchestrator


def test_work_items_analysis():
    """Test work items analysis and insights generation."""
    print("📋 Testing Work Items Analysis")
    print("=" * 50)
    
    engine = InsightsEngine()
    
    # Create test work items data
    test_work_items = [
        {
            "id": 1,
            "fields": {
                "System.Title": "Critical bug in authentication",
                "System.WorkItemType": "Bug",
                "System.State": "Active",
                "System.AssignedTo": "John Smith <john@company.com>",
                "Microsoft.VSTS.Common.Priority": "1",
                "System.ChangedDate": "2024-01-01T10:00:00Z"
            }
        },
        {
            "id": 2,
            "fields": {
                "System.Title": "Implement new dashboard",
                "System.WorkItemType": "Feature",
                "System.State": "New",
                "System.AssignedTo": "",
                "Microsoft.VSTS.Common.Priority": "3",
                "System.ChangedDate": "2024-01-15T14:30:00Z"
            }
        },
        {
            "id": 3,
            "fields": {
                "System.Title": "Update user documentation",
                "System.WorkItemType": "Task",
                "System.State": "Done",
                "System.AssignedTo": "Jane Doe",
                "Microsoft.VSTS.Common.Priority": "4",
                "System.ChangedDate": "2024-01-10T09:15:00Z"
            }
        }
    ]
    
    analysis = engine.analyze_work_items(test_work_items)
    
    print(f"✅ Analysis completed:")
    print(f"   Total items: {analysis['total_items']}")
    print(f"   By type: {dict(analysis['by_type'])}")
    print(f"   By state: {dict(analysis['by_state'])}")
    print(f"   By priority: {dict(analysis['by_priority'])}")
    print(f"   Unassigned: {analysis['unassigned_count']}")
    print(f"   High priority: {analysis['high_priority_count']}")
    
    print(f"\n💡 Insights generated:")
    for insight in analysis['insights']:
        print(f"   • {insight}")


def test_health_score_calculation():
    """Test project health score calculation."""
    print("\n\n🏥 Testing Health Score Calculation")
    print("=" * 50)
    
    engine = InsightsEngine()
    
    # Test case 1: Healthy project
    healthy_items = [
        {
            "fields": {
                "System.AssignedTo": "John Smith",
                "System.State": "Active"
            }
        },
        {
            "fields": {
                "System.AssignedTo": "Jane Doe", 
                "System.State": "Done"
            }
        }
    ]
    
    recent_items = [{"fields": {"System.Title": "Recent work"}}]
    
    health_score = engine._calculate_health_score(healthy_items, recent_items)
    print(f"Healthy project score: {health_score:.2f}")
    
    # Test case 2: Unhealthy project
    unhealthy_items = [
        {
            "fields": {
                "System.AssignedTo": "",
                "System.State": "New"
            }
        },
        {
            "fields": {
                "System.AssignedTo": "",
                "System.State": "Active"
            }
        }
    ]
    
    no_recent_items = []
    
    unhealthy_score = engine._calculate_health_score(unhealthy_items, no_recent_items)
    print(f"Unhealthy project score: {unhealthy_score:.2f}")
    
    if health_score > unhealthy_score:
        print("✅ Health scoring working correctly")
    else:
        print("❌ Health scoring needs adjustment")


def test_project_insight_generation():
    """Test complete project insight generation."""
    print("\n\n🏢 Testing Project Insight Generation")  
    print("=" * 50)
    
    engine = InsightsEngine()
    
    # Create test project data
    project_data = {
        "project": "Test Data Platform",
        "work_items_summary": [
            {
                "id": 1,
                "fields": {
                    "System.Title": "High priority feature",
                    "System.WorkItemType": "Feature",
                    "System.State": "Active",
                    "System.AssignedTo": "Alice Johnson",
                    "Microsoft.VSTS.Common.Priority": "2"
                }
            },
            {
                "id": 2,
                "fields": {
                    "System.Title": "Documentation update",
                    "System.WorkItemType": "Task", 
                    "System.State": "New",
                    "System.AssignedTo": "",
                    "Microsoft.VSTS.Common.Priority": "4"
                }
            }
        ],
        "repositories": [
            {"name": "data-api", "id": "1"},
            {"name": "data-ui", "id": "2"}
        ],
        "recent_work_items": [
            {
                "id": 3,
                "fields": {
                    "System.Title": "New feature request",
                    "System.WorkItemType": "Feature"
                }
            }
        ]
    }
    
    insight = engine.analyze_project_health(project_data)
    
    print(f"Project: {insight.project_name}")
    print(f"Health Score: {insight.health_score:.2f}")
    print(f"Key Metrics: {insight.key_metrics}")
    
    if insight.trends:
        print("📈 Trends:")
        for trend in insight.trends:
            print(f"   • {trend}")
    
    if insight.risks:
        print("⚠️  Risks:")
        for risk in insight.risks:
            print(f"   • {risk}")
    
    if insight.recommendations:
        print("💡 Recommendations:")
        for rec in insight.recommendations:
            print(f"   • {rec}")


async def test_full_business_intelligence():
    """Test complete business intelligence generation through orchestrator."""
    print("\n\n🧠 Testing Full Business Intelligence Pipeline")
    print("=" * 60)
    
    orchestrator = AzureDevOpsOrchestrator()
    
    # Add mock context
    orchestrator.context = {
        "available_projects": ["Test Project"]
    }
    
    try:
        # Test analysis request
        result = await orchestrator.handle_request("Analyze the health of our projects")
        
        if result["success"]:
            print("✅ Request processed successfully")
            
            if "business_intelligence" in result:
                bi = result["business_intelligence"]
                print(f"\n📊 Business Intelligence Generated:")
                print(f"   Summary: {bi.get('summary', 'No summary')}")
                print(f"   Projects analyzed: {len(bi.get('projects', []))}")
                print(f"   Executive summary: {bi.get('executive_summary', 'No executive summary')}")
                
                if bi.get('overall_recommendations'):
                    print("🎯 Overall Recommendations:")
                    for rec in bi['overall_recommendations'][:3]:
                        print(f"   • {rec}")
            else:
                print("ℹ️  No business intelligence generated (may not be an analysis request)")
        else:
            print(f"❌ Request failed: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


def test_pull_request_analysis():
    """Test pull request analysis capabilities."""
    print("\n\n🔄 Testing Pull Request Analysis")
    print("=" * 50)
    
    engine = InsightsEngine()
    
    test_prs = [
        {
            "id": 123,
            "title": "Fix authentication bug",
            "status": "completed",
            "created_by": "John Smith",
            "repository": "backend-api",
            "created_date": "2024-01-15"
        },
        {
            "id": 124,
            "title": "Add new dashboard feature", 
            "status": "active",
            "created_by": "Jane Doe",
            "repository": "frontend-web",
            "created_date": "2024-01-16"
        },
        {
            "id": 125,
            "title": "Update documentation",
            "status": "completed",
            "created_by": "John Smith", 
            "repository": "docs",
            "created_date": "2024-01-17"
        }
    ]
    
    analysis = engine.analyze_pull_requests(test_prs)
    
    print(f"✅ PR Analysis completed:")
    print(f"   Total PRs: {analysis['total_prs']}")
    print(f"   By status: {dict(analysis['by_status'])}")
    print(f"   By author: {dict(analysis['by_author'])}")
    print(f"   By repository: {dict(analysis['by_repository'])}")
    
    print(f"\n💡 PR Insights:")
    for insight in analysis['insights']:
        print(f"   • {insight}")


if __name__ == "__main__":
    test_work_items_analysis()
    test_health_score_calculation()
    test_project_insight_generation()
    test_pull_request_analysis()
    asyncio.run(test_full_business_intelligence())