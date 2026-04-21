"""CLI entry point for all ingestion tasks.

Usage:
    python -m scripts.ingest <subcommand> [options]

Subcommands:
    whoami              Verify auth — print your Spotify display name.
    recent              Pull recent plays (up to last 50 per call, paginated forward).
    enrich              Fetch track/artist metadata + audio features for new plays.
    snapshot            Take a top-artists/tracks snapshot (weekly by default).
    all                 Run: recent → enrich → snapshot (respecting weekly guard).
    import-extended     Import Streaming_History_Audio_*.json from Spotify data export.
"""
import logging
import sys
from typing import Optional

import typer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)

app = typer.Typer(add_completion=False)


@app.command()
def whoami() -> None:
    """Verify auth — print your Spotify display name."""
    from wrapped.auth import get_client

    sp = get_client()
    me = sp.me()
    typer.echo(f"Authenticated as: {me['display_name']} ({me['id']})")


@app.command()
def recent() -> None:
    """Pull recently played tracks into local DB."""
    from wrapped.ingest.recent import run

    new = run()
    typer.echo(f"Done — {new} new plays ingested.")


@app.command()
def enrich() -> None:
    """Fetch track/artist metadata and audio features for unenriched plays."""
    from wrapped.ingest.enrich import run

    run()
    typer.echo("Enrichment complete.")


@app.command()
def snapshot(force: bool = typer.Option(False, "--force", help="Skip the weekly guard and snapshot now.")) -> None:
    """Capture a weekly snapshot of your top artists and tracks."""
    from wrapped.ingest.snapshot import run

    taken = run(force=force)
    if taken:
        typer.echo("Snapshot captured.")
    else:
        typer.echo("Snapshot skipped (taken recently). Use --force to override.")


@app.command()
def all() -> None:
    """Run the full ingestion pipeline: recent → enrich → snapshot."""
    from wrapped.ingest import enrich as enrich_mod
    from wrapped.ingest import recent as recent_mod
    from wrapped.ingest import snapshot as snapshot_mod

    typer.echo("→ Pulling recent plays...")
    new = recent_mod.run()
    typer.echo(f"  {new} new plays.")

    typer.echo("→ Enriching tracks & artists...")
    enrich_mod.run()

    typer.echo("→ Checking snapshot...")
    taken = snapshot_mod.run()
    if taken:
        typer.echo("  Snapshot captured.")
    else:
        typer.echo("  Snapshot skipped (taken recently).")

    typer.echo("Done.")


@app.command("import-extended")
def import_extended(
    path: str = typer.Argument(..., help="Path to a directory of Streaming_History_Audio_*.json files, or a single file."),
) -> None:
    """Import Spotify Extended Streaming History JSON files."""
    from wrapped.ingest.extended import run

    count = run(path)
    typer.echo(f"Imported {count} plays from extended history.")
    typer.echo("Run `enrich` next to fetch metadata for the new tracks.")


if __name__ == "__main__":
    app()
