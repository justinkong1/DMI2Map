"""CLI: python -m dmi2map ..."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import paths as pathutil
from .convert import convert_selection
from .tileset import Tileset


def _default_root() -> Path:
    # python/dmi2map/__main__.py → repo root is parents[2]
    return Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dmi2map",
        description="Convert map PNGs/DMIs into BYOND .dmm files + a shared tileset DMI.",
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--root",
        type=Path,
        default=_default_root(),
        help="Workspace root containing PNG/, DMI/, Maps/, Tilesets/ (default: repo root)",
    )

    sub = p.add_subparsers(dest="command", required=True)

    conf = sub.add_parser("convert", parents=[common], help="Convert PNG or DMI selection")
    conf.add_argument(
        "source",
        choices=("png", "dmi"),
        help="Input type",
    )
    conf.add_argument(
        "selection",
        help="Relative path under PNG/ or DMI/ (file or folder, e.g. SafariZoneExterior/)",
    )
    conf.add_argument(
        "--tileset",
        required=True,
        help="Tileset name in Tilesets/ (e.g. outdoorTilesets.dmi) or new name to create",
    )
    conf.add_argument(
        "--new-tileset",
        action="store_true",
        help="Create a fresh empty tileset instead of loading an existing one",
    )
    conf.add_argument(
        "--duplicates",
        action="store_true",
        help="Always insert new tiles (no deduplication)",
    )

    sub.add_parser("list", parents=[common], help="List PNG/DMI/Tileset entries")

    ui = sub.add_parser("ui", parents=[common], help="Launch local web UI")
    ui.add_argument("--host", default="127.0.0.1")
    ui.add_argument("--port", type=int, default=8765)

    return p


def cmd_list(root: Path) -> int:
    pathutil.ensure_workspace(root)
    print(f"Root: {root}")
    print("\nTilesets/")
    for t in pathutil.list_tilesets(root) or ["(empty)"]:
        print(f"  {t}")
    print("\nPNG/")
    for t in pathutil.list_png_entries(root) or ["(empty)"]:
        print(f"  {t}")
    print("\nDMI/")
    for t in pathutil.list_dmi_entries(root) or ["(empty)"]:
        print(f"  {t}")
    return 0


def cmd_convert(args: argparse.Namespace) -> int:
    root: Path = args.root.resolve()
    pathutil.ensure_workspace(root)
    tileset = Tileset()
    ts_name = args.tileset if args.tileset.endswith(".dmi") else f"{args.tileset}.dmi"
    ts_path = root / "Tilesets" / ts_name

    if args.new_tileset or not ts_path.exists():
        if ts_path.exists() and args.new_tileset:
            print(f"Warning: overwriting logic — starting empty tileset named {ts_name}")
        tileset.name = ts_name
        tileset.clear()
        print(f"Using new tileset {ts_name}")
    else:
        tileset.load(ts_path)
        print(f"Loaded tileset {ts_name} ({tileset.count} states)")

    def progress(msg: str) -> None:
        print(msg)

    results = convert_selection(
        root,
        args.selection,
        tileset,
        source=args.source,
        force_duplicates=args.duplicates,
        progress=progress,
    )
    print(f"Converted {len(results)} file(s).")
    return 0


def cmd_ui(args: argparse.Namespace) -> int:
    import uvicorn

    root = args.root.resolve()
    from .web_app import create_app

    app = create_app(root)
    print(f"DMI2Map UI -> http://{args.host}:{args.port}  (root={root})")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "list":
        return cmd_list(args.root.resolve())
    if args.command == "convert":
        return cmd_convert(args)
    if args.command == "ui":
        return cmd_ui(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
