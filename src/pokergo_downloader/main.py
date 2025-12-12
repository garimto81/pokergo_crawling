"""
PokerGO Crawler CLI

DB 파싱 전용 - 메타데이터 수집 및 URL 목록 생성
다운로드는 4K Downloader 등 외부 프로그램 사용

Usage:
    pokergo crawl youtube          # YouTube 채널 크롤링
    pokergo crawl youtube --full   # 전체 메타데이터 포함
    pokergo list videos            # DB 영상 목록
    pokergo export-urls            # 4K Downloader용 URL 목록 생성
    pokergo stats                  # 통계
"""

import logging
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from pokergo_downloader.config import settings
from pokergo_downloader.database.models import DownloadStatus, Source
from pokergo_downloader.database.repository import Repository

# CLI App
app = typer.Typer(
    name="pokergo",
    help="PokerGO Crawler - DB 파싱 전용 (다운로드는 4K Downloader 사용)",
    no_args_is_help=True,
)

# Sub-commands
crawl_app = typer.Typer(help="Crawl metadata from sources")
list_app = typer.Typer(help="List content from database")
app.add_typer(crawl_app, name="crawl")
app.add_typer(list_app, name="list")

# Rich console
console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Setup logging with Rich handler."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, show_time=False, show_path=False)],
    )


def get_repo() -> Repository:
    """Get repository instance."""
    settings.ensure_directories()
    repo = Repository(str(settings.db_path))
    repo.init_db()
    return repo


# ==================== Crawl Commands ====================


