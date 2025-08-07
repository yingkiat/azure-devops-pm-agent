#!/usr/bin/env python3
"""
AI-driven CLI for Azure DevOps.
Natural language interface powered by intent classification and MCP tools.
"""
import asyncio
import sys
import typer
from pathlib import Path

# Add src to path  
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_orchestrator.orchestrator import AzureDevOpsOrchestrator
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.json import JSON

app = typer.Typer(help="AI-powered Azure DevOps assistant")
console = Console()


@app.command("ask")
def ask_natural_language(
    request: str = typer.Argument(..., help="Your natural language request"),
    show_plan: bool = typer.Option(False, "--show-plan", help="Show execution plan details"),
    show_raw: bool = typer.Option(False, "--show-raw", help="Show raw JSON response")
):
    """
    Ask the AI assistant to perform Azure DevOps operations using natural language.
    
    Examples:
        python -m src.cli.ai_cli ask "What projects do we have?"
        python -m src.cli.ai_cli ask "Show me all critical bugs"
        python -m src.cli.ai_cli ask "Create an epic for the new data platform"
        python -m src.cli.ai_cli ask "What's in the README of the main API repo?"
    """
    asyncio.run(handle_natural_request(request, show_plan, show_raw))


async def handle_natural_request(request: str, show_plan: bool, show_raw: bool):
    """Handle a natural language request through the AI orchestrator."""
    try:
        orchestrator = AzureDevOpsOrchestrator()
        
        console.print(Panel.fit(f"🎯 [bold cyan]{request}[/bold cyan]", title="Request"))
        
        with console.status("[bold green]Processing request..."):
            result = await orchestrator.handle_request(request)
        
        if result["success"]:
            console.print("✅ [bold green]Request completed successfully![/bold green]\n")
            
            # Show classification results
            if "classified_intent" in result:
                intent_info = result["classified_intent"]
                console.print(f"🤖 [bold]Intent:[/bold] {intent_info['intent']} (confidence: {intent_info['confidence']:.2f})")
                console.print(f"📝 [bold]Description:[/bold] {intent_info['description']}\n")
            
            # Show execution plan if requested
            if show_plan and "execution_plan" in result:
                plan_info = result["execution_plan"]
                console.print("📋 [bold]Execution Plan:[/bold]")
                for step in plan_info["execution_plan"]:
                    console.print(f"   {step['step']}. {step['tool']} - {step.get('purpose', 'No purpose')}")
                console.print()
            
            # Show results in a user-friendly format
            if "execution_result" in result:
                display_results(result["execution_result"])
            
            # Show business intelligence if available
            if "business_intelligence" in result:
                display_business_intelligence(result["business_intelligence"])
            
            # Show context stats if available
            if "context_stats" in result:
                stats = result["context_stats"]
                console.print(f"\n💾 [dim]Context: {stats['conversation_entries']} conversations, {stats['known_projects']} projects tracked[/dim]")
            
            # Show wiki report if created
            if "wiki_report" in result:
                wiki_path = result["wiki_report"]
                console.print(f"📝 [blue]Wiki Report:[/blue] [link]{wiki_path}[/link] - Available for PM visibility")
            
            # Show raw JSON if requested
            if show_raw:
                console.print("\n📊 [bold]Raw Response:[/bold]")
                console.print(JSON(result))
                
        else:
            console.print(f"❌ [bold red]Request failed:[/bold red] {result.get('error', 'Unknown error')}")
            
            if show_raw:
                console.print(JSON(result))
        
    except Exception as e:
        console.print(f"❌ [bold red]Error:[/bold red] {e}")
        if show_raw:
            import traceback
            console.print(f"[red]{traceback.format_exc()}[/red]")


