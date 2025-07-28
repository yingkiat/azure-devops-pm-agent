#src/cli/main.py
import json, typer
from pathlib import Path
from rich import print as rprint

from agent import agent as ai_planner
from agent.id_mapping import get_id_mapping_manager
from devops_gateway.work_items import (
    list_epics,
    list_features_and_stories,
    list_tasks,
    list_orphan_features,
    list_orphan_tasks,
    get_work_item_hierarchy,
    create_work_item,
    delete_work_item,
)
from typing import Optional  # add this at top

app = typer.Typer(help="CLI for managing Azure DevOps projects with LLM assistance")

# ────────────────────────────────────────────────
# LIST COMMANDS
# ────────────────────────────────────────────────
@app.command("list-epics")
def _list_epics():
    """List all Epics in the configured Azure DevOps project."""
    for e in list_epics():
        rprint(f"[bold]{e['fields']['System.Title']}[/bold] (#{e['id']})")


@app.command("list-features")
def _list_features():
    """List Epics and their associated Features/User Stories."""
    hierarchy = get_work_item_hierarchy()
    epics = list_epics()
    for epic in epics:
        rprint(f"\n[bold magenta]{hierarchy[0]}: {epic['fields']['System.Title']}[/bold magenta] (#{epic['id']})")
        features = list_features_and_stories(epic['id'])
        for f in features:
            rprint(f"  └── [bold]{f['fields']['System.Title']}[/bold] (#{f['id']}) [{f['fields']['System.WorkItemType']}]")

    orphaned = list_orphan_features()
    if orphaned:
        rprint("\n[bold red]Orphaned Features/User Stories (no parent Epic):[/bold red]")
        for f in orphaned:
            rprint(f"  └── [bold]{f['fields']['System.Title']}[/bold] (#{f['id']}) [{f['fields']['System.WorkItemType']}]")

@app.command("list-tasks")
def _list_tasks():
    """List Epics, their Features/User Stories, and nested Tasks."""
    hierarchy = get_work_item_hierarchy()
    epics = list_epics()
    for epic in epics:
        rprint(f"\n[bold magenta]{hierarchy[0]}: {epic['fields']['System.Title']}[/bold magenta] (#{epic['id']})")
        features = list_features_and_stories(epic['id'])
        for f in features:
            rprint(f"  └── [bold cyan]{f['fields']['System.Title']}[/bold cyan] (#{f['id']}) [{f['fields']['System.WorkItemType']}]")
            tasks = list_tasks(f['id'])
            for t in tasks:
                rprint(f"      └── [green]{t['fields']['System.Title']}[/green] (#{t['id']}) [{t['fields']['System.WorkItemType']}]")

    orphaned = list_orphan_tasks()
    if orphaned:
        rprint("\n[bold red]Orphaned Tasks (no parent Feature/User Story):[/bold red]")
        for t in orphaned:
            rprint(f"  └── [green]{t['fields']['System.Title']}[/green] (#{t['id']}) [{t['fields']['System.WorkItemType']}] (#{t['id']})")

# ────────────────────────────────────────────────
# NEW TWO-LAYER ARCHITECTURE COMMANDS
# ────────────────────────────────────────────────
@app.command("plan-new")
def plan_new(goal: str = typer.Argument(..., help="Business goal to generate plan for")):
    """🆕 NEW: LLM generates structured plan (no direct API calls)."""
    from agent.agent import draft_structured_plan, save_structured_plan
    from agent.wiki_interface import create_interaction_log
    
    rprint(f"🎯 [bold cyan]Business Goal:[/bold cyan] {goal}")
    rprint("🤖 Generating structured plan...")
    
    try:
        # Auto-sync ID mappings before planning
        rprint("🔄 Syncing ID mappings...")
        manager = get_id_mapping_manager() 
        sync_results = manager.sync_with_azure_devops()
        rprint(f"   📝 {sync_results['created']} new, 🔄 {sync_results['updated']} updated")
        
        # LLM layer: generate structured plan
        plan = draft_structured_plan(goal)
        path = save_structured_plan(plan)
        
        rprint(f"✅ [green]Structured plan created:[/green] {path}")
        rprint(f"📋 [bold]Plan ID:[/bold] {plan.plan_id}")
        rprint(f"🏗️  [bold]Epics:[/bold] {len(plan.epics)}")
        
        # Create wiki interaction log and auto-update dashboard
        session_id = create_interaction_log(goal, path)
        rprint(f"📝 [blue]Wiki transcript:[/blue] /PM-Agent/Interactions/{session_id}")
        
        # Auto-update dashboard with debug info
        from agent.wiki_interface import WikiInterface
        interface = WikiInterface()
        rprint("🔧 [blue]Attempting dashboard auto-update...[/blue]")
        dashboard_success = interface.auto_update_dashboard()
        if dashboard_success:
            rprint("✅ [green]Dashboard updated successfully[/green]")
        else:
            rprint("⚠️  [yellow]Dashboard auto-update failed. You can update it manually later with:[/yellow]")
            rprint("   [cyan]python -m src.cli.main update-dashboard[/cyan]")
        
        rprint("\n🔍 [yellow]Next steps:[/yellow]")
        rprint(f"  1. Review plan: [cyan]python -m src.cli.main preview {path}[/cyan]")
        rprint(f"  2. Apply changes: [cyan]python -m src.cli.main sync {path} --approve[/cyan]")
        
    except Exception as e:
        rprint(f"❌ [red]Failed to generate plan:[/red] {e}")