@crawl_app.command("youtube")
def crawl_youtube(
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max videos to crawl"),
    full: bool = typer.Option(False, "--full", "-f", help="Extract full metadata (slower)"),
    playlists: bool = typer.Option(True, "--playlists/--no-playlists", help="Include playlists"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """
    Crawl YouTube PokerGO channel metadata.

    Phase 1: Extracts video metadata without downloading.
    """
    setup_logging(verbose)
    repo = get_repo()

    # Import here to avoid circular imports
    from pokergo_downloader.crawler.youtube import YouTubeCrawler

    crawler = YouTubeCrawler(repo, verbose=verbose)

    console.print("[cyan]Crawling YouTube channel...[/cyan]")

    result = crawler.full_sync(
        video_limit=limit,
        full_metadata=full,
        include_playlists=playlists,
    )

    if result["success"]:
        console.print("\n[green]Crawl completed successfully![/green]\n")

        table = Table(title="Crawl Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Videos Found", str(result["videos"]["total"]))
        table.add_row("New Videos", str(result["videos"]["new"]))
        table.add_row("Updated Videos", str(result["videos"]["updated"]))
        if "playlists" in result:
            table.add_row("Playlists", str(result["playlists"]))

        console.print(table)
    else:
        console.print(f"\n[red]Crawl failed: {result.get('error')}[/red]")
        raise typer.Exit(1)


@crawl_app.command("video")
def crawl_single_video(
    video_id: str = typer.Argument(..., help="YouTube video ID or URL"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Crawl metadata for a single YouTube video."""
    setup_logging(verbose)
    repo = get_repo()

    from pokergo_downloader.crawler.youtube import YouTubeCrawler

    crawler = YouTubeCrawler(repo, verbose=verbose)

    console.print(f"Crawling video: {video_id}")
    video_data = crawler.crawl_video_metadata(video_id)

    if video_data:
        # Get or create channel
        channel = repo.get_channels_by_source(Source.YOUTUBE)
        if channel:
            channel_db_id = channel[0].id
        else:
            channel_db_id = crawler.sync_channel_to_db()

        if channel_db_id:
            repo.upsert_video(
                video_id=video_data["video_id"],
                channel_id=channel_db_id,
                source=Source.YOUTUBE,
                title=video_data["title"],
                description=video_data.get("description"),
                thumbnail_url=video_data.get("thumbnail_url"),
                duration=video_data.get("duration"),
                view_count=video_data.get("view_count"),
                like_count=video_data.get("like_count"),
                upload_date=video_data.get("upload_date"),
                tags=video_data.get("tags"),
                available_qualities=video_data.get("available_qualities"),
            )
            console.print(f"[green]Saved: {video_data['title']}[/green]")
        else:
            console.print("[red]Failed to get channel info[/red]")
    else:
        console.print("[red]Failed to extract video metadata[/red]")
        raise typer.Exit(1)


# ==================== List Commands ====================


@list_app.command("videos")
def list_videos(
    source: Optional[str] = typer.Option(
        None, "--source", "-s", help="Filter by source (youtube, pokergo)"
    ),
    status: Optional[str] = typer.Option(
        None, "--status", help="Filter by download status (pending, completed, failed)"
    ),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of videos to show"),
) -> None:
    """List videos in the database."""
    repo = get_repo()

    # Parse filters
    source_filter = None
    if source:
        source_filter = Source.YOUTUBE if "youtube" in source.lower() else Source.POKERGO_WEB

    status_filter = None
    if status:
        status_filter = DownloadStatus(status.lower())

    videos = repo.get_videos(source=source_filter, download_status=status_filter, limit=limit)

    if not videos:
        console.print("[yellow]No videos found[/yellow]")
        return

    table = Table(title=f"Videos (showing {len(videos)})")
    table.add_column("ID", style="dim", width=12)
    table.add_column("Title", style="cyan", max_width=50)
    table.add_column("Source", style="green", width=10)
    table.add_column("Duration", width=10)
    table.add_column("Status", width=12)

    for video in videos:
        duration_str = ""
        if video.duration:
            mins, secs = divmod(video.duration, 60)
            duration_str = f"{mins}:{secs:02d}"

        table.add_row(
            video.video_id[:11] + "...",
            video.title[:47] + "..." if len(video.title) > 50 else video.title,
            video.source.value,
            duration_str,
            video.download_status.value,
        )

    console.print(table)


@list_app.command("playlists")
def list_playlists() -> None:
    """List playlists in the database."""
    repo = get_repo()
    playlists = repo.get_playlists()

    if not playlists:
        console.print("[yellow]No playlists found[/yellow]")
        return

    table = Table(title="Playlists")
    table.add_column("ID", style="dim")
    table.add_column("Title", style="cyan")
    table.add_column("Videos", style="green")
    table.add_column("Source")

    for playlist in playlists:
        table.add_row(
            playlist.playlist_id,
            playlist.title,
            str(playlist.video_count or "?"),
            playlist.source.value,
        )

    console.print(table)


# ==================== Stats Command ====================


@app.command("stats")
def show_stats() -> None:
    """Show database statistics."""
    repo = get_repo()
    stats = repo.get_stats()

    table = Table(title="Database Statistics")
    table.add_column("Category", style="cyan")
    table.add_column("Count", style="green")

    table.add_row("Channels", str(stats["channels"]))
    table.add_row("Playlists", str(stats["playlists"]))
    table.add_row("─" * 20, "─" * 10)
    table.add_row("Total Videos", str(stats["videos"]["total"]))
    table.add_row("  YouTube", str(stats["videos"]["youtube"]))
    table.add_row("  PokerGO", str(stats["videos"]["pokergo"]))
    table.add_row("─" * 20, "─" * 10)
    table.add_row("Downloads Pending", str(stats["downloads"]["pending"]))
    table.add_row("Downloads Completed", str(stats["downloads"]["completed"]))
    table.add_row("Downloads Failed", str(stats["downloads"]["failed"]))

    console.print(table)


# ==================== Init Command ====================


@app.command("init")
def init_db() -> None:
    """Initialize the database."""
    repo = get_repo()
    console.print(f"[green]Database initialized at: {settings.db_path}[/green]")


# ==================== Export Command ====================


@app.command("export")
def export_data(
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Filter by source"),
    snapshot: bool = typer.Option(False, "--snapshot", help="Create timestamped snapshot"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """
    Export data to chunked JSON files (5MB per file).

    Files are saved to data/exports/:
    - index.json: Searchable index with video_id → title mapping
    - channel.json: Channel info
    - videos/: Chunked video files (videos_001.json, videos_002.json, ...)
    - playlists/: Playlist data
    - urls/: 4K Downloader URL list
    """
    setup_logging(verbose)
    repo = get_repo()

    source_filter = None
    if source:
        source_filter = Source.YOUTUBE if "youtube" in source.lower() else Source.POKERGO_WEB

    from pokergo_downloader.exporter import ChunkedExporter

    exporter = ChunkedExporter(repo)

    console.print("[cyan]Exporting data (chunked mode)...[/cyan]")
    result = exporter.export_all(source=source_filter)

    # Show results
    table = Table(title="Export Results")
    table.add_column("Type", style="cyan")
    table.add_column("Count", style="green")
    table.add_column("Files", style="dim")

    videos_info = result.get("videos", {})
    table.add_row(
        "Videos",
        str(videos_info.get("total", 0)),
        f"{len(videos_info.get('files', []))} files",
    )

    playlists_info = result.get("playlists", {})
    table.add_row(
        "Playlists",
        str(playlists_info.get("total", 0)),
        playlists_info.get("file", "N/A"),
    )

    urls_info = result.get("urls", {})
    table.add_row(
        "URLs",
        str(urls_info.get("total", 0)),
        urls_info.get("file", "N/A"),
    )

    console.print(table)

    console.print(f"\n[green]Index created: {settings.exports_path}/index.json[/green]")

    if snapshot:
        snapshot_path = exporter.create_snapshot(source=source_filter)
        console.print(f"[green]Snapshot created: {snapshot_path}[/green]")


# ==================== Export URLs Command (for 4K Downloader) ====================


@app.command("export-urls")
def export_urls(
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path (default: data/exports/urls/youtube_urls.txt)"),
    source: Optional[str] = typer.Option("youtube", "--source", "-s", help="Filter by source"),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max URLs to export"),
) -> None:
    """
    Export video URLs for 4K Downloader.

    4K Downloader에서 '링크 붙여넣기'로 사용할 URL 목록 생성.
    """
    repo = get_repo()

    source_filter = None
    if source:
        source_filter = Source.YOUTUBE if "youtube" in source.lower() else Source.POKERGO_WEB

    videos = repo.get_videos(source=source_filter, limit=limit)

    if not videos:
        console.print("[yellow]No videos found[/yellow]")
        return

    # Default output path
    if output is None:
        settings.ensure_directories()
        output = str(settings.urls_path / "youtube_urls.txt")
    else:
        from pathlib import Path
        Path(output).parent.mkdir(parents=True, exist_ok=True)

    urls = [video.url for video in videos]

    with open(output, "w", encoding="utf-8") as f:
        f.write("\n".join(urls))

    console.print(f"[green]Exported {len(urls)} URLs to: {output}[/green]")
    console.print(f"\n[cyan]4K Downloader 사용법:[/cyan]")
    console.print("  1. 4K Downloader 실행")
    console.print("  2. '링크 붙여넣기' 클릭")
    console.print(f"  3. {output} 파일 내용 붙여넣기")


# ==================== Search Command ====================


@app.command("search")
def search_videos(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max results"),
) -> None:
    """Search videos by title."""
    repo = get_repo()

    # Simple search using SQL LIKE
    from sqlalchemy import select

    from pokergo_downloader.database.models import Video

    with repo.get_session() as session:
        stmt = select(Video).where(Video.title.ilike(f"%{query}%")).limit(limit)
        videos = session.execute(stmt).scalars().all()

    if not videos:
        console.print(f"[yellow]No videos found for '{query}'[/yellow]")
        return

    table = Table(title=f"Search Results: '{query}'")
    table.add_column("ID", style="dim", width=12)
    table.add_column("Title", style="cyan", max_width=60)
    table.add_column("Duration", width=10)
    table.add_column("URL", style="dim", max_width=40)

    for video in videos:
        duration_str = ""
        if video.duration:
            mins, secs = divmod(video.duration, 60)
            duration_str = f"{mins}:{secs:02d}"

        table.add_row(
            video.video_id[:11] + "...",
            video.title[:57] + "..." if len(video.title) > 60 else video.title,
            duration_str,
            video.url[:37] + "..." if len(video.url) > 40 else video.url,
        )

    console.print(table)


if __name__ == "__main__":
    app()
