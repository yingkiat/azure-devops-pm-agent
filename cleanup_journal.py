#!/usr/bin/env python3
"""
AI Journal Cleanup Utility

Intelligent cleanup of AI journal content, removing test data and low-value content
while preserving valuable architectural insights.

Usage:
    python cleanup_journal.py --preview          # Preview what would be cleaned
    python cleanup_journal.py --execute          # Execute cleanup with backup
    python cleanup_journal.py --force            # Execute without confirmation
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm

from core.working_journal import WorkingJournal
from core.journal_cleanup import JournalCleanup

console = Console()
app = typer.Typer(help="AI Journal Cleanup Utility")


def display_cleanup_report(report: dict):
    """Display cleanup report in a user-friendly format"""

    analysis = report["analysis"]

    # Summary panel
    console.print(Panel.fit(
        f"[bold]Cleanup Analysis Summary[/bold]\n\n"
        f" Total deliverables: {analysis['total_deliverables']}\n"
        f" To keep: {analysis['to_keep']} (high architectural value)\n"
        f"  To delete: {analysis['to_delete']} (low/no value)\n"
        f" To review: {analysis['to_review']} (borderline cases)",
        title=" Analysis Results"
    ))

    # Detailed breakdown
    cleanup_results = report["cleanup_results"]

    if cleanup_results["deleted_deliverables"]:
        console.print("\n[bold red] Items to be removed:[/bold red]")

        table = Table()
        table.add_column("ID", style="dim")
        table.add_column("Title", style="cyan")
        table.add_column("Value Score", justify="center")
        table.add_column("Reason", style="yellow")

        for item in cleanup_results["deleted_deliverables"]:
            table.add_row(
                item["id"][:20] + "..." if len(item["id"]) > 20 else item["id"],
                item["title"][:40] + "..." if len(item["title"]) > 40 else item["title"],
                str(item.get("architectural_value", "N/A")),
                item["reason"]
            )

        console.print(table)

    if cleanup_results["kept_deliverables"]:
        console.print(f"\n[bold green] Keeping {len(cleanup_results['kept_deliverables'])} valuable items[/bold green]")

        # Show top valuable items
        kept_items = cleanup_results["kept_deliverables"]
        if kept_items:
            console.print("\n[dim]Top valuable content being preserved:[/dim]")
            for item in kept_items[:3]:  # Show top 3
                value_score = item.get("architectural_value", 0)
                console.print(f"   {item['title']} (value: {value_score}/10)")

    # Recommendations
    if report.get("recommendations"):
        console.print(f"\n[bold] Recommendations:[/bold]")
        for rec in report["recommendations"]:
            console.print(f"  • {rec}")


@app.command("preview")
def preview_cleanup():
    """Preview what would be cleaned up without making changes"""

    console.print(Panel.fit(
        "[bold cyan] AI Journal Cleanup Preview[/bold cyan]\n\n"
        "[dim]Analyzing content for cleanup opportunities...[/dim]",
        title="Preview Mode"
    ))

    try:
        # Initialize journal and cleanup
        journal = WorkingJournal()
        journal.start_session()

        cleanup_system = JournalCleanup(journal)
        report = cleanup_system.smart_cleanup(dry_run=True)

        # Display results
        display_cleanup_report(report)

        # Show backup info
        if report["cleanup_results"]["deleted_deliverables"]:
            console.print(f"\n[dim] Note: Actual cleanup will create automatic backup before any changes[/dim]")
        else:
            console.print(f"\n[green] Journal is clean! No low-value content found.[/green]")

    except Exception as e:
        console.print(f"[red] Preview failed: {e}[/red]")
        raise typer.Exit(1)


@app.command("execute")
def execute_cleanup(force: bool = typer.Option(False, "--force", help="Skip confirmation prompt")):
    """Execute cleanup with backup and confirmation"""

    console.print(Panel.fit(
        "[bold yellow]  AI Journal Cleanup Execution[/bold yellow]\n\n"
        "[dim]This will permanently remove low-value content.[/dim]\n"
        "[dim]A backup will be created automatically.[/dim]",
        title="Execution Mode"
    ))

    try:
        # Initialize journal and cleanup
        journal = WorkingJournal()
        journal.start_session()

        cleanup_system = JournalCleanup(journal)

        # Get preview first
        preview_report = cleanup_system.smart_cleanup(dry_run=True)
        display_cleanup_report(preview_report)

        items_to_delete = len(preview_report["cleanup_results"]["deleted_deliverables"])

        if items_to_delete == 0:
            console.print(f"\n[green] Nothing to clean up! Journal is already optimized.[/green]")
            return

        # Confirmation
        if not force:
            console.print(f"\n[bold]About to remove {items_to_delete} low-value items.[/bold]")

            if not Confirm.ask("Continue with cleanup?"):
                console.print(" Cleanup cancelled by user")
                return

        console.print(f"\n[yellow] Executing cleanup...[/yellow]")

        # Execute actual cleanup
        actual_report = cleanup_system.smart_cleanup(dry_run=False)

        if actual_report["cleanup_results"]["errors"]:
            console.print(f"[red] Cleanup completed with errors:[/red]")
            for error in actual_report["cleanup_results"]["errors"]:
                console.print(f"  • {error}")
        else:
            deleted_count = len(actual_report["cleanup_results"]["deleted_deliverables"])
            kept_count = len(actual_report["cleanup_results"]["kept_deliverables"])
            backup_path = actual_report["cleanup_results"]["backup_created"]

            console.print(Panel.fit(
                f"[bold green] Cleanup Completed Successfully[/bold green]\n\n"
                f"  Removed: {deleted_count} low-value items\n"
                f" Preserved: {kept_count} valuable items\n"
                f" Backup: {backup_path}",
                title=" Success"
            ))

    except Exception as e:
        console.print(f"[red] Cleanup execution failed: {e}[/red]")
        raise typer.Exit(1)


@app.command("analyze")
def analyze_content():
    """Analyze journal content quality without making changes"""

    console.print(Panel.fit(
        "[bold blue] AI Journal Content Analysis[/bold blue]\n\n"
        "[dim]Analyzing architectural value of journal content...[/dim]",
        title="Analysis Mode"
    ))

    try:
        journal = WorkingJournal()
        journal.start_session()

        cleanup_system = JournalCleanup(journal)
        assessments = cleanup_system.analyze_journal_content()

        # Create detailed analysis table
        console.print("\n[bold] Content Quality Breakdown:[/bold]")

        table = Table()
        table.add_column("Category", style="bold")
        table.add_column("Count", justify="center")
        table.add_column("Percentage", justify="center")
        table.add_column("Description", style="dim")

        total = len(journal.deliverables)

        table.add_row(
            "[green]High Value[/green]",
            str(len(assessments["keep"])),
            f"{len(assessments['keep'])/total*100:.1f}%" if total > 0 else "0%",
            "Architectural insights, analysis, technical content"
        )

        table.add_row(
            "[yellow]Borderline[/yellow]",
            str(len(assessments["review"])),
            f"{len(assessments['review'])/total*100:.1f}%" if total > 0 else "0%",
            "Needs manual review to determine value"
        )

        table.add_row(
            "[red]Low Value[/red]",
            str(len(assessments["delete"])),
            f"{len(assessments['delete'])/total*100:.1f}%" if total > 0 else "0%",
            "Test data, temporary content, minimal value"
        )

        console.print(table)

        # Quality insights
        if total > 0:
            quality_score = len(assessments["keep"]) / total * 100

            if quality_score >= 70:
                console.print(f"\n[green] Journal Quality: Excellent ({quality_score:.1f}%)[/green]")
            elif quality_score >= 50:
                console.print(f"\n[yellow]  Journal Quality: Good ({quality_score:.1f}%) - Consider cleanup[/yellow]")
            else:
                console.print(f"\n[red] Journal Quality: Poor ({quality_score:.1f}%) - Cleanup recommended[/red]")

    except Exception as e:
        console.print(f"[red] Analysis failed: {e}[/red]")
        raise typer.Exit(1)


@app.command("status")
def show_status():
    """Show current journal status and cleanup recommendations"""

    try:
        journal = WorkingJournal()
        session_info = journal.start_session()

        console.print(Panel.fit(
            f"[bold]AI Journal Status[/bold]\n\n"
            f" Session: {session_info['session_date']}\n"
            f" Total deliverables: {session_info['recovered_deliverables']}\n"
            f" Conversations: {session_info['conversation_entries']}\n"
            f" Active context: {len(session_info['active_context'])} items\n"
            f" Cleanup recommended: {'Yes' if session_info.get('cleanup_triggered', False) else 'No'}",
            title=" Journal Status"
        ))

        if session_info.get('cleanup_triggered', False):
            console.print(f"\n[yellow] Recommendation: Run cleanup to optimize journal performance[/yellow]")
            console.print(f"[dim]Use: python cleanup_journal.py preview[/dim]")

    except Exception as e:
        console.print(f"[red] Status check failed: {e}[/red]")
        raise typer.Exit(1)


@app.command("reset")
def reset_all(force: bool = typer.Option(False, "--force", help="Skip confirmation prompt")):
    """Reset all journal data and outputs for a fresh start"""

    console.print(Panel.fit(
        "[bold red]  COMPLETE RESET[/bold red]\n\n"
        "[dim]This will permanently remove:[/dim]\n"
        "  • All journal sessions, context, deliverables\n"
        "  • All EA matrices (entities, relationships)\n"
        "  • All output files and caches\n"
        "  • All backups\n\n"
        "[bold yellow]This action CANNOT be undone![/bold yellow]",
        title=" Reset Mode"
    ))

    try:
        from pathlib import Path
        import shutil

        # Define what will be cleaned
        cleanup_targets = {
            "journal": {
                "path": Path("ai_journal"),
                "items": ["session_*.md", "context/", "deliverables/", "thoughts/", "backups/"]
            },
            "ea_data": {
                "path": Path("data/ea"),
                "items": ["ea_entities.csv", "ea_relationships.csv", "backups/"]
            },
            "cache": {
                "path": Path(".cache"),
                "items": ["repositories/"]
            },
            "outputs": {
                "path": Path("."),
                "items": ["ea_outputs/", "ea_diagrams/", "reports/"]
            }
        }

        # Preview what will be removed
        console.print("\n[bold] Items to be removed:[/bold]")
        total_items = 0

        for category, config in cleanup_targets.items():
            base_path = config["path"]
            if base_path.exists():
                for item in config["items"]:
                    item_path = base_path / item if "/" not in item and "*" not in item else base_path.glob(item.replace("/", ""))
                    if isinstance(item_path, Path):
                        if item_path.exists():
                            console.print(f"  • {item_path}")
                            total_items += 1
                    else:
                        for p in item_path:
                            if p.exists():
                                console.print(f"  • {p}")
                                total_items += 1

        if total_items == 0:
            console.print("[green] Nothing to reset! All directories are already clean.[/green]")
            return

        # Confirmation
        if not force:
            console.print(f"\n[bold red]  About to permanently remove {total_items} items/directories[/bold red]")

            if not Confirm.ask("Are you absolutely sure you want to reset everything?"):
                console.print(" Reset cancelled by user")
                return

        console.print(f"\n[yellow] Resetting all data...[/yellow]")

        # Execute cleanup
        removed_count = 0
        errors = []

        # Clean journal
        journal_path = Path("ai_journal")
        if journal_path.exists():
            for item in ["session_*.md", "context", "deliverables", "thoughts", "backups"]:
                if "*" in item:
                    for p in journal_path.glob(item):
                        try:
                            if p.is_file():
                                p.unlink()
                            elif p.is_dir():
                                shutil.rmtree(p)
                            removed_count += 1
                        except Exception as e:
                            errors.append(f"Failed to remove {p}: {e}")
                else:
                    item_path = journal_path / item
                    if item_path.exists():
                        try:
                            if item_path.is_file():
                                item_path.unlink()
                            elif item_path.is_dir():
                                shutil.rmtree(item_path)
                            removed_count += 1
                        except Exception as e:
                            errors.append(f"Failed to remove {item_path}: {e}")

        # Clean EA data
        ea_path = Path("data/ea")
        if ea_path.exists():
            for item in ["ea_entities.csv", "ea_relationships.csv", "backups"]:
                item_path = ea_path / item
                if item_path.exists():
                    try:
                        if item_path.is_file():
                            item_path.unlink()
                        elif item_path.is_dir():
                            shutil.rmtree(item_path)
                        removed_count += 1
                    except Exception as e:
                        errors.append(f"Failed to remove {item_path}: {e}")

        # Clean cache
        cache_path = Path(".cache")
        if cache_path.exists():
            repositories_path = cache_path / "repositories"
            if repositories_path.exists():
                try:
                    shutil.rmtree(repositories_path)
                    removed_count += 1
                except Exception as e:
                    errors.append(f"Failed to remove {repositories_path}: {e}")

        # Clean outputs
        for output_dir in ["ea_outputs", "ea_diagrams", "reports"]:
            output_path = Path(output_dir)
            if output_path.exists():
                try:
                    shutil.rmtree(output_path)
                    removed_count += 1
                except Exception as e:
                    errors.append(f"Failed to remove {output_path}: {e}")

        # Report results
        if errors:
            console.print(f"\n[yellow]  Reset completed with {len(errors)} errors:[/yellow]")
            for error in errors:
                console.print(f"  • {error}")

        console.print(Panel.fit(
            f"[bold green] Reset Completed[/bold green]\n\n"
            f"  Removed: {removed_count} items/directories\n"
            f" Errors: {len(errors)}\n\n"
            f"[dim]You now have a clean slate for a fresh start.[/dim]",
            title=" Reset Complete"
        ))

    except Exception as e:
        console.print(f"[red] Reset failed: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()