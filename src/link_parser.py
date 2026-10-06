import re

_MAGNET_RE = re.compile(r"magnet:\?xt=urn:btih:[0-9A-Za-z]{32,40}[^\s]*", re.IGNORECASE)


def read_text(path):
    with open(path, "rb") as f:
        raw = f.read()
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def extract_links(text):
    out, seen = [], set()
    for m in _MAGNET_RE.finditer(text):
        link = m.group(0)
        h = hash_of(link)
        if h not in seen:
            seen.add(h)
            out.append(link)
    return out


def hash_of(link):
    m = re.search(r"urn:btih:([0-9A-Za-z]{32,40})", link, re.IGNORECASE)
    return m.group(1).lower() if m else ""


def filter_done(links, done_hashes):
    return [l for l in links if hash_of(l) not in done_hashes]
