import urllib.request

urls = [
    "http://kokinn.com/wp-content/uploads/2026/01/xcZzcNIr.jpg",
    "https://kokinn.com/wp-content/uploads/2026/01/xcZzcNIr.jpg",
]
for url in urls:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as res:
            data = res.read(20)
            print(url, res.status, res.headers.get("Content-Type"), len(data), data[:8])
    except Exception as exc:
        print(url, "ERROR", type(exc).__name__, exc)
