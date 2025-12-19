"""Connection test script."""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

load_dotenv()

from iconik import IconikClient
from sheets import SheetsWriter


def main() -> None:
    """Test connections to Iconik and Google Sheets."""
    console = Console()

    console.print("[bold]Connection Test[/bold]")
    console.print()

    table = Table(show_header=True, header_style="bold")
    table.add_column("Service")
    table.add_column("Status")

    # Test Iconik
    try:
        iconik = IconikClient()
        if iconik.health_check():
            table.add_row("Iconik API", "[green]Connected[/green]")
        else:
            table.add_row("Iconik API", "[red]Failed[/red]")
        iconik.close()
    except Exception as e:
        table.add_row("Iconik API", f"[red]Error: {e}[/red]")

    # Test Google Sheets
    try:
        sheets = SheetsWriter()
        if sheets.health_check():
            table.add_row("Google Sheets", "[green]Connected[/green]")
        else:
            table.add_row("Google Sheets", "[red]Failed[/red]")
    except Exception as e:
        table.add_row("Google Sheets", f"[red]Error: {e}[/red]")

    console.print(table)


if __name__ == "__main__":
    main()