@app.command("preview") 
def preview_plan(plan_path: str):
    """📋 Preview changes that would be made by syncing a plan."""
    from agent.sync_engine import sync_command
    sync_command(plan_path, dry_run=True)

@app.command("sync")
def sync_plan(
    plan_path: str,
    approve: bool = typer.Option(False, "--approve", help="Apply changes (required for actual sync)")
):
    """🔄 Sync structured plan to Azure DevOps (diff-first workflow)."""
    from agent.sync_engine import sync_command
    sync_command(plan_path, dry_run=False, approve=approve)
    
    if approve:
        # Auto-update wiki dashboard after successful sync
        from agent.wiki_interface import WikiInterface
        interface = WikiInterface()
        interface.auto_update_dashboard()

@app.command("setup-wiki")
def setup_wiki():
    """🔧 Set up PM-Agent wiki structure (run once)."""
    from devops_gateway.wiki_setup import ensure_pm_agent_wiki_structure, test_wiki_access
    
    rprint("🔧 Setting up PM-Agent wiki structure...")
    
    # Test basic access first
    if not test_wiki_access():
        rprint("❌ [red]Wiki access failed. Check your .env settings:[/red]")
        rprint("   - AZDO_PAT: Valid personal access token")
        rprint("   - AZDO_WIKI_NAME: Correct wiki name")
        rprint("   - AZDO_PROJECT: Correct project name")
        return
    
    # Set up the structure
    if ensure_pm_agent_wiki_structure():
        rprint("✅ [green]PM-Agent wiki structure ready![/green]")
        rprint("🌐 Check your wiki at: {}/{}/_wiki/wikis/{}/PM-Agent".format(
            "https://dev.azure.com/medline-apac-data-team",
            "Unified%20Data%20Warehouse", 
            "Unified-Data-Warehouse"
        ))
    else:
        rprint("❌ [red]Wiki setup failed. Check error messages above.[/red]")

@app.command("execute-requests")
def execute_pm_requests():
    """📋 Read PM-Agent page instructions and execute business requests."""
    from agent.page_reader import read_pm_instructions
    from agent.business_intel import execute_business_requests
    
    rprint("📖 Reading PM-Agent page instructions...")
    
    try:
        config = read_pm_instructions()
        if not config:
            rprint("❌ [red]Could not read PM-Agent page. Make sure it exists and has content.[/red]")
            rprint("💡 [yellow]Run 'setup-pm-page' to create an example page to edit.[/yellow]")
            return
        
        rprint(f"✅ Found {len(config.projects_to_monitor)} projects to monitor")
        rprint(f"📋 Found {len(config.business_requests)} business requests")
        
        if not config.business_requests:
            rprint("⚠️  [yellow]No requests found in PM-Agent page.[/yellow]")
            return
        
        # Auto-sync ID mappings for monitored projects
        rprint("🔄 Syncing ID mappings...")
        manager = get_id_mapping_manager()
        sync_results = manager.sync_with_azure_devops(config.projects_to_monitor)
        rprint(f"   📝 {sync_results['created']} new, 🔄 {sync_results['updated']} updated")
        
        # Execute the requests
        rprint("🚀 Executing business requests...")
        execute_business_requests(config)
        
    except Exception as e:
        rprint(f"❌ [red]Failed to execute requests: {e}[/red]")

@app.command("setup-pm-page")
def setup_pm_page():
    """📝 Create example PM-Agent page for business PM to edit."""
    from agent.page_reader import PMAgentPageReader
    from devops_gateway.wiki import push_markdown_to_azure_wiki
    
    rprint("📝 Creating example PM-Agent page...")
    
    try:
        reader = PMAgentPageReader()
        example_content = reader.create_example_page()
        
        success = push_markdown_to_azure_wiki(example_content, "PM-Agent")
        if success:
            rprint("✅ [green]Example PM-Agent page created![/green]")
            rprint("📝 Edit the page at: /PM-Agent to add your instructions")
            rprint("🔗 Then run: [cyan]python -m src.cli.main execute-requests[/cyan]")
            
            # Test reading it back immediately
            rprint("🔧 Testing page read...")
            test_content = reader.read_pm_agent_page()
            if test_content:
                rprint("✅ [green]Page read test successful![/green]")
            else:
                rprint("⚠️  [yellow]Page created but cannot be read back - check wiki permissions[/yellow]")
        else:
            rprint("❌ [red]Failed to create PM-Agent page[/red]")
            
    except Exception as e:
        rprint(f"❌ [red]Failed to setup PM page: {e}[/red]")

@app.command("test-wiki")
def test_wiki():
    """🔧 Test wiki connectivity and list available wikis."""
    from agent.page_reader import PMAgentPageReader
    from devops_gateway.connection import get_connection
    from utils.settings import settings
    
    rprint("🔧 Testing wiki connectivity...")
    
    try:
        from azure.devops.v7_0.wiki.wiki_client import WikiClient
        
        connection = get_connection()
        client: WikiClient = connection.clients.get_wiki_client()
        
        rprint(f"🔧 Organization: {settings.azdo_org_url}")
        rprint(f"🔧 Project: {settings.azdo_project}")
        rprint(f"🔧 Configured wiki: {settings.azdo_wiki_name}")
        
        wikis = client.get_all_wikis(project=settings.azdo_project)
        rprint(f"✅ Found {len(wikis)} wikis:")
        
        for wiki in wikis:
            rprint(f"   📖 {wiki.name} (ID: {wiki.id}, Type: {wiki.type})")
            
        
        # Test reading PM-Agent page if it exists
        reader = PMAgentPageReader()
        content = reader.read_pm_agent_page()
        
    except Exception as e:
        rprint(f"❌ [red]Wiki test failed: {e}[/red]")

# ────────────────────────────────────────────────
# LEGACY PLAN COMMAND (for backward compatibility)
# ────────────────────────────────────────────────
@app.command("plan")
def plan_ai(goal: str = typer.Argument(..., help="Business goal to generate plan for")):
    """⚠️  LEGACY: create plan using old format (will be deprecated)."""
    rprint("⚠️  [yellow]Using legacy plan format. Consider using 'plan-new' instead.[/yellow]")
    
    plan = ai_planner.draft_plan(goal)
    path = ai_planner.save_plan(plan)
    rprint(f"[green]Plan saved → {path}[/green]")

    # Push to Azure DevOps wiki (legacy behavior)
    from devops_gateway.wiki import save_plan_to_wiki
    import json
    with open(path, 'r', encoding='utf-8') as f:
        plan_json = json.load(f)
    save_plan_to_wiki(plan_json, None)

# ────────────────────────────────────────────────
# CREATE / DELETE COMMANDS
# ────────────────────────────────────────────────
@app.command("create")
def _create(
    work_item_type: str,
    title: str,
    description: str = typer.Option("", "--description", "-d"),
    parent_id: Optional[int] = typer.Option(None, "--parent")
):
    """
    Create a new work item (Epic, Feature, User Story, Task, Bug).
    Example:
        python -m src.cli.main create epic "New Platform" -d "High‑level initiative"
    """
    work_item = create_work_item(work_item_type, title, description, parent_id)
    rprint(f"[green]Created {work_item_type} → #{work_item['id']}[/green] {work_item['fields']['System.Title']}")


@app.command("delete")
def _delete(work_item_id: int):
    """Delete a work item by ID."""
    delete_work_item(work_item_id)
    rprint(f"[red]Deleted work item #{work_item_id}[/red]")




if __name__ == "__main__":
    app()
