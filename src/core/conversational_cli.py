"""
Conversational AI CLI - MVP4 Implementation

Revolutionary interface that transforms the AI from stateless command execution
into a persistent analytical partner with working memory and iterative capabilities.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import enhanced systems
from core.enhanced_ea_orchestrator import EnhancedEAOrchestrator
from pm.orchestrator import PMOrchestrator
from core.persona_detector import PersonaDetector

console = Console()

class ConversationalAI:
    """
    Conversational AI Interface with persistent memory and iteration

    Features:
    - Single entry point (no subcommands)
    - Persistent session memory
    - Reference resolution ("that analysis", "the diagram")
    - Iterative refinement capabilities
    - Smart file caching
    """

    def __init__(self):
        self.persona_detector = PersonaDetector()
        self.ea_orchestrator = None
        self.pm_orchestrator = None
        self.session_started = False

    async def start_session(self):
        """Initialize conversational session with context recovery"""
        if self.session_started:
            return

        console.print(Panel.fit(
            "[bold cyan] AI Working Journal - MVP4[/bold cyan]\n\n"
            "[dim]Starting session with persistent memory...[/dim]",
            title=" Initializing"
        ))

        # Initialize EA orchestrator with journal
        self.ea_orchestrator = EnhancedEAOrchestrator()
        ea_session = await self.ea_orchestrator.start_session()

        # Initialize PM orchestrator (standard)
        self.pm_orchestrator = PMOrchestrator()

        self.session_started = True

        # Show session recovery information
        if ea_session['recovered_deliverables'] > 0:
            console.print(f"[green] Session recovered:[/green]")
            console.print(f"    {ea_session['recovered_deliverables']} deliverables")
            console.print(f"    {ea_session['conversation_entries']} conversations")
            console.print(f"    {len(ea_session['active_context'])} active items")

            if ea_session.get('context_summary'):
                console.print(f"\n[bold]Recent Context:[/bold]")
                console.print(f"   {ea_session['context_summary']}")
        else:
            console.print("[green] Fresh session started[/green]")

        console.print()

    async def handle_conversation(self, user_input: str) -> bool:
        """
        Handle conversational input with iteration support

        Returns True to continue conversation, False to exit
        """
        if user_input.lower() in ["quit", "exit", "q", "bye"]:
            return False

        if not user_input.strip():
            return True

        try:
            # Detect persona for the request
            persona_decision = self.persona_detector.detect_persona(user_input)

            # Route to appropriate orchestrator
            if persona_decision.primary_persona == "EA":
                console.print(f" [bold blue]EA Intelligence[/bold blue] (confidence: {persona_decision.confidence:.2f})")
                result = await self.ea_orchestrator.handle_request(user_input)
            else:
                console.print(f" [bold green]PM Intelligence[/bold green] (confidence: {persona_decision.confidence:.2f})")
                result = await self.pm_orchestrator.handle_request(user_input)

            # Display results
            await self._display_conversational_result(result, user_input)

        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            console.print("[dim]Please try rephrasing your request.[/dim]")

        return True

    async def _display_conversational_result(self, result: dict, user_input: str):
        """Display results in conversational format"""

        if not result.get("success"):
            error_msg = result.get('error', 'Unknown error')
            # Check if there are execution errors
            if 'execution_result' in result and 'errors' in result['execution_result']:
                errors = result['execution_result']['errors']
                if errors:
                    error_msg = '\n'.join(errors)
            console.print(f"[red] {error_msg}[/red]")
            return

        # Show intent understanding
        if "classified_intent" in result:
            intent_info = result["classified_intent"]
            console.print(f"[dim] Understood: {intent_info['description']}[/dim]")

        # Show file efficiency (EA only)
        if "file_efficiency" in result:
            efficiency = result["file_efficiency"]
            if efficiency['files_cached'] > 0:
                console.print(f"[dim] Efficiency: Processed {efficiency['files_processed']} files, cached {efficiency['files_cached']} ({efficiency['efficiency_gain']:.1f}% saved)[/dim]")

        # Display execution results
        if "execution_result" in result:
            await self._display_execution_results(result["execution_result"])

        # Show deliverable information
        if result.get("deliverable_created"):
            console.print(f"[green] Created: {result['deliverable_created']}[/green]")

        if result.get("deliverable_modified"):
            console.print(f"[yellow] Modified: {result['deliverable_modified']}[/yellow]")

        # Show context summary
        if result.get("context_summary"):
            console.print(f"[dim] Context: {result['context_summary']}[/dim]")

        console.print()

    async def _display_execution_results(self, execution_result: dict):
        """Display detailed execution results"""
        results = execution_result.get("results", [])

        for step_result in results:
            if not step_result.get("success"):
                continue

            tool = step_result["tool"]
            data = step_result.get("data", {})

            # MVP3 Visual Diagram Results
            if tool == "ea_generate_visual_diagram":
                console.print("[bold cyan] Visual Diagram Generated[/bold cyan]")
                if data.get("image_path"):
                    console.print(f"    Image: {data['image_path']}")
                if data.get("deliverable_id"):
                    console.print(f"    Tracked as: {data['deliverable_id']}")
                if data.get("source"):
                    console.print(f"    {data['source']}")

            # Deliverable Operations
            elif tool == "deliverable_modification":
                console.print("[bold yellow] Content Modified[/bold yellow]")
                console.print(f"    Original: {data.get('original_title')}")
                console.print(f"    Modified: {data.get('modified_deliverable')}")
                console.print(f"    Change: {data.get('modification')}")

            elif tool == "deliverable_retrieval":
                console.print("[bold blue] Retrieved Content[/bold blue]")
                console.print(f"    Title: {data.get('title')}")
                console.print(f"    Created: {data.get('created_at')}")
                if data.get("content_preview"):
                    console.print(Panel(data["content_preview"], title="Content Preview"))

            # EA Discovery Results
            elif tool == "ea_discovery" and "discovery" in data:
                console.print("[bold cyan] EA Discovery Completed[/bold cyan]")
                if "changes" in data and data["changes"]:
                    changes = data["changes"]
                    if changes.get("inserts"):
                        console.print(f"   [green] Added {len(changes['inserts'])} new mappings[/green]")

            # Standard EA results (delegate to existing display logic)
            else:
                # Use existing display logic for other EA tools
                self._display_standard_ea_result(step_result)

    def _display_standard_ea_result(self, step_result: dict):
        """Display standard EA results (from existing ai_cli.py logic)"""
        tool = step_result["tool"]
        data = step_result.get("data", {})

        if tool == "ea_discovery":
            console.print("[bold cyan] EA Discovery Results[/bold cyan]")
            if "matrix_summary" in data:
                summary = data["matrix_summary"]
                console.print(f"    {summary.get('applications', 0)} apps, {summary.get('capabilities', 0)} capabilities")

    def get_welcome_message(self) -> str:
        """Get personalized welcome message"""
        if self.session_started and self.ea_orchestrator and self.ea_orchestrator.session_info:
            session_info = self.ea_orchestrator.session_info
            if session_info['recovered_deliverables'] > 0:
                return f"Welcome back! I remember our work on {len(session_info['active_context'])} active items. What would you like to explore next?"
            else:
                return "Hello! I'm ready to help with your EA and PM work. What would you like to analyze or create?"
        else:
            return "Hello! I'm your AI assistant with persistent memory. What would you like to work on?"


async def run_conversational_interface():
    """Main conversational interface"""
    ai = ConversationalAI()

    # Start session
    await ai.start_session()

    # Show welcome message
    welcome_msg = ai.get_welcome_message()
    console.print(Panel.fit(
        f"[bold green]{welcome_msg}[/bold green]\n\n"
        "[dim]Try phrases like:[/dim]\n"
        "• [cyan]'analyze our microservices platform'[/cyan]\n"
        "• [cyan]'that missed the security layer'[/cyan]\n"
        "• [cyan]'create a visual diagram of this'[/cyan]\n"
        "• [cyan]'make it more detailed'[/cyan]\n\n"
        "[dim]Type 'quit' to exit[/dim]",
        title=" Ready for Conversation"
    ))

    # Conversation loop
    while True:
        try:
            user_input = console.input("\n[bold cyan] You:[/bold cyan] ").strip()

            # Handle conversation
            should_continue = await ai.handle_conversation(user_input)

            if not should_continue:
                console.print("\n[green] Goodbye! Your work is saved in the AI journal.[/green]")
                break

        except KeyboardInterrupt:
            console.print("\n\n[green] Session ended. Your work is saved![/green]")
            break
        except EOFError:
            break


# CLI Application
app = typer.Typer(help="Conversational AI Assistant with Working Memory", no_args_is_help=False)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Start conversational AI session with persistent memory.

    Revolutionary interface with:
    - Persistent session memory
    - Reference resolution ("that analysis", "the diagram")
    - Iterative refinement capabilities
    - Smart file caching
    """
    if ctx.invoked_subcommand is None:
        # No subcommand provided - start conversational interface
        asyncio.run(run_conversational_interface())


@app.command("legacy")
def legacy_mode():
    """
    Access legacy command-based interface for backwards compatibility.
    """
    console.print("[yellow]  Legacy mode - consider using the new conversational interface[/yellow]")
    console.print("Run: [cyan]python -m src.cli.ai_cli[/cyan] for old interface")


@app.command("session")
def session_info():
    """
    Show current session information and context.
    """
    async def show_session():
        ai = ConversationalAI()
        await ai.start_session()

        session_info = ai.ea_orchestrator.session_info
        console.print(Panel.fit(
            f"[bold]Session Information[/bold]\n\n"
            f" Date: {session_info['session_date']}\n"
            f" Deliverables: {session_info['recovered_deliverables']}\n"
            f" Conversations: {session_info['conversation_entries']}\n"
            f" Active Context: {len(session_info['active_context'])}\n\n"
            f"[dim]Context Summary:[/dim]\n{session_info.get('context_summary', 'No active context')}",
            title=" AI Working Journal"
        ))

    asyncio.run(show_session())


if __name__ == "__main__":
    app()