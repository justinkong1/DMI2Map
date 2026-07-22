"""Core conversion pipeline: PNG/DMI → tiles → .dmm + tileset."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PIL import Image

from . import paths as pathutil
from .dmi import load_dmi, sheet_as_dmi
from .dmm import build_dmm
from .tileset import Tileset

ProgressCb = Callable[[str], None]


def _log(cb: ProgressCb | None, msg: str) -> None:
    if cb:
        cb(msg)


def scale_2x(image: Image.Image) -> Image.Image:
    w, h = image.size
    return image.resize((w * 2, h * 2), Image.Resampling.NEAREST)


def extract_tiles_byond_order(image: Image.Image, tile_size: int = 32) -> tuple[list[Image.Image], int, int]:
    """
    Split a full map image into 32x32 tiles in BYOND FixDMI order.

    BYOND icon (1,1) is the bottom-left of the image. FixDMI iterates
    j (from bottom) outer, i (left→right) inner, naming states \"i,j\".
    Pillow uses top-left origin, so j=0 is the bottom row of the PNG.
    """
    img = image.convert("RGBA")
    w, h = img.size
    if w % tile_size or h % tile_size:
        raise ValueError(
            f"Image size {w}x{h} is not divisible by tile size {tile_size}"
        )
    tiles_x = w // tile_size
    tiles_y = h // tile_size
    tiles: list[Image.Image] = []
    for j in range(tiles_y):  # j=0 → bottom row
        pillow_y = h - (j + 1) * tile_size
        for i in range(tiles_x):
            x0 = i * tile_size
            tiles.append(img.crop((x0, pillow_y, x0 + tile_size, pillow_y + tile_size)))
    return tiles, tiles_x, tiles_y


def png_to_scaled_dmi(
    root: Path,
    png_path: Path,
    progress: ProgressCb | None = None,
) -> Path:
    dest = pathutil.png_to_dmi_path(root, png_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.open(png_path).convert("RGBA")
    scaled = scale_2x(img)
    sheet_as_dmi(scaled, dest)
    _log(
        progress,
        f"  saved {dest.relative_to(root)} ({img.width}x{img.height} -> {scaled.width}x{scaled.height})",
    )
    return dest


def image_to_map(
    root: Path,
    image: Image.Image,
    out_dmm: Path,
    tileset: Tileset,
    force_duplicates: bool = False,
    progress: ProgressCb | None = None,
    from_png: bool = False,
) -> dict:
    tiles, width, height = extract_tiles_byond_order(image, tileset.tile_size)
    total = len(tiles)
    map_step = "[3/5]" if from_png else "[2/4]"
    write_step = "[4/5]" if from_png else "[3/4]"
    done_step = "[5/5]" if from_png else "[4/4]"

    _log(progress, f"{map_step} Mapping tiles (0/{total}, tileset size {tileset.count})...")

    tile_ids: list[str] = []
    reused = added = 0
    for n, tile in enumerate(tiles, start=1):
        tid, was_added = tileset.add_tile(tile, force_new=force_duplicates)
        tile_ids.append(tid)
        if was_added:
            added += 1
        else:
            reused += 1
        if n % 50 == 0 or n == total:
            _log(
                progress,
                f"  ... tile {n}/{total} (reused {reused}, new {added}, tileset {tileset.count})",
            )

    dmm_text = build_dmm(tile_ids, width)
    out_dmm.parent.mkdir(parents=True, exist_ok=True)
    _log(progress, f"{write_step} Writing {out_dmm.relative_to(root)}")
    out_dmm.write_text(dmm_text, encoding="utf-8", newline="\n")
    _log(
        progress,
        f"{done_step} Done: {out_dmm.name} (reused {reused}, new {added}, tileset {tileset.count})",
    )
    return {
        "dmm": str(out_dmm),
        "width": width,
        "height": height,
        "tiles": total,
        "reused": reused,
        "added": added,
        "tileset_count": tileset.count,
    }


def convert_dmi_file(
    root: Path,
    dmi_path: Path,
    tileset: Tileset,
    force_duplicates: bool = False,
    progress: ProgressCb | None = None,
    from_png: bool = False,
) -> dict:
    fix_step = "[2/5]" if from_png else "[1/4]"
    if not from_png:
        _log(progress, f"=== Convert: {dmi_path.relative_to(root)} ===")
    _log(progress, f"{fix_step} Fixing DMI (splitting tiles)...")

    dmi = load_dmi(dmi_path)
    # Full-map DMI is typically one large state; use the sheet image itself.
    if len(dmi.states) == 1 and dmi.width > tileset.tile_size:
        image = dmi.states[0].images[0]
    else:
        # Already-split multi-state map: rebuild sheet from states named "i,j"
        # or fall back to opening the raw PNG sheet.
        image = Image.open(dmi_path).convert("RGBA")
        # If metadata says tile-sized states, compose isn't needed — raw sheet
        # for single large icon; for weird cases use the opened image dimensions.
        if dmi.width == tileset.tile_size and dmi.height == tileset.tile_size:
            # Reconstruct full map from "i,j" states if present
            coords: list[tuple[int, int, Image.Image]] = []
            for st in dmi.states:
                if "," in st.name and st.images:
                    try:
                        ix, jy = st.name.split(",", 1)
                        coords.append((int(ix), int(jy), st.images[0]))
                    except ValueError:
                        pass
            if coords:
                max_x = max(c[0] for c in coords) + 1
                max_y = max(c[1] for c in coords) + 1
                image = Image.new(
                    "RGBA",
                    (max_x * tileset.tile_size, max_y * tileset.tile_size),
                    (0, 0, 0, 0),
                )
                for ix, jy, im in coords:
                    # BYOND j=0 is bottom → pillow y from top
                    pillow_y = (max_y - 1 - jy) * tileset.tile_size
                    image.paste(im, (ix * tileset.tile_size, pillow_y))

    out_dmm = pathutil.dmi_to_map_path(root, dmi_path)
    return image_to_map(
        root,
        image,
        out_dmm,
        tileset,
        force_duplicates=force_duplicates,
        progress=progress,
        from_png=from_png,
    )


def convert_png_file(
    root: Path,
    png_path: Path,
    tileset: Tileset,
    force_duplicates: bool = False,
    progress: ProgressCb | None = None,
    save_intermediate_dmi: bool = True,
) -> dict:
    _log(progress, f"=== Convert: {png_path.relative_to(root)} ===")
    _log(progress, "[1/5] PNG -> 2x DMI...")
    img = Image.open(png_path).convert("RGBA")
    scaled = scale_2x(img)

    if save_intermediate_dmi:
        dmi_path = pathutil.png_to_dmi_path(root, png_path)
        dmi_path.parent.mkdir(parents=True, exist_ok=True)
        sheet_as_dmi(scaled, dmi_path)
        _log(
            progress,
            f"  saved {dmi_path.relative_to(root)} ({img.width}x{img.height} -> {scaled.width}x{scaled.height})",
        )
        return convert_dmi_file(
            root,
            dmi_path,
            tileset,
            force_duplicates=force_duplicates,
            progress=progress,
            from_png=True,
        )

    # Direct path without writing intermediate (still place DMM under Maps/DMI/...)
    fake_dmi = pathutil.png_to_dmi_path(root, png_path)
    out_dmm = pathutil.dmi_to_map_path(root, fake_dmi)
    _log(progress, "[2/5] Fixing DMI (splitting tiles)...")
    return image_to_map(
        root,
        scaled,
        out_dmm,
        tileset,
        force_duplicates=force_duplicates,
        progress=progress,
        from_png=True,
    )


def convert_selection(
    root: Path,
    selection: str,
    tileset: Tileset,
    source: str = "png",
    force_duplicates: bool = False,
    progress: ProgressCb | None = None,
) -> list[dict]:
    """
    Convert a flist-style selection under PNG/ or DMI/.
    `selection` is relative like 'SafariZoneExterior/' or '1.png'.
    """
    root = Path(root)
    pathutil.ensure_workspace(root)
    results: list[dict] = []

    if source == "png":
        mode = "always new tiles" if force_duplicates else "reuse duplicates"
        _log(progress, f"=== ConvertPNG start ({mode}) ===")
        files = pathutil.iter_pngs(root, selection)
        if not files:
            raise FileNotFoundError(f"No PNG files found for selection: {selection}")
        for f in files:
            results.append(
                convert_png_file(
                    root, f, tileset, force_duplicates=force_duplicates, progress=progress
                )
            )
    else:
        mode = "always new tiles" if force_duplicates else "reuse duplicates"
        _log(progress, f"=== Convert start ({mode}) ===")
        files = pathutil.iter_dmis(root, selection)
        if not files:
            raise FileNotFoundError(f"No DMI files found for selection: {selection}")
        for f in files:
            results.append(
                convert_dmi_file(
                    root, f, tileset, force_duplicates=force_duplicates, progress=progress
                )
            )

    out = tileset.save(root / "Tilesets")
    _log(progress, f"Tileset {tileset.name} saved ( {tileset.count} states ).")
    _log(progress, "=== Finished batch ===")
    for r in results:
        r["tileset_path"] = str(out)
    return results
