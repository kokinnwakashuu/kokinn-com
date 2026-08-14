"""Extract selected files from an All-in-One WP Migration .wpress archive."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

HEADER_SIZE = 4377
NAME_LEN = 255
SIZE_LEN = 14
MTIME_LEN = 12


def iter_entries(archive: Path):
    file_size = archive.stat().st_size
    with archive.open("rb") as f:
        while True:
            pos = f.tell()
            if pos + HEADER_SIZE > file_size:
                break
            header = f.read(HEADER_SIZE)
            if len(header) < HEADER_SIZE:
                break
            name = header[:NAME_LEN].split(b"\x00", 1)[0].decode("utf-8", "replace").strip()
            size_raw = header[NAME_LEN : NAME_LEN + SIZE_LEN].split(b"\x00", 1)[0].decode("ascii", "replace").strip()
            prefix = header[NAME_LEN + SIZE_LEN + MTIME_LEN :].split(b"\x00", 1)[0].decode("utf-8", "replace").strip()
            if not name and not size_raw:
                break
            try:
                size = int(size_raw) if size_raw else 0
            except ValueError:
                break
            rel = f"{prefix}/{name}" if prefix else name
            data_pos = f.tell()
            yield rel, size, data_pos
            f.seek(size, os.SEEK_CUR)


def extract(archive: Path, dest: Path, wanted: list[str], list_only: bool = False) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    wanted_set = set(wanted)
    found = []
    with archive.open("rb") as f:
        for rel, size, data_pos in iter_entries(archive):
            base = Path(rel).name
            if list_only:
                if base in wanted_set or rel in wanted_set or any(rel.endswith(w) for w in wanted):
                    print(f"FOUND\t{size}\t{rel}")
                    found.append(rel)
                continue
            if base not in wanted_set and rel not in wanted_set:
                continue
            out = dest / base
            print(f"EXTRACT\t{size}\t{rel}\t->\t{out}")
            f.seek(data_pos)
            remaining = size
            with out.open("wb") as out_f:
                while remaining:
                    chunk = f.read(min(remaining, 8 * 1024 * 1024))
                    if not chunk:
                        break
                    out_f.write(chunk)
                    remaining -= len(chunk)
            found.append(rel)
    if not found:
        raise SystemExit(f"No matching files in archive: {wanted}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True)
    parser.add_argument("--dest", required=True)
    parser.add_argument("--files", nargs="+", default=["package.json", "database.sql"])
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    extract(Path(args.archive), Path(args.dest), args.files, list_only=args.list)


if __name__ == "__main__":
    main()
