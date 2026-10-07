#!/usr/bin/env python3
import copy
import gzip
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHANNELS_FILE = ROOT / "channels.txt"
OUT_XML = ROOT / "epg.xml"
OUT_GZ = ROOT / "epg.xml.gz"
STATUS = ROOT / "status.json"

SOURCE_BY_SUFFIX = {
    "us": "https://iptv-epg.org/files/epg-us.xml.gz",
    "uk": "https://iptv-epg.org/files/epg-gb.xml.gz",
    "ca": "https://iptv-epg.org/files/epg-ca.xml.gz",
    "mx": "https://iptv-epg.org/files/epg-mx.xml.gz",
    "au": "https://iptv-epg.org/files/epg-au.xml.gz",
}

PAST_HOURS = 8
FUTURE_DAYS = 3
USER_AGENT = "uhf-favorites-epg/1.0"


def load_ids():
    return {
        line.strip()
        for line in CHANNELS_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def parse_xmltv_time(value):
    if not value:
        return None
    value = value.strip()
    for pattern in ("%Y%m%d%H%M%S %z", "%Y%m%d%H%M %z", "%Y%m%d%H%M%S", "%Y%m%d%H%M"):
        try:
            dt = datetime.strptime(value, pattern)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass
    return None


def fetch_relevant(url, wanted_ids, window_start, window_end):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    channels = []
    programmes = []
    with urllib.request.urlopen(req, timeout=180) as response:
        with gzip.GzipFile(fileobj=response) as stream:
            for _, elem in ET.iterparse(stream, events=("end",)):
                if elem.tag == "channel":
                    if elem.get("id") in wanted_ids:
                        channels.append(copy.deepcopy(elem))
                    elem.clear()
                elif elem.tag == "programme":
                    if elem.get("channel") in wanted_ids:
                        start = parse_xmltv_time(elem.get("start"))
                        stop = parse_xmltv_time(elem.get("stop"))
                        in_window = start is None or stop is None or (stop >= window_start and start <= window_end)
                        if in_window:
                            programmes.append(copy.deepcopy(elem))
                    elem.clear()
    return channels, programmes


def main():
    wanted = load_ids()
    suffixes = sorted({cid.rsplit(".", 1)[-1].lower() for cid in wanted})
    unsupported = sorted(set(suffixes) - set(SOURCE_BY_SUFFIX))
    if unsupported:
        raise SystemExit(f"Unsupported channel suffixes: {', '.join(unsupported)}")

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=PAST_HOURS)
    window_end = now + timedelta(days=FUTURE_DAYS)

    found_channels = {}
    programmes = []
    per_source = {}

    for suffix in suffixes:
        source_ids = {cid for cid in wanted if cid.lower().endswith('.' + suffix)}
        url = SOURCE_BY_SUFFIX[suffix]
        channels, shows = fetch_relevant(url, source_ids, window_start, window_end)
        for channel in channels:
            found_channels[channel.get("id")] = channel
        programmes.extend(shows)
        per_source[suffix] = {
            "requested_channels": len(source_ids),
            "found_channels": len({c.get('id') for c in channels}),
            "programmes": len(shows),
            "source": url,
        }

    tv = ET.Element("tv", {
        "generator-info-name": "UHF Favorites EPG Filter",
        "generator-info-url": "https://iptv-epg.org/",
    })

    for channel_id in sorted(found_channels):
        tv.append(found_channels[channel_id])

    programmes.sort(key=lambda p: (p.get("start", ""), p.get("channel", "")))
    for programme in programmes:
        tv.append(programme)

    ET.indent(tv, space="  ")
    ET.ElementTree(tv).write(OUT_XML, encoding="utf-8", xml_declaration=True)

    with OUT_XML.open("rb") as source, gzip.open(OUT_GZ, "wb", compresslevel=9) as target:
        target.write(source.read())

    missing = sorted(wanted - set(found_channels))
    status = {
        "updated_utc": now.isoformat(),
        "requested_unique_channels": len(wanted),
        "found_channels": len(found_channels),
        "missing_channels": missing,
        "programmes": len(programmes),
        "window_start_utc": window_start.isoformat(),
        "window_end_utc": window_end.isoformat(),
        "epg_xml_bytes": OUT_XML.stat().st_size,
        "epg_gz_bytes": OUT_GZ.stat().st_size,
        "sources": per_source,
    }
    STATUS.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
