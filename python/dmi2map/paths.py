"""Workspace path helpers matching the BYOND tool folder layout."""

from __future__ import annotations

from pathlib import Path


def ensure_workspace(root: Path) -> None:
    for name in ("PNG", "DMI", "Maps", "Tilesets"):
        (root / name).mkdir(parents=True, exist_ok=True)


def list_tilesets(root: Path) -> list[str]:
    folder = root / "Tilesets"
    if not folder.is_dir():
        return []
    return sorted(p.name for p in folder.glob("*.dmi"))


def list_png_entries(root: Path) -> list[str]:
    """Top-level names under PNG/ (files and folders), like flist()."""
    folder = root / "PNG"
    if not folder.is_dir():
        return []
    entries: list[str] = []
    for p in sorted(folder.iterdir()):
        if p.is_dir():
            entries.append(p.name + "/")
        elif p.suffix.lower() == ".png":
            entries.append(p.name)
    return entries


def list_dmi_entries(root: Path) -> list[str]:
    folder = root / "DMI"
    if not folder.is_dir():
        return []
    entries: list[str] = []
    for p in sorted(folder.iterdir()):
        if p.is_dir():
            entries.append(p.name + "/")
        elif p.suffix.lower() == ".dmi":
            entries.append(p.name)
    return entries


def iter_pngs(root: Path, relative: str) -> list[Path]:
    """Expand a flist-style selection into concrete PNG paths."""
    base = root / "PNG" / relative.rstrip("/")
    if relative.endswith("/") or base.is_dir():
        return sorted(p for p in base.rglob("*.png") if p.is_file())
    path = root / "PNG" / relative
    return [path] if path.is_file() else []


def iter_dmis(root: Path, relative: str) -> list[Path]:
    base = root / "DMI" / relative.rstrip("/")
    if relative.endswith("/") or base.is_dir():
        return sorted(p for p in base.rglob("*.dmi") if p.is_file())
    path = root / "DMI" / relative
    return [path] if path.is_file() else []


def png_to_dmi_path(root: Path, png_path: Path) -> Path:
    rel = png_path.relative_to(root / "PNG")
    return root / "DMI" / rel.with_suffix(".dmi")


def dmi_to_map_path(root: Path, dmi_path: Path) -> Path:
    """Maps/<path under workspace mirroring DMI location>.dmm — same as BYOND tool."""
    try:
        rel = dmi_path.relative_to(root)
    except ValueError:
        rel = Path("DMI") / dmi_path.name
    # BYOND: Maps/[folder][basename without .dmi].dmm where folder includes DMI/...
    return root / "Maps" / rel.with_suffix(".dmm")
