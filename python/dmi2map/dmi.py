"""Read and write BYOND .dmi files (PNG + Description zTXt metadata)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from PIL import Image
from PIL.PngImagePlugin import PngInfo


@dataclass
class DmiState:
    name: str
    dirs: int = 1
    frames: int = 1
    delay: list[float] | None = None
    # First-frame image for each direction is enough for this tool; we store all frames.
    images: list[Image.Image] = field(default_factory=list)

    @property
    def slot_count(self) -> int:
        return self.dirs * self.frames


@dataclass
class Dmi:
    width: int
    height: int
    states: list[DmiState] = field(default_factory=list)

    def state_names(self) -> list[str]:
        return [s.name for s in self.states]

    def get_state(self, name: str) -> DmiState | None:
        for s in self.states:
            if s.name == name:
                return s
        return None

    def first_frame(self, name: str) -> Image.Image | None:
        st = self.get_state(name)
        if not st or not st.images:
            return None
        return st.images[0]


_STATE_RE = re.compile(r'^state\s*=\s*"(.*)"\s*$')
_KV_RE = re.compile(r"^\t(\w+)\s*=\s*(.+)\s*$")
_HEADER_WH = re.compile(r"^\t(width|height)\s*=\s*(\d+)\s*$")


def _parse_description(desc: str) -> tuple[int, int, list[dict]]:
    """Return (width, height, list of state dicts)."""
    lines = desc.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    width = height = 32
    states: list[dict] = []
    current: dict | None = None
    in_header = True

    for raw in lines:
        line = raw.rstrip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("version"):
            continue

        m_wh = _HEADER_WH.match(line)
        if in_header and m_wh:
            if m_wh.group(1) == "width":
                width = int(m_wh.group(2))
            else:
                height = int(m_wh.group(2))
            continue

        m_state = _STATE_RE.match(line)
        if m_state:
            in_header = False
            if current is not None:
                states.append(current)
            current = {
                "name": m_state.group(1),
                "dirs": 1,
                "frames": 1,
                "delay": None,
            }
            continue

        m_kv = _KV_RE.match(line)
        if m_kv and current is not None:
            key, val = m_kv.group(1), m_kv.group(2).strip()
            if key in ("dirs", "frames"):
                current[key] = int(val)
            elif key == "delay":
                current["delay"] = [float(x) for x in val.split(",")]
            continue

    if current is not None:
        states.append(current)
    return width, height, states


def _build_description(dmi: Dmi) -> str:
    lines = [
        "# BEGIN DMI",
        "version = 4.0",
        f"\twidth = {dmi.width}",
        f"\theight = {dmi.height}",
    ]
    for st in dmi.states:
        # Escape quotes in state names if any
        name = st.name.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'state = "{name}"')
        lines.append(f"\tdirs = {st.dirs}")
        lines.append(f"\tframes = {st.frames}")
        if st.delay and st.frames > 1:
            delay = ",".join(str(int(d) if d == int(d) else d) for d in st.delay)
            lines.append(f"\tdelay = {delay}")
    lines.append("# END DMI")
    lines.append("")
    return "\n".join(lines)


def load_dmi(path: str | Path) -> Dmi:
    path = Path(path)
    img = Image.open(path).convert("RGBA")
    desc = img.info.get("Description") or ""
    if isinstance(desc, bytes):
        desc = desc.decode("utf-8", errors="replace")

    if desc.strip():
        tw, th, state_defs = _parse_description(desc)
    else:
        tw, th = img.size
        state_defs = [{"name": "", "dirs": 1, "frames": 1, "delay": None}]

    sheet_w, sheet_h = img.size
    icons_per_row = max(1, sheet_w // tw)

    dmi = Dmi(width=tw, height=th)
    index = 0
    for sd in state_defs:
        slots = sd["dirs"] * sd["frames"]
        frames: list[Image.Image] = []
        for _ in range(slots):
            col = index % icons_per_row
            row = index // icons_per_row
            x0 = col * tw
            y0 = row * th
            frames.append(img.crop((x0, y0, x0 + tw, y0 + th)).copy())
            index += 1
        dmi.states.append(
            DmiState(
                name=sd["name"],
                dirs=sd["dirs"],
                frames=sd["frames"],
                delay=sd["delay"],
                images=frames,
            )
        )
    return dmi


def save_dmi(dmi: Dmi, path: str | Path, icons_per_row: int | None = None) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    total_slots = sum(st.slot_count for st in dmi.states)
    if total_slots == 0:
        # Empty tileset — write a minimal 32x32 transparent DMI
        sheet = Image.new("RGBA", (dmi.width, dmi.height), (0, 0, 0, 0))
        meta = PngInfo()
        meta.add_text("Description", _build_description(dmi), zip=True)
        sheet.save(path, "PNG", pnginfo=meta)
        return

    if icons_per_row is None:
        # Prefer a roughly square sheet; keep existing feel (~40 wide for large sets)
        import math

        icons_per_row = max(1, math.ceil(math.sqrt(total_slots)))
        # Cap width so sheets don't become absurdly wide for tiny sets
        icons_per_row = max(1, min(icons_per_row, max(total_slots, 1)))

    rows = (total_slots + icons_per_row - 1) // icons_per_row
    sheet = Image.new(
        "RGBA",
        (icons_per_row * dmi.width, rows * dmi.height),
        (0, 0, 0, 0),
    )

    index = 0
    for st in dmi.states:
        for frame in st.images:
            col = index % icons_per_row
            row = index // icons_per_row
            sheet.paste(frame.convert("RGBA"), (col * dmi.width, row * dmi.height))
            index += 1

    meta = PngInfo()
    meta.add_text("Description", _build_description(dmi), zip=True)
    sheet.save(path, "PNG", pnginfo=meta)


def sheet_as_dmi(image: Image.Image, path: str | Path | None = None) -> Dmi:
    """Wrap a full map image as a single-state DMI (matches BYOND png→dmi output)."""
    img = image.convert("RGBA")
    dmi = Dmi(width=img.width, height=img.height, states=[DmiState(name="", images=[img])])
    if path is not None:
        save_dmi(dmi, path, icons_per_row=1)
    return dmi


def states_from_images(
    images: Iterable[tuple[str, Image.Image]],
    tile_w: int = 32,
    tile_h: int = 32,
) -> Dmi:
    dmi = Dmi(width=tile_w, height=tile_h)
    for name, im in images:
        dmi.states.append(DmiState(name=name, images=[im.convert("RGBA")]))
    return dmi
