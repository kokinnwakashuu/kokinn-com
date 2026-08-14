from pathlib import Path
import re

root = Path(r"G:\scratch\kokinn-com\src\content")
urls = set()
for path in root.rglob("*.md"):
    text = path.read_text(encoding="utf-8", errors="replace")
    urls.update(re.findall(r"https?://kokinn\.com/wp-content/uploads/[^\s\"')>]+", text))

print(f"unique={len(urls)}")
print(f"https={sum(1 for u in urls if u.startswith('https://'))}")
print(f"http={sum(1 for u in urls if u.startswith('http://'))}")
for url in sorted(urls)[:20]:
    print(url)
