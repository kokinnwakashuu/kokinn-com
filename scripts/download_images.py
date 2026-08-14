"""Download live WordPress images over HTTP and point Markdown at local copies."""
from __future__ import annotations

import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(r"G:\scratch\kokinn-com")
CONTENT = ROOT / "src" / "content"
PUBLIC = ROOT / "public"
URL_RE = re.compile(r"https://kokinn\.com(/wp-content/uploads/[^\s\"')>]+)")


def collect_paths() -> list[str]:
    found: set[str] = set()
    for path in CONTENT.rglob("*.md"):
        text = path.read_text(encoding="utf-8", errors="replace")
        found.update(URL_RE.findall(text))
    return sorted(found)


def download(rel_path: str) -> str:
    local = PUBLIC / rel_path.lstrip("/").replace("\\", "/")
    local.parent.mkdir(parents=True, exist_ok=True)
    if local.exists() and local.stat().st_size > 0:
        return "exists"
    quoted = urllib.parse.quote(rel_path, safe="/")
    url = f"http://kokinn.com{quoted}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 kokinn-com-import"})
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                data = res.read()
            if not data:
                raise RuntimeError("empty body")
            local.write_bytes(data)
            return "ok"
        except Exception as exc:
            last_error = exc
            time.sleep(1 + attempt)
    raise RuntimeError(f"{rel_path}: {last_error}")


def rewrite_markdown() -> int:
    changed = 0
    for path in CONTENT.rglob("*.md"):
        text = path.read_text(encoding="utf-8", errors="replace")
        new = text.replace("https://kokinn.com/wp-content/uploads/", "/wp-content/uploads/")
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed += 1
    return changed


def main() -> None:
    paths = collect_paths()
    print(f"images={len(paths)}")
    ok = exists = failed = 0
    errors = []
    for i, rel in enumerate(paths, 1):
        try:
            result = download(rel)
            if result == "exists":
                exists += 1
            else:
                ok += 1
        except Exception as exc:
            failed += 1
            errors.append(str(exc))
        if i % 50 == 0 or i == len(paths):
            print(f"progress {i}/{len(paths)} ok={ok} exists={exists} failed={failed}")
    changed = rewrite_markdown()
    print(f"rewritten_markdown={changed}")
    print(f"ok={ok} exists={exists} failed={failed}")
    for item in errors[:30]:
        print("FAIL", item)


if __name__ == "__main__":
    main()
