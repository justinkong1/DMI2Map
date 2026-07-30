"""FastAPI web UI for DMI2Map."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import paths as pathutil
from .convert import convert_selection
from .tileset import Tileset

STATIC_DIR = Path(__file__).resolve().parent.parent / "web" / "static"


class TilesetBody(BaseModel):
    action: str = Field(description="'new' or 'load'")
    name: str


class ConvertBody(BaseModel):
    source: str = Field(description="'png' or 'dmi'")
    selection: str
    duplicates: bool = False


class OpenBody(BaseModel):
    folder: str = Field(description="PNG | DMI | Maps | Tilesets | or relative path")


class Session:
    def __init__(self, root: Path):
        self.root = root
        self.tileset = Tileset()
        self.tileset_ready = False
        self.lock = threading.Lock()
        self.busy = False
        self.logs: list[str] = []
        self.last_results: list[dict] = []

    def log(self, msg: str) -> None:
        self.logs.append(msg)
        if len(self.logs) > 2000:
            self.logs = self.logs[-1500:]


def create_app(root: Path | None = None) -> FastAPI:
    root = (root or pathutil.default_workspace()).resolve()
    pathutil.ensure_workspace(root)
    session = Session(root)

    app = FastAPI(title="DMI2Map", version="1.0.0")
    if STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index() -> FileResponse:
        index_path = STATIC_DIR / "index.html"
        if not index_path.is_file():
            raise HTTPException(500, "UI assets missing")
        return FileResponse(index_path)

    @app.get("/api/status")
    def status() -> dict[str, Any]:
        return {
            "root": str(session.root),
            "busy": session.busy,
            "tileset_ready": session.tileset_ready,
            "tileset_name": session.tileset.name if session.tileset_ready else None,
            "tileset_count": session.tileset.count if session.tileset_ready else 0,
            "png": pathutil.list_png_entries(session.root),
            "dmi": pathutil.list_dmi_entries(session.root),
            "tilesets": pathutil.list_tilesets(session.root),
            "log_len": len(session.logs),
        }

    @app.get("/api/logs")
    def logs(after: int = 0) -> dict[str, Any]:
        lines = session.logs[after:]
        return {"after": after, "next": len(session.logs), "lines": lines}

    @app.post("/api/tileset")
    def set_tileset(payload: TilesetBody = Body(...)) -> dict[str, Any]:
        name = payload.name.strip()
        if not name:
            raise HTTPException(400, "Tileset name required")
        if not name.endswith(".dmi"):
            name += ".dmi"
        with session.lock:
            if payload.action == "new":
                session.tileset = Tileset(name=name)
                session.tileset_ready = True
                session.log(f"Set tileset to {name} ( 0 states ).")
            elif payload.action == "load":
                path = session.root / "Tilesets" / name
                if not path.is_file():
                    raise HTTPException(404, f"Tileset not found: {name}")
                try:
                    loaded = Tileset()
                    loaded.load(path)
                except Exception as exc:  # noqa: BLE001 — return readable API error
                    raise HTTPException(
                        400, f"Failed to load tileset {name}: {exc}"
                    ) from exc
                session.tileset = loaded
                session.tileset_ready = True
                session.log(
                    f"Set tileset to {session.tileset.name} ( {session.tileset.count} states )."
                )
            else:
                raise HTTPException(400, "action must be 'new' or 'load'")
        return {
            "ok": True,
            "tileset_name": session.tileset.name,
            "tileset_count": session.tileset.count,
        }

    @app.post("/api/convert")
    def convert(payload: ConvertBody = Body(...)) -> dict[str, Any]:
        if not session.tileset_ready:
            raise HTTPException(400, "Set a tileset first")
        if payload.source not in ("png", "dmi"):
            raise HTTPException(400, "source must be png or dmi")
        with session.lock:
            if session.busy:
                raise HTTPException(409, "Conversion already running")
            session.busy = True
            session.logs.clear()
            session.last_results = []

        def run() -> None:
            try:
                results = convert_selection(
                    session.root,
                    payload.selection,
                    session.tileset,
                    source=payload.source,
                    force_duplicates=payload.duplicates,
                    progress=session.log,
                )
                session.last_results = results
            except Exception as exc:  # noqa: BLE001 — surface to UI log
                session.log(f"Error: {exc}")
            finally:
                with session.lock:
                    session.busy = False

        threading.Thread(target=run, daemon=True).start()
        return {"ok": True, "started": True}

    @app.post("/api/open-folder")
    def open_folder(payload: OpenBody = Body(...)) -> dict[str, Any]:
        target = (session.root / payload.folder).resolve()
        try:
            target.relative_to(session.root)
        except ValueError as exc:
            raise HTTPException(400, "Path outside workspace") from exc
        if not target.exists():
            target.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(target)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target)])
        return {"ok": True, "path": str(target)}

    @app.get("/api/results")
    def results() -> dict[str, Any]:
        return {"busy": session.busy, "results": session.last_results}

    return app


def main() -> None:
    import uvicorn

    root = pathutil.default_workspace()
    app = create_app(root)
    uvicorn.run(app, host="127.0.0.1", port=8765)


if __name__ == "__main__":
    main()
