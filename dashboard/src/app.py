"""FastAPI dashboard application for live arena events."""

from datetime import datetime
from pathlib import Path

import typer
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from common.src.event_emitter import DEFAULT_EVENTS_DIR, EVENTS_FILENAME, TIMESTAMP_FORMAT
from common.src.logging import setup_logging
from dashboard.src.event_watcher import ResetSignal, watch_events

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
DEFAULT_LOG_FILE = Path("data/logs/dashboard.log")
STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
INDEX_FILE = STATIC_DIR / "index.html"
RESET_MESSAGE = '{"type": "reset"}'
LATEST_RUN_ID = "latest"


def create_app(events_dir: Path = DEFAULT_EVENTS_DIR) -> FastAPI:
    """Create the dashboard FastAPI application.

    Args:
        events_dir: Parent directory containing timestamped run subdirectories.
    """
    app = FastAPI(title="AgentShield Arena Dashboard")
    app.state.events_dir = events_dir

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    async def index() -> FileResponse:
        """Serve the dashboard single-page application."""
        return FileResponse(INDEX_FILE)

    @app.get("/api/runs")
    async def list_runs() -> list[dict[str, str]]:
        """List available run directories, sorted newest-first."""
        return _list_runs(events_dir)

    @app.websocket("/ws")
    async def websocket_events(websocket: WebSocket, run: str = LATEST_RUN_ID) -> None:
        """Stream replayed and live arena events to a connected browser.

        Args:
            websocket: The WebSocket connection.
            run: Run identifier — a timestamp directory name or ``"latest"``.
        """
        events_file = _resolve_events_file(events_dir, run)
        await websocket.accept()

        try:
            async for message in watch_events(events_file):
                if isinstance(message, ResetSignal):
                    await websocket.send_text(RESET_MESSAGE)
                else:
                    await websocket.send_text(message.model_dump_json())
        except WebSocketDisconnect:
            return

    return app


def _list_runs(events_dir: Path) -> list[dict[str, str]]:
    """Scan *events_dir* for timestamped run directories.

    Returns:
        List of ``{"id": "<dir_name>", "timestamp": "<ISO 8601>"}`` dicts,
        sorted newest-first.
    """
    if not events_dir.is_dir():
        return []

    runs: list[dict[str, str]] = []
    for entry in events_dir.iterdir():
        if not entry.is_dir() or entry.is_symlink():
            continue
        events_file = entry / EVENTS_FILENAME
        if not events_file.exists():
            continue
        try:
            ts = datetime.strptime(entry.name, TIMESTAMP_FORMAT)
        except ValueError:
            continue
        runs.append({"id": entry.name, "timestamp": ts.isoformat()})

    runs.sort(key=lambda r: r["id"], reverse=True)
    return runs


def _resolve_events_file(events_dir: Path, run_id: str) -> Path:
    """Turn a run identifier into a concrete JSONL file path.

    Args:
        events_dir: Parent directory for all runs.
        run_id: ``"latest"`` or a timestamp directory name.

    Returns:
        Path to the JSONL events file for the requested run.
    """
    if run_id == LATEST_RUN_ID:
        return events_dir / "latest" / EVENTS_FILENAME
    return events_dir / run_id / EVENTS_FILENAME


app = create_app()


def main(
    events_dir: Path = typer.Option(DEFAULT_EVENTS_DIR, help="Parent directory for timestamped run output."),
    host: str = typer.Option(DEFAULT_HOST, help="Host to bind the dashboard server to."),
    port: int = typer.Option(DEFAULT_PORT, help="Port to bind the dashboard server to."),
    reload: bool = typer.Option(False, help="Enable auto-reload on code changes."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable DEBUG-level logging."),
    log_file: Path = typer.Option(DEFAULT_LOG_FILE, help=f"Log file path. Defaults to {DEFAULT_LOG_FILE}."),
) -> None:
    """Run the dashboard development server."""
    setup_logging(verbose=verbose, log_file=log_file)

    if reload:
        uvicorn.run(
            "dashboard.src.app:app",
            host=host,
            port=port,
            reload=True,
            reload_dirs=["dashboard", "common"],
        )
    else:
        uvicorn.run(create_app(events_dir), host=host, port=port)


if __name__ == "__main__":
    typer.run(main)
