"""Azure DevOps PM Agent - Main CLI Entry Point.

🚀 This tool has evolved to use natural language AI interface!

Use: python -m src.cli.ai_cli ask "your request"
"""
import typer
from rich import print as rprint

app = typer.Typer(help="Azure DevOps PM Agent - AI-powered project management")


@app.callback()
def main():
    """
    Azure DevOps PM Agent - AI-powered project management assistant.
    
    🚀 NEW: Natural language interface available!
    Use: python -m src.cli.ai_cli ask "Show me project health"
    """
    pass


@app.command()
def info():
    """Show information about the AI interface."""
    rprint("[bold cyan]Azure DevOps PM Agent - AI Interface[/bold cyan]\n")
    
    rprint("[bold green]Natural language commands:[/bold green]")
    rprint("  [cyan]python -m src.cli.ai_cli ask \"Show me all critical bugs\"[/cyan]")
    rprint("  [cyan]python -m src.cli.ai_cli ask \"Analyze project health\"[/cyan]") 
    rprint("  [cyan]python -m src.cli.ai_cli ask \"What's in the README?\"[/cyan]")
    
    rprint("\n[bold blue]Interactive mode:[/bold blue]")
    rprint("  [cyan]python -m src.cli.ai_cli chat[/cyan]")
    
    rprint("\n[bold yellow]Context management:[/bold yellow]")
    rprint("  [cyan]python -m src.cli.ai_cli context show[/cyan]")
    rprint("  [cyan]python -m src.cli.ai_cli context clear[/cyan]")


@app.command("plan-new")
def plan_new(goal: str = typer.Argument(..., help="Business goal to generate plan for")):
    """Generate structured plan using LLM reasoning (legacy feature)."""
    rprint("[yellow]Note: Plan generation is still available but consider using AI interface for comprehensive analysis:[/yellow]")
    rprint(f"  [cyan]python -m src.cli.ai_cli ask \"Create a plan for: {goal}\"[/cyan]\n")
    
    # Keep minimal plan generation for backward compatibility
    from agent.agent import draft_structured_plan, save_structured_plan
    from agent.id_mapping import get_id_mapping_manager
    
    rprint(f"[bold cyan]Business Goal:[/bold cyan] {goal}")
    rprint("Generating structured plan...")
    
    try:
        # Auto-sync ID mappings before planning
        rprint("Syncing ID mappings...")
        manager = get_id_mapping_manager() 
        sync_results = manager.sync_with_azure_devops()
        rprint(f"   {sync_results['created']} new, {sync_results['updated']} updated")
        
        # LLM layer: generate structured plan
        plan = draft_structured_plan(goal)
        path = save_structured_plan(plan)
        
        rprint(f"[green]Structured plan created:[/green] {path}")
        rprint(f"[bold]Plan ID:[/bold] {plan.plan_id}")
        rprint(f"[bold]Epics:[/bold] {len(plan.epics)}")
        
        rprint("\n[yellow]Next steps:[/yellow]")
        rprint(f"  1. Review plan: [cyan]python -m src.cli.main preview {path}[/cyan]")
        rprint(f"  2. Apply changes: [cyan]python -m src.cli.main sync {path} --approve[/cyan]")
        
    except Exception as e:
        rprint(f"[red]Failed to generate plan:[/red] {e}")


@app.command("preview") 
def preview_plan(plan_path: str):
    """Preview changes that would be made by syncing a plan."""
    from agent.sync_engine import sync_command
    sync_command(plan_path, dry_run=True)


@app.command("sync")
def sync_plan(
    plan_path: str,
    approve: bool = typer.Option(False, "--approve", help="Apply changes (required for actual sync)")
):
    """Sync structured plan to Azure DevOps."""
    from agent.sync_engine import sync_command
    sync_command(plan_path, dry_run=False, approve=approve)


if __name__ == "__main__":
    app()