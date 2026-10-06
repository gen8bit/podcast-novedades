#!/usr/bin/env python3
"""
Genera un .m3u con los últimos N episodios de cada feed configurado en feeds.yml.
"""

import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from email.utils import parsedate_to_datetime

try:
    import yaml
except ImportError:
    print("ERROR: falta PyYAML. Añádelo al workflow.", file=sys.stderr)
    sys.exit(1)

BASE_DIR = Path(__file__).parent.parent
CONFIG_FILE = BASE_DIR / "feeds.yml"
USER_AGENT = "Mozilla/5.0 (compatible; Podcast-Novelties-Updater/1.0)"


def fetch_feed(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def extract_episodes(xml_bytes: bytes) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    episodes = []
    for item in root.findall(".//item"):
        enc = item.find("enclosure")
        if enc is None or not enc.get("url"):
            continue
        pub = item.findtext("pubDate")
        try:
            dt = parsedate_to_datetime(pub) if pub else None
        except Exception:
            dt = None
        episodes.append({"url": enc.get("url").strip(), "date": dt})
    return episodes


def sort_by_date_desc(episodes: list[dict]) -> list[dict]:
    def key(ep):
        d = ep["date"]
        if d is not None and d.tzinfo is not None:
            d = d.replace(tzinfo=None)
        return d or datetime.min
    return sorted(episodes, key=key, reverse=True)


def by_date(all_episodes: list[dict]) -> list[str]:
    return [ep["url"] for ep in sort_by_date_desc(all_episodes)]


def round_robin(feeds_episodes: list[list[dict]]) -> list[str]:
    result = []
    max_len = max((len(f) for f in feeds_episodes), default=0)
    for i in range(max_len):
        for feed_eps in feeds_episodes:
            if i < len(feed_eps):
                result.append(feed_eps[i]["url"])
    return result


def concatenate(feeds_episodes: list[list[dict]]) -> list[str]:
    result = []
    for feed_eps in feeds_episodes:
        result.extend(ep["url"] for ep in feed_eps)
    return result


def main() -> int:
    if not CONFIG_FILE.exists():
        print(f"ERROR: no existe {CONFIG_FILE}", file=sys.stderr)
        return 1

    with CONFIG_FILE.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    output_file = BASE_DIR / config.get("output", "novedades.m3u")
    strategy = config.get("strategy", "by-date")
    feed_order = config.get("feed_order", "newest-first")
    default_limit = int(config.get("default_limit", 3))
    feeds = config.get("feeds", [])

    if not feeds:
        print("ERROR: no hay feeds configurados en feeds.yml", file=sys.stderr)
        return 1

    feeds_episodes: list[list[dict]] = []
    all_episodes: list[dict] = []

    for feed in feeds:
        name = feed.get("name", feed["url"])
        limit = int(feed.get("limit", default_limit))
        try:
            xml_bytes = fetch_feed(feed["url"])
        except Exception as e:
            print(f"WARN: fallo al descargar '{name}': {e}", file=sys.stderr)
            continue

        episodes = extract_episodes(xml_bytes)
        # Los feeds suelen venir del más nuevo al más antiguo.
        # Ordenamos por fecha descendente para asegurarnos.
        episodes = sort_by_date_desc(episodes)
        # Recortamos a los "limit" más recientes
        episodes = episodes[:limit]

        if feed_order == "oldest-first":
            episodes.reverse()

        feeds_episodes.append(episodes)
        all_episodes.extend(episodes)
        print(f"OK: {name} → {len(episodes)} episodios (limit={limit})")

    if strategy == "by-date":
        urls = by_date(all_episodes)
    elif strategy == "round-robin":
        urls = round_robin(feeds_episodes)
    elif strategy == "concatenate":
        urls = concatenate(feeds_episodes)
    else:
        print(f"ERROR: estrategia desconocida '{strategy}'", file=sys.stderr)
        return 1

    with output_file.open("w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for u in urls:
            f.write(u + "\n")

    print(f"OK: {len(urls)} URLs escritas en {output_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
