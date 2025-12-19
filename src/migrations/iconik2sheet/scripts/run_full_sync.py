"""Full sync CLI script."""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

from sync import FullSync


def main() -> None:
    """Run full sync."""
    console = Console()

    console.print("[bold]Iconik to Sheet - Full Sync[/bold]")
    console.print()

    sync = FullSync()
    result = sync.run()

    console.print()
    console.print("[bold]Summary:[/bold]")
    console.print(f"  Sync ID: {result['sync_id']}")
    console.print(f"  Status: {result['status']}")
    console.print(f"  Assets: {result['assets_new']}")


if __name__ == "__main__":
    main()
