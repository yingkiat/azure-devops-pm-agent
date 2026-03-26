"""Azure DevOps PM Agent - Main CLI Entry Point.

 This tool has evolved to use natural language AI interface!

Use: python -m src.cli.ai_cli ask "your request"
"""
import typer
from rich import print as rprint

app = typer.Typer(help="Azure DevOps PM Agent - AI-powered project management")



@app.callback()
def main():
    """
    Azure DevOps PM Agent - AI-powered project management assistant.
    
     NEW: Natural language interface available!
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


@app.command("ea-discover")
def ea_discover(
    text_input: str = typer.Argument(..., help="Natural language description of EA changes or file path"),
    output: str = typer.Option(None, "--output", "-o", help="Output JSON file (defaults to ea_outputs/ folder)"),
    summary: bool = typer.Option(False, "--summary", "-s", help="Display formatted summary"),
    matrix: bool = typer.Option(True, "--matrix/--no-matrix", help="Update EA matrix (default: True)"),
    storage_type: str = typer.Option("csv", "--storage", help="Storage type (csv, sqlite, azure)")
):
    """Discover EA objects and update matrix from natural language input."""
    from pathlib import Path
    from ..ea.ea_discovery import EADiscovery

    try:
        discovery = EADiscovery(storage_type=storage_type)

        # Check if input is a file path or direct text
        input_path = Path(text_input)
        if input_path.exists() and input_path.is_file():
            # Read from file
            system_description = input_path.read_text(encoding='utf-8')
            rprint(f"[cyan]Reading from file:[/cyan] {text_input}")
        else:
            # Use as direct text input
            system_description = text_input
            rprint(f"[cyan]Processing text:[/cyan] {text_input[:100]}...")

        if matrix:
            # Use new matrix-aware discovery
            results = discovery.discover_and_update_matrix(system_description)

            # Display matrix results
            rprint("\n" + discovery.format_matrix_results(results))

            # Show matrix summary
            rprint("\n" + discovery.get_matrix_summary())

        else:
            # Use legacy discovery (JSON output)
            results = discovery.discover(system_description)

            if summary:
                rprint("\n" + discovery.format_summary(results))

        # Save JSON output if requested or use default
        if output:
            discovery.save_discovery(results, output)
            rprint(f"\n[green]Results saved to:[/green] {output}")
        elif not matrix:  # Only auto-save JSON when not using matrix mode
            # Default to ea_outputs folder with timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_output = f"ea_outputs/ea_analysis_{timestamp}.json"
            discovery.save_discovery(results, default_output)
            rprint(f"\n[green]Results saved to:[/green] {default_output}")

        if "error" in results:
            rprint(f"[red]Discovery failed:[/red] {results['error']}")
            raise typer.Exit(1)
        else:
            rprint("[green]EA discovery completed successfully![/green]")

    except FileNotFoundError as e:
        rprint(f"[red]File not found:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        rprint(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


@app.command("ea-diagrams")
def ea_diagrams(
    ea_file: str = typer.Argument(..., help="Path to EA analysis JSON file"),
    diagram_type: str = typer.Option("overview", "--type", "-t", help="Type of diagram to generate"),
    output: str = typer.Option(None, "--output", "-o", help="Output file path"),
    list_types: bool = typer.Option(False, "--list", "-l", help="List available diagram types")
):
    """Generate EA diagrams using Gemini Flash 2.5 visual capabilities."""
    from ..ea.ea_diagrams import EADiagramGenerator

    try:
        generator = EADiagramGenerator()

        if list_types:
            rprint("[bold cyan]Available Diagram Types:[/bold cyan]\n")
            for dtype in generator.list_supported_types():
                rprint(f"• [green]{dtype}[/green]: {generator.get_diagram_info(dtype)}")
            return

        rprint(f"[cyan]Generating {diagram_type} diagram from {ea_file}...[/cyan]")

        # Generate diagram
        result_path = generator.generate_from_file(ea_file, diagram_type, output)

        # Display results
        rprint(generator.format_results(result_path, diagram_type))

    except FileNotFoundError as e:
        rprint(f"[red]File not found:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        rprint(f"[red]Failed to generate diagram:[/red] {e}")
        raise typer.Exit(1)


@app.command("ea-archi")
def ea_archi(
    ea_file: str = typer.Argument(..., help="Path to EA analysis JSON file"),
    output_dir: str = typer.Option("archi_inputs", "--output-dir", "-o", help="Output directory for Archi CSV files"),
    no_views: bool = typer.Option(False, "--no-views", help="Skip view generation"),
    preview: bool = typer.Option(False, "--preview", "-p", help="Preview what would be generated")
):
    """Generate Archi-compatible CSV files with auto-generated views."""
    from ..ea.archi_export import ArchiExporter

    try:
        rprint(f"[cyan]Exporting EA analysis to Archi format...[/cyan]")
        rprint(f"[dim]Input: {ea_file}[/dim]")
        rprint(f"[dim]Output: {output_dir}/[/dim]\n")

        if preview:
            # Load and show preview
            import json
            from pathlib import Path

            with open(ea_file, 'r', encoding='utf-8') as f:
                ea_analysis = json.load(f)

            rprint("[bold cyan]Preview of Archi Export:[/bold cyan]\n")

            # Count elements by layer
            for layer in ['business', 'application', 'data', 'infrastructure', 'security']:
                if layer in ea_analysis and ea_analysis[layer]:
                    count = sum(len(items) if isinstance(items, list) else 1
                               for items in ea_analysis[layer].values() if items)
                    rprint(f"  [green]{layer.title()}:[/green] ~{count} elements")

            rprint("\n[bold cyan]Views to be generated:[/bold cyan]")
            rprint("  • Application Landscape Overview")
            if ea_analysis.get('business'):
                rprint("  • Business Process Flow")
            if ea_analysis.get('application'):
                rprint("  • Application Cooperation")
            if ea_analysis.get('data'):
                rprint("  • Information Structure")
            if ea_analysis.get('infrastructure'):
                rprint("  • Technology Architecture")
            if ea_analysis.get('security'):
                rprint("  • Security Architecture")

            app_count = len(ea_analysis.get('application', {}).get('applications', []))
            if app_count > 1:
                rprint("  • Integration View")

            rprint(f"\n[yellow]Run without --preview to generate CSV files[/yellow]")
            return

        # Generate Archi CSV files
        exporter = ArchiExporter(output_dir=output_dir)
        output_files = exporter.export(ea_file, generate_views=not no_views)

        rprint("\n[bold green] Archi export completed successfully![/bold green]\n")
        rprint("[bold cyan]Generated files:[/bold cyan]")
        for file_type, file_path in output_files.items():
            rprint(f"   {file_type}: {file_path}")

        rprint("\n[bold yellow]Next steps:[/bold yellow]")
        rprint("  1. Open Archi tool")
        rprint("  2. File → Import → CSV")
        rprint(f"  3. Select files from: {output_dir}/")
        rprint("  4. View auto-generated diagrams in Archi")

    except FileNotFoundError as e:
        rprint(f"[red]File not found:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        rprint(f"[red]Failed to export to Archi:[/red] {e}")
        import traceback
        rprint(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.command("ea-artifacts")
def ea_artifacts(
    data_source: str = typer.Option(None, "--data-source", "-d", help="Path to EA data source (defaults to data/ea/ea_entities.csv)"),
    output_dir: str = typer.Option("ea_diagrams", "--output-dir", "-o", help="Output directory for artifacts"),
    diagram_type: str = typer.Option(None, "--type", "-t", help="Generate specific diagram type only"),
    preview: bool = typer.Option(False, "--preview", "-p", help="Preview available diagrams without generating"),
    info: bool = typer.Option(False, "--info", "-i", help="Show data source information"),
    separate: bool = typer.Option(False, "--separate", "-s", help="Generate separate files instead of combined diagram")
):
    """Generate EA artifacts (diagrams) from EA data sources."""
    from ..ea.artifact_generator import create_artifact_generator
    from ..ea.artifact_generators.diagram_types import DiagramType

    try:
        # Create artifact generator
        generator = create_artifact_generator(data_source)

        if info:
            # Show data source information
            data_info = generator.get_data_info()
            if data_info.get("available"):
                rprint("[bold cyan]EA Data Source Information[/bold cyan]\n")
                rprint(f"[green] Data Available[/green]")
                rprint(f"Applications: {data_info['data_summary']['applications']}")
                rprint(f"Capabilities: {data_info['data_summary']['capabilities']}")
                rprint(f"Domains: {data_info['data_summary']['domains']}")
                rprint(f"Schema Version: {data_info['schema']['version']}")
                rprint(f"Available Columns: {', '.join(data_info['schema']['columns'])}")

                rprint(f"\n[bold]Compatible Diagrams ({len(data_info['compatible_diagrams'])}):[/bold]")
                for diagram in data_info['compatible_diagrams']:
                    rprint(f"  • {diagram}")
            else:
                rprint("[red] Data source not available[/red]")
                if "error" in data_info:
                    rprint(f"Error: {data_info['error']}")
            return

        if preview:
            # Preview available diagrams
            preview_info = generator.preview_diagrams()
            if preview_info.get("success"):
                rprint("[bold cyan]EA Artifact Generation Preview[/bold cyan]\n")
                rprint(f"Data Source: {preview_info['data_source']}")
                rprint(f"Applications: {preview_info['data_summary']['applications']}")
                rprint(f"Capabilities: {preview_info['data_summary']['capabilities']}")
                rprint(f"Domains: {preview_info['data_summary']['domains']}")

                rprint(f"\n[bold]Available Diagrams ({len(preview_info['available_diagrams'])}):[/bold]")
                for diagram in preview_info['available_diagrams']:
                    rprint(f"  {diagram['priority']:3d} • {diagram['type']} - {diagram['description']}")
            else:
                rprint(f"[red]Preview failed:[/red] {preview_info.get('error', 'Unknown error')}")
            return

        if diagram_type:
            # Generate specific diagram
            try:
                diagram_enum = DiagramType(diagram_type)
                result = generator.generate_specific_diagram(diagram_enum, output_dir)

                if result.get("success"):
                    rprint(f"[green] Generated {diagram_type} diagram[/green]")
                    rprint(f"File: {result['file_path']}")
                else:
                    rprint(f"[red] Failed to generate diagram:[/red] {result.get('error', 'Unknown error')}")
            except ValueError:
                rprint(f"[red]Invalid diagram type:[/red] {diagram_type}")
                rprint(f"Available types: {', '.join([dt.value for dt in DiagramType])}")
        else:
            # Generate all compatible artifacts
            combined_mode = not separate  # Default to combined unless --separate specified
            mode_text = "separate files" if separate else "combined diagram"
            rprint(f"[cyan]Generating EA artifacts ({mode_text})...[/cyan]")
            result = generator.generate_all_artifacts(output_dir, combined=combined_mode)

            if result.get("success"):
                rprint(f"[green] EA artifacts generated successfully![/green]")
                rprint(f"Output directory: {result['output_directory']}")
                rprint(f"Generated diagrams: {len(result['generated_diagrams'])}")

                rprint("\n[bold]Generated Files:[/bold]")
                for diagram_type, file_path in result['saved_files'].items():
                    if not diagram_type.endswith("_error"):
                        rprint(f"  • {diagram_type}: {file_path}")

                # Show summary
                if result.get('summary'):
                    rprint(f"\n[yellow]Summary saved to: {output_dir}/generation_summary.txt[/yellow]")

                if combined_mode:
                    rprint(f"\n[bold blue]Single File Generated:[/bold blue]")
                    rprint(f"   All {result['generated_diagrams']} diagrams in one file with clear section separators")
                    rprint(f"   Perfect for documentation and sharing")
                else:
                    rprint(f"\n[bold blue]Multiple Files Generated:[/bold blue]")
                    rprint(f"   {len(result['generated_diagrams'])} separate .mermaid files")

                rprint(f"\n[bold green]Quick Actions:[/bold green]")
                rprint(f"  View diagrams: Open .mermaid files in a Mermaid-compatible viewer")
                rprint(f"  Preview online: Copy content to https://mermaid.live/")
                rprint(f"  Switch mode: Add --separate for individual files")

            else:
                rprint(f"[red] Failed to generate artifacts:[/red] {result.get('error', 'Unknown error')}")
                if 'data_source' in result:
                    rprint(f"Data source: {result['data_source']}")

    except FileNotFoundError as e:
        rprint(f"[red]File not found:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        rprint(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


@app.command("ea-view")
def ea_view(
    spec_path: str = typer.Argument(..., help="Path to YAML view spec"),
    rebuild_portal: bool = typer.Option(False, "--portal/--no-portal", help="Rebuild portal after generating the diagram"),
):
    """Generate a draw.io diagram from a YAML view spec and optionally rebuild the portal."""
    from pathlib import Path
    from ..ea.drawio_generator import DrawIOGenerator
    from portal.backend.builder import PortalBuilder

    try:
        spec = Path(spec_path)
        if not spec.exists():
            rprint(f"[red]View spec not found:[/red] {spec_path}")
            raise typer.Exit(1)

        rprint(f"[cyan]Generating view from:[/cyan] {spec_path}")
        generator = DrawIOGenerator()
        result = generator.generate(str(spec))

        if result.get("error"):
            rprint(f"[red]Diagram generation failed:[/red] {result['error']}")
            raise typer.Exit(1)

        for output_file in result.get("output_files", []):
            rprint(f"[green]Generated:[/green] {output_file}")

        if rebuild_portal:
            rprint("[cyan]Rebuilding portal...[/cyan]")
            builder = PortalBuilder(
                diagrams_dir="ea_diagrams",
                model_dir="archi_inputs",
                specs_dir="ea_inputs/views",
                output_dir="portal/dist",
            )
            portal_result = builder.build()

            if not portal_result.get("success"):
                rprint(f"[red]Portal rebuild failed:[/red] {portal_result.get('errors', [])}")
                raise typer.Exit(1)

            rprint(f"[green]Portal ready:[/green] {Path(portal_result['output_path']).absolute() / 'index.html'}")

    except typer.Exit:
        raise
    except Exception as e:
        rprint(f"[red]Failed to generate view:[/red] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
