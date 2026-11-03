"""
Servicio de noticias: combina feeds RSS gaming públicos. Antes estaba en extras_kira.py.
"""

import re
import time
import requests
import feedparser
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape

RSS_FEEDS = [
    ("Vandal",         "https://vandal.elespanol.com/rss/noticias"),
    ("3DJuegos",       "https://www.3djuegos.com/rss/rss.xml"),
    ("Hobby Consolas", "https://www.hobbyconsolas.com/rss.xml"),
    ("Eurogamer ES",   "https://www.eurogamer.es/?format=rss"),
]

CACHE_TTL_NOTICIAS = 300  # 5 min
_cache_noticias = {"ts": 0, "data": []}


# =====================================================================
# NOTICIAS RSS
# =====================================================================
def _limpiar_html(texto):
    if not texto:
        return ""
    txt = re.sub(r"<[^>]+>", "", texto)
    return re.sub(r"\s+", " ", unescape(txt)).strip()


def _extraer_thumbnail(entry):
    """Intenta sacar una imagen del entry del RSS."""
    if "media_thumbnail" in entry and entry.media_thumbnail:
        return entry.media_thumbnail[0].get("url")
    if "media_content" in entry and entry.media_content:
        return entry.media_content[0].get("url")
    if hasattr(entry, "enclosures"):
        for e in entry.enclosures:
            if e.get("type", "").startswith("image"):
                return e.get("href") or e.get("url")
    desc = entry.get("summary", "") or entry.get("description", "")
    m = re.search(r'<img[^>]+src=["\'](.*?)["\']', desc)
    return m.group(1) if m else None


def _fetch_feed(nombre, url):
    try:
        r = requests.get(url, timeout=8, headers={
            "User-Agent": "Mozilla/5.0 (compatible; KiraIA/1.0)"
        })
        if r.status_code != 200:
            return []
        feed = feedparser.parse(r.content)
        items = []
        for entry in feed.entries[:10]:
            ts = 0
            if entry.get("published_parsed"):
                try:
                    ts = time.mktime(entry.published_parsed)
                except Exception:
                    ts = 0
            items.append({
                "titulo":    _limpiar_html(entry.get("title", ""))[:180],
                "resumen":   _limpiar_html(entry.get("summary", ""))[:220],
                "link":      entry.get("link", ""),
                "fuente":    nombre,
                "fecha_ts":  ts,
                "thumbnail": _extraer_thumbnail(entry),
            })
        return items
    except Exception as e:
        print(f"Error RSS '{nombre}': {e}")
        return []


def obtener_noticias(limit=10, forzar=False):
    """Combina varios RSS y devuelve las últimas noticias. Cachea 5 min."""
    ahora = time.time()
    if not forzar and (ahora - _cache_noticias["ts"] < CACHE_TTL_NOTICIAS) and _cache_noticias["data"]:
        return _cache_noticias["data"][:limit]

    todos = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futuros = [pool.submit(_fetch_feed, nombre, url) for nombre, url in RSS_FEEDS]
        for f in as_completed(futuros):
            todos.extend(f.result())

    todos.sort(key=lambda x: x["fecha_ts"], reverse=True)
    _cache_noticias["data"] = todos
    _cache_noticias["ts"] = ahora
    return todos[:limit]
