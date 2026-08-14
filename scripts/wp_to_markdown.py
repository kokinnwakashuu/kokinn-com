"""Convert All-in-One WP Migration SQL dump into Astro Markdown files."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote

SQL_PATH = Path(r"G:\scratch\kokinn-com\_import\database.sql")
ROOT = Path(r"G:\scratch\kokinn-com")
POSTS_DIR = ROOT / "src" / "content" / "posts"
PAGES_DIR = ROOT / "src" / "content" / "pages"
DATA_DIR = ROOT / "src" / "data"

POST_COLUMNS = [
    "ID",
    "post_author",
    "post_date",
    "post_date_gmt",
    "post_content",
    "post_title",
    "post_excerpt",
    "post_status",
    "comment_status",
    "ping_status",
    "post_password",
    "post_name",
    "to_ping",
    "pinged",
    "post_modified",
    "post_modified_gmt",
    "post_content_filtered",
    "post_parent",
    "guid",
    "menu_order",
    "post_type",
    "post_mime_type",
    "comment_count",
]


def parse_mysql_string(s: str, i: int) -> tuple[str, int]:
    assert s[i] == "'"
    i += 1
    out: list[str] = []
    while i < len(s):
        ch = s[i]
        if ch == "\\":
            if i + 1 >= len(s):
                break
            nxt = s[i + 1]
            mapping = {"n": "\n", "r": "\r", "t": "\t", "0": "\0", "b": "\b", "Z": "\x1a"}
            out.append(mapping.get(nxt, nxt))
            i += 2
            continue
        if ch == "'":
            if i + 1 < len(s) and s[i + 1] == "'":
                out.append("'")
                i += 2
                continue
            return "".join(out), i + 1
        out.append(ch)
        i += 1
    return "".join(out), i


def parse_sql_tuple(s: str, i: int) -> tuple[list[object], int]:
    while i < len(s) and s[i] != "(":
        i += 1
    if i >= len(s):
        raise ValueError("tuple start not found")
    i += 1
    values: list[object] = []
    while i < len(s):
        while i < len(s) and s[i] in " \t\r\n":
            i += 1
        if i < len(s) and s[i] == ")":
            return values, i + 1
        if s.startswith("NULL", i) and (i + 4 == len(s) or s[i + 4] in ",) \t\r\n"):
            values.append(None)
            i += 4
        elif i < len(s) and s[i] == "'":
            val, i = parse_mysql_string(s, i)
            values.append(val)
        else:
            j = i
            while j < len(s) and s[j] not in ",)":
                j += 1
            raw = s[i:j].strip()
            values.append(raw)
            i = j
        while i < len(s) and s[i] in " \t\r\n":
            i += 1
        if i < len(s) and s[i] == ",":
            i += 1
    raise ValueError("unterminated tuple")


def iter_inserts(sql: str, table: str):
    needle = f"INSERT INTO `SERVMASK_PREFIX_{table}` VALUES "
    start = 0
    while True:
        idx = sql.find(needle, start)
        if idx < 0:
            break
        i = idx + len(needle)
        values, end = parse_sql_tuple(sql, i)
        yield values
        start = end


PAGE_SLUGS = {
    80: "privacy",
}

PAGE_SLUGS_BY_TITLE = {
    "プライバシーポリシー": "privacy",
    "おうちで学べる！おすすめのオンライン英会話スクール": "english-schools",
    "おすすめのプログラミングスクール3つを比較！": "programming-schools",
}


def decode_wp_slug(slug: str) -> str:
    raw = unquote(slug or "")
    parts = raw.split("-")
    hex_parts = [p for p in parts if re.fullmatch(r"[0-9a-fA-F]{2}", p)]
    extras = [p for p in parts if not re.fullmatch(r"[0-9a-fA-F]{2}", p)]
    if len(hex_parts) >= 3:
        try:
            decoded = bytes(int(p, 16) for p in hex_parts).decode("utf-8")
            if extras:
                decoded = f"{decoded}-{'-'.join(extras)}"
            return decoded
        except Exception:
            pass
    return raw


def slugify(text: str, fallback: str) -> str:
    text = decode_wp_slug(text or "").strip()
    if re.search(r"[^\x00-\x7f]", text):
        return fallback
    text = text.lower()
    text = re.sub(r"[^\w\-]+", "-", text, flags=re.ASCII)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or fallback


def yaml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        if not value:
            return "[]"
        return "[" + ", ".join(json.dumps(str(v), ensure_ascii=False) for v in value) + "]"
    return json.dumps("" if value is None else str(value), ensure_ascii=False)


def write_frontmatter(meta: dict, body: str) -> str:
    lines = ["---"]
    for key, value in meta.items():
        lines.append(f"{key}: {yaml_value(value)}")
    lines.append("---")
    lines.append("")
    lines.append(body.rstrip())
    lines.append("")
    return "\n".join(lines)


CAPTION_RE = re.compile(r"\[caption[^\]]*\](.*?)\[/caption\]", re.I | re.S)
AMAZONJS_RE = re.compile(r"\[amazonjs([^\]]*)\]", re.I)
ASIN_RE = re.compile(r'asin="([^"]+)"', re.I)
GUTENBERG_RE = re.compile(r"<!--\s+/?wp:[^>]*-->")
MORE_RE = re.compile(r"<!--more-->", re.I)


def convert_content(html: str) -> str:
    if not html:
        return ""
    html = html.replace("\r\n", "\n").replace("\r", "\n")
    html = html.replace("http://127.0.0.1/wordpress", "")
    html = html.replace("https://kokinn.com/wp-content/uploads/", "/wp-content/uploads/")
    html = html.replace("http://kokinn.com/wp-content/uploads/", "/wp-content/uploads/")
    html = html.replace("http://kokinn.com", "https://kokinn.com")
    html = GUTENBERG_RE.sub("", html)
    html = MORE_RE.sub("\n\n", html)

    def caption_sub(match: re.Match) -> str:
        inner = match.group(1).strip()
        return f"<figure>{inner}</figure>"

    html = CAPTION_RE.sub(caption_sub, html)

    def amazon_sub(match: re.Match) -> str:
        attrs = match.group(1)
        asin_match = ASIN_RE.search(attrs)
        if not asin_match:
            return match.group(0)
        asin = asin_match.group(1)
        url = f"https://www.amazon.co.jp/dp/{asin}"
        return f'<p class="amazon-link"><a href="{url}" rel="nofollow sponsored">Amazonで見る（{asin}）</a></p>'

    html = AMAZONJS_RE.sub(amazon_sub, html)
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html.strip()


def excerpt_from(html: str, fallback: str) -> str:
    text = re.sub(r"<[^>]+>", "", html or "")
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        text = fallback
    return text[:160]


def main() -> None:
    sql = SQL_PATH.read_text(encoding="utf-8", errors="replace")

    terms = {}
    for row in iter_inserts(sql, "terms"):
        term_id, name, slug, _group = row[:4]
        terms[int(term_id)] = {"name": name, "slug": slug}

    taxonomies = {}
    for row in iter_inserts(sql, "term_taxonomy"):
        tt_id, term_id, taxonomy, _desc, parent, _count = row[:6]
        taxonomies[int(tt_id)] = {
            "term_id": int(term_id),
            "taxonomy": taxonomy,
            "parent": int(parent or 0),
        }

    rels = defaultdict(list)
    for row in iter_inserts(sql, "term_relationships"):
        object_id, tt_id = int(row[0]), int(row[1])
        rels[object_id].append(tt_id)

    attachments = {}
    posts = []
    pages = []
    for row in iter_inserts(sql, "posts"):
        item = dict(zip(POST_COLUMNS, row))
        item["ID"] = int(item["ID"])
        item["post_parent"] = int(item["post_parent"] or 0)
        ptype = item["post_type"]
        if ptype == "attachment":
            attachments[item["ID"]] = item
            continue
        if item["post_status"] != "publish":
            continue
        if ptype == "post":
            posts.append(item)
        elif ptype == "page":
            pages.append(item)

    options = {}
    wanted_options = {
        "blogname",
        "blogdescription",
        "siteurl",
        "home",
        "ihaf_insert_header",
        "ihaf_insert_footer",
    }
    for row in iter_inserts(sql, "options"):
        _id, name, value, _autoload = row[:4]
        if name in wanted_options or (isinstance(name, str) and "amazon" in name.lower()):
            options[name] = value

    thumbnail_ids = {}
    attached_files = {}
    for row in iter_inserts(sql, "postmeta"):
        _meta_id, post_id, meta_key, meta_value = row[:4]
        post_id = int(post_id)
        if meta_key == "_thumbnail_id" and meta_value:
            try:
                thumbnail_ids[post_id] = int(meta_value)
            except ValueError:
                pass
        elif meta_key == "_wp_attached_file" and meta_value:
            attached_files[post_id] = meta_value

    def image_url(post_id: int) -> str:
        thumb_id = thumbnail_ids.get(post_id)
        if not thumb_id:
            return ""
        rel = attached_files.get(thumb_id)
        if rel:
            return f"/wp-content/uploads/{rel}"
        att = attachments.get(thumb_id)
        if att and att.get("guid"):
            return str(att["guid"]).replace("http://kokinn.com", "https://kokinn.com")
        return ""

    def cats_and_tags(post_id: int) -> tuple[list[str], list[str], list[str], list[str]]:
        cats, tags, cat_slugs, tag_slugs = [], [], [], []
        for tt_id in rels.get(post_id, []):
            tax = taxonomies.get(tt_id)
            if not tax:
                continue
            term = terms.get(tax["term_id"])
            if not term:
                continue
            if tax["taxonomy"] == "category":
                cats.append(term["name"])
                cat_slugs.append(term["slug"])
            elif tax["taxonomy"] == "post_tag":
                tags.append(term["name"])
                tag_slugs.append(term["slug"])
        return cats, tags, cat_slugs, tag_slugs

    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for old in list(POSTS_DIR.glob("*.md")) + list(PAGES_DIR.glob("*.md")):
        old.unlink()

    used_slugs: set[str] = set()
    id_map = {}

    def unique_slug(raw: str, post_id: int) -> str:
        base = slugify(raw, f"post-{post_id}")
        slug = base
        n = 2
        while slug in used_slugs:
            slug = f"{base}-{n}"
            n += 1
        used_slugs.add(slug)
        return slug

    for item in sorted(posts, key=lambda x: x["post_date"]):
        slug = str(item["ID"])
        used_slugs.add(slug)
        cats, tags, cat_slugs, tag_slugs = cats_and_tags(item["ID"])
        cat_slugs = [decode_wp_slug(s) for s in cat_slugs]
        body = convert_content(item["post_content"] or "")
        title = item["post_title"] or f"記事 {item['ID']}"
        meta = {
            "title": title,
            "description": excerpt_from(item["post_excerpt"] or body, title),
            "pubDate": (item["post_date"] or "")[:19].replace(" ", "T"),
            "updatedDate": (item["post_modified"] or "")[:19].replace(" ", "T"),
            "categories": cats,
            "categorySlugs": cat_slugs,
            "tags": tags,
            "heroImage": image_url(item["ID"]),
            "wpId": item["ID"],
            "draft": False,
        }
        date_prefix = (item["post_date"] or "1970-01-01")[:10]
        (POSTS_DIR / f"{date_prefix}-{slug}.md").write_text(
            write_frontmatter(meta, body),
            encoding="utf-8",
        )
        id_map[str(item["ID"])] = f"/posts/{slug}"

    page_slugs = {}
    for item in sorted(pages, key=lambda x: x["menu_order"] or 0):
        title = item["post_title"] or f"ページ {item['ID']}"
        slug = PAGE_SLUGS.get(item["ID"]) or PAGE_SLUGS_BY_TITLE.get(title) or unique_slug(
            item["post_name"] or f"page-{item['ID']}", item["ID"]
        )
        body = convert_content(item["post_content"] or "")
        meta = {
            "title": title,
            "description": excerpt_from(item["post_excerpt"] or body, title),
            "wpId": item["ID"],
            "menuOrder": int(item["menu_order"] or 0),
        }
        (PAGES_DIR / f"{slug}.md").write_text(write_frontmatter(meta, body), encoding="utf-8")
        page_slugs[slug] = title
        id_map[str(item["ID"])] = f"/{slug}"

    categories = []
    for tt in taxonomies.values():
        if tt["taxonomy"] != "category":
            continue
        term = terms.get(tt["term_id"])
        if not term:
            continue
        categories.append({"name": term["name"], "slug": decode_wp_slug(term["slug"])})
    categories.sort(key=lambda x: x["name"])

    site = {
        "title": options.get("blogname") or "kokinn.com",
        "description": options.get("blogdescription") or "",
        "site": "https://kokinn.com",
        "adsensePublisher": "ca-pub-3308566948805620",
        "enableAds": False,
        "categories": categories,
        "pages": page_slugs,
        "importNotes": {
            "headerOptionPresent": "ihaf_insert_header" in options,
            "footerOptionPresent": "ihaf_insert_footer" in options,
            "amazonOptionKeys": [k for k in options if "amazon" in k.lower()],
        },
    }
    (DATA_DIR / "site.json").write_text(json.dumps(site, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA_DIR / "wp-id-map.json").write_text(json.dumps(id_map, ensure_ascii=False, indent=2), encoding="utf-8")

    if options.get("ihaf_insert_header") or options.get("ihaf_insert_footer"):
        (DATA_DIR / "legacy-header-footer.html").write_text(
            "<!-- HEADER -->\n"
            + str(options.get("ihaf_insert_header") or "")
            + "\n\n<!-- FOOTER -->\n"
            + str(options.get("ihaf_insert_footer") or ""),
            encoding="utf-8",
        )

    print(f"published_posts={len(posts)}")
    print(f"published_pages={len(pages)}")
    print(f"categories={len(categories)}")
    print(f"attachments={len(attachments)}")
    print("pages", page_slugs)
    print("category_names", [c["name"] for c in categories])


if __name__ == "__main__":
    main()
