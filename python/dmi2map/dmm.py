"""Emit BYOND .dmm text matching DMI2Map.dm conventions."""

from __future__ import annotations

ALPHABET = list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")


def make_keys(count: int) -> list[str]:
    """Generate `count` two-letter keys in BYOND tool order (aa, ab, ... aZ, ba, ...)."""
    keys: list[str] = []
    ix = iy = 0
    for _ in range(count):
        keys.append(ALPHABET[ix] + ALPHABET[iy])
        iy += 1
        if iy >= len(ALPHABET):
            iy = 0
            ix += 1
            if ix >= len(ALPHABET):
                raise ValueError("Too many unique tiles for two-letter DMM keys (max 52*52)")
    return keys


def build_dmm(
    tile_ids_row_major_bottom_first: list[str],
    width: int,
) -> str:
    """
    Build .dmm contents.

    `tile_ids_row_major_bottom_first` matches BYOND FixDMI IconStates order:
    for j in 0..height-1 (bottom row first): for i in 0..width-1.

    Keys are assigned in that discovery order (unique ids only).
    Grid assembly mirrors DMI2Map.dm: walk list backwards, flush rows of `width`,
    reverse each row → top-to-bottom, left-to-right in the file.
    """
    if width <= 0:
        raise ValueError("width must be positive")
    if len(tile_ids_row_major_bottom_first) % width != 0:
        raise ValueError("tile count is not divisible by width")

    key_by_id: dict[str, str] = {}
    tile_keys: list[str] = []
    templates: list[str] = []
    ix = iy = 0

    for tid in tile_ids_row_major_bottom_first:
        existing = key_by_id.get(tid)
        if existing is not None:
            tile_keys.append(existing)
            continue
        if ix >= len(ALPHABET):
            raise ValueError("Too many unique tiles for two-letter DMM keys")
        key = ALPHABET[ix] + ALPHABET[iy]
        key_by_id[tid] = key
        tile_keys.append(key)
        templates.append(
            f'"{key}"=(/turf/{{name="{tid}"; icon = \'INSERT_DMI_HERE\'; '
            f'icon_state = "{tid}"}},/area)'
        )
        iy += 1
        if iy >= len(ALPHABET):
            iy = 0
            ix += 1

    # Reverse-walk assembly (same as DMI2Map.dm)
    rows_out: list[str] = []
    row: list[str] = []
    counter = 0
    for i in range(len(tile_keys) - 1, -1, -1):
        counter += 1
        if counter > width:
            counter = 1
            rows_out.append("".join(reversed(row)))
            row = []
        row.append(tile_keys[i])
    if row:
        rows_out.append("".join(reversed(row)))

    parts = list(templates)
    parts.append("")
    parts.append('(1,1,1) = {"')
    parts.extend(rows_out)
    parts.append('"}')
    return "\n".join(parts) + "\n"
