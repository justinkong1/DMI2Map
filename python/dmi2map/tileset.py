"""Tileset storage with hash-based deduplication."""

from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image

from .dmi import Dmi, DmiState, load_dmi, save_dmi


def tile_hash(image: Image.Image) -> str:
    img = image.convert("RGBA")
    return hashlib.blake2b(img.tobytes(), digest_size=16).hexdigest()


class Tileset:
    def __init__(self, name: str = "tileset.dmi", tile_size: int = 32):
        self.name = name if name.endswith(".dmi") else f"{name}.dmi"
        self.tile_size = tile_size
        self.dmi = Dmi(width=tile_size, height=tile_size)
        self._hash_to_id: dict[str, str] = {}
        self._next_id = 1

    @property
    def count(self) -> int:
        return len(self.dmi.states)

    def clear(self) -> None:
        self.dmi = Dmi(width=self.tile_size, height=self.tile_size)
        self._hash_to_id.clear()
        self._next_id = 1

    def load(self, path: str | Path) -> None:
        path = Path(path)
        self.name = path.name
        self.dmi = load_dmi(path)
        self.tile_size = self.dmi.width
        self._hash_to_id.clear()
        max_num = 0
        for st in self.dmi.states:
            if not st.images:
                continue
            h = tile_hash(st.images[0])
            # Prefer first state for a given hash (stable)
            if h not in self._hash_to_id:
                self._hash_to_id[h] = st.name
            if st.name.isdigit():
                max_num = max(max_num, int(st.name))
        self._next_id = max_num + 1 if max_num else self.count + 1

    def save(self, folder: str | Path) -> Path:
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        out = folder / self.name
        save_dmi(self.dmi, out)
        return out

    def find_duplicate(self, tile: Image.Image) -> str | None:
        return self._hash_to_id.get(tile_hash(tile))

    def add_tile(self, tile: Image.Image, force_new: bool = False) -> tuple[str, bool]:
        """
        Return (state_id, was_added).
        If force_new is False, reuse an existing matching state when found.
        """
        img = tile.convert("RGBA")
        if img.size != (self.tile_size, self.tile_size):
            img = img.resize((self.tile_size, self.tile_size), Image.Resampling.NEAREST)

        if not force_new:
            existing = self.find_duplicate(img)
            if existing is not None:
                return existing, False

        state_id = str(self._next_id)
        self._next_id += 1
        self.dmi.states.append(DmiState(name=state_id, images=[img.copy()]))
        h = tile_hash(img)
        # Only index if not already present (force_new may create visual dupes)
        if h not in self._hash_to_id:
            self._hash_to_id[h] = state_id
        elif force_new:
            pass  # keep first hash mapping for future reuse lookups
        return state_id, True