def display_results(execution_result: dict):
    """Display execution results in a user-friendly format."""
    results = execution_result.get("results", [])
    
    for step_result in results:
        if not step_result.get("success"):
            continue
            
        tool = step_result["tool"]
        data = step_result.get("data", {})
        
        if tool == "get_projects" and "projects" in data:
            console.print("🏢 [bold]Available Projects:[/bold]")
            for project in data["projects"]:
                state_color = "green" if project["state"] == "wellFormed" else "yellow"
                console.print(f"   • [{state_color}]{project['name']}[/{state_color}] - {project.get('description', 'No description')}")
                
        elif tool == "get_repositories" and "repositories" in data:
            console.print(f"📁 [bold]Repositories in {data.get('project', 'project')}:[/bold]")
            for repo in data["repositories"]:
                console.print(f"   • {repo['name']} (default: {repo.get('default_branch', 'unknown')})")
                
        elif tool == "get_work_items" and "work_items" in data:
            console.print(f"📋 [bold]Work Items ({data['count']} found):[/bold]")
            for wi in data["work_items"][:10]:  # Show first 10
                title = wi["fields"].get("System.Title", "No title")
                wi_type = wi["fields"].get("System.WorkItemType", "Unknown")
                state = wi["fields"].get("System.State", "Unknown")
                state_color = "green" if state in ["Done", "Closed"] else "yellow" if state == "Active" else "red"
                console.print(f"   • #{wi['id']}: {title[:60]}... [{wi_type}, [{state_color}]{state}[/{state_color}]]")
            
            if data["count"] > 10:
                console.print(f"   ... and {data['count'] - 10} more items")
                
        elif tool == "get_pull_requests" and "pull_requests" in data:
            console.print(f"🔄 [bold]Pull Requests ({data['count']} found):[/bold]")
            for pr in data["pull_requests"][:10]:  # Show first 10
                status_color = "green" if pr["status"] == "completed" else "yellow" if pr["status"] == "active" else "red"
                console.print(f"   • PR #{pr['id']}: {pr['title'][:50]}... [{pr['repository']}, [{status_color}]{pr['status']}[/{status_color}]]")
                console.print(f"     Created by {pr['created_by']} on {pr['created_date']}")
            
            if data["count"] > 10:
                console.print(f"   ... and {data['count'] - 10} more PRs")
                
        elif tool == "get_readme" and data.get("success"):
            console.print(f"📖 [bold]README from {data.get('repository', 'repository')}:[/bold]")
            content = data.get("content", "No content")
            # Show first 500 characters
            preview = content[:500]
            if len(content) > 500:
                preview += "..."
            console.print(Panel(preview, title=data.get("filename", "README")))


def display_business_intelligence(bi_data: dict):
    """Display business intelligence insights in a user-friendly format."""
    console.print("\n🧠 [bold cyan]Business Intelligence[/bold cyan]")
    console.print("=" * 50)
    
    # Executive Summary
    if bi_data.get("executive_summary"):
        console.print(f"📈 [bold]Executive Summary:[/bold]")
        console.print(f"   {bi_data['executive_summary']}\n")
    
    # Project Insights
    projects = bi_data.get("projects", [])
    if projects:
        console.print(f"🏢 [bold]Project Analysis ({len(projects)} projects):[/bold]")
        
        for project in projects:
            project_name = project.get("project_name", "Unknown")
            health_score = project.get("health_score", 0)
            
            # Health score color coding
            if health_score >= 0.8:
                health_color = "green"
                health_emoji = "🟢"
            elif health_score >= 0.6:
                health_color = "yellow" 
                health_emoji = "🟡"
            else:
                health_color = "red"
                health_emoji = "🔴"
            
            console.print(f"\n   {health_emoji} [bold]{project_name}[/bold] - Health: [{health_color}]{health_score:.1f}/1.0[/{health_color}]")
            
            # Key metrics
            metrics = project.get("key_metrics", {})
            if metrics:
                work_items = metrics.get("total_work_items", 0)
                repos = metrics.get("repositories", 0)
                recent = metrics.get("recent_activity", 0)
                console.print(f"     📊 {work_items} work items, {repos} repos, {recent} recent items")
            
            # Trends
            trends = project.get("trends", [])
            if trends:
                console.print("     📈 Trends:")
                for trend in trends[:2]:  # Show top 2 trends
                    console.print(f"       • {trend}")
            
            # Risks
            risks = project.get("risks", [])
            if risks:
                console.print("     ⚠️  Risks:")
                for risk in risks[:2]:  # Show top 2 risks
                    console.print(f"       • {risk}")
            
            # Recommendations
            recommendations = project.get("recommendations", [])
            if recommendations:
                console.print("     💡 Recommendations:")
                for rec in recommendations[:2]:  # Show top 2 recommendations
                    console.print(f"       • {rec}")
    
    # Team Insights
    team_insights = bi_data.get("team_insights", {})
    if team_insights and team_insights.get("team_members"):
        console.print(f"\n👥 [bold]Team Analysis:[/bold]")
        
        workload = team_insights.get("workload_distribution", {})
        if workload:
            console.print("   📊 Workload Distribution:")
            for member, count in sorted(workload.items(), key=lambda x: x[1], reverse=True)[:5]:
                console.print(f"     • {member}: {count} items")
        
        bottlenecks = team_insights.get("bottlenecks", [])
        if bottlenecks:
            console.print("   🚧 Bottlenecks:")
            for bottleneck in bottlenecks[:3]:
                console.print(f"     • {bottleneck}")
    
    # Overall Recommendations
    overall_recs = bi_data.get("overall_recommendations", [])
    if overall_recs:
        console.print(f"\n🎯 [bold]Strategic Recommendations:[/bold]")
        for rec in overall_recs:
            console.print(f"   • {rec}")
    
    console.print()


@app.command("chat")
def interactive_chat():
    """
    Start an interactive chat session with the AI assistant.
    Type 'quit' or 'exit' to end the session.
    """
    console.print(Panel.fit(
        "[bold cyan]Welcome to Azure DevOps AI Assistant![/bold cyan]\n\n"
        "Ask me anything about your Azure DevOps projects:\n"
        "• 'What projects do we have?'\n"
        "• 'Show me critical bugs'\n" 
        "• 'Create an epic for data platform'\n"
        "• 'What's in the main repo README?'\n\n"
        "Type 'quit' or 'exit' to end the session.",
        title="🤖 AI Chat Mode"
    ))
    
    orchestrator = None
    
    while True:
        try:
            request = typer.prompt("\n🎯 What would you like to know").strip()
            
            if request.lower() in ["quit", "exit", "q"]:
                console.print("👋 Goodbye!")
                break
                
            if not request:
                continue
            
            # Initialize orchestrator on first use
            if orchestrator is None:
                orchestrator = AzureDevOpsOrchestrator()
            
            # Process request
            asyncio.run(handle_chat_request(orchestrator, request))
            
        except KeyboardInterrupt:
            console.print("\n👋 Goodbye!")
            break
        except Exception as e:
            console.print(f"❌ Error: {e}")


async def handle_chat_request(orchestrator, request):
    """Handle a single chat request."""
    with console.status("[bold green]Thinking..."):
        result = await orchestrator.handle_request(request)
    
    if result["success"]:
        console.print("✅ [green]Done![/green]")
        
        if "execution_result" in result:
            display_results(result["execution_result"])
    else:
        console.print(f"❌ [red]Failed:[/red] {result.get('error', 'Unknown error')}")


@app.command("context")
def manage_context(
    action: str = typer.Argument(..., help="Action: 'show', 'clear', or 'history'"),
    keep_preferences: bool = typer.Option(True, "--keep-prefs", help="Keep user preferences when clearing")
):
    """
    Manage conversation context and memory.
    
    Actions:
        show - Display current context statistics
        clear - Clear all context data
        history - Show recent conversation history
    """
    from ai_orchestrator.context_manager import ContextManager
    
    context_manager = ContextManager()
    
    if action == "show":
        stats = context_manager.get_context_stats()
        console.print("🧠 [bold cyan]Context Statistics[/bold cyan]")
        console.print(f"   📊 Session keys: {stats['session_keys']}")
        console.print(f"   🏢 Known projects: {stats['known_projects']}")
        console.print(f"   💬 Conversations: {stats['conversation_entries']}")
        console.print(f"   ⭐ Preferred projects: {stats['preferred_projects']}")
        console.print(f"   🔄 Total interactions: {stats['total_interactions']}")
        console.print(f"   💾 Storage size: {stats['context_files_size_mb']} MB")
        
        # Show preferred projects if any
        if context_manager.user_preferences.preferred_projects:
            console.print(f"\n📁 [bold]Preferred Projects:[/bold]")
            for project in context_manager.user_preferences.preferred_projects[:5]:
                console.print(f"   • {project}")
        
        # Show common intents
        if context_manager.user_preferences.common_intents:
            console.print(f"\n🎯 [bold]Common Intent Patterns:[/bold]")
            for intent, count in sorted(context_manager.user_preferences.common_intents.items(), 
                                      key=lambda x: x[1], reverse=True)[:5]:
                console.print(f"   • {intent}: {count} times")
    
    elif action == "clear":
        confirm = typer.confirm("Are you sure you want to clear context data?")
        if confirm:
            context_manager.clear_context(keep_preferences=keep_preferences)
            if keep_preferences:
                console.print("✅ [green]Context cleared (preferences kept)[/green]")
            else:
                console.print("✅ [green]All context data cleared[/green]")
        else:
            console.print("❌ Context clear cancelled")
    
    elif action == "history":
        history = context_manager.get_conversation_summary(limit=10)
        if history:
            console.print("📜 [bold cyan]Recent Conversation History[/bold cyan]")
            for entry in reversed(history):  # Show most recent first
                success_icon = "✅" if entry['success'] else "❌"
                timestamp = entry['timestamp'][:19].replace('T', ' ')
                console.print(f"   {success_icon} [{entry['intent']}] {timestamp}")
                console.print(f"      {entry['request']}")
        else:
            console.print("📜 No conversation history found")
    
    else:
        console.print(f"❌ Unknown action: {action}")
        console.print("Valid actions: show, clear, history")


if __name__ == "__main__":
    app()