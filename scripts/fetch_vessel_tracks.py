#!/usr/bin/env python3
"""Fetch AIS tracks for the vessels on the Bontang->Benoa shuttle and write GeoJSON.

Part of the auth-gated `make etl` step. Pulls positions from the Kpler CLI for
each Bontang-route vessel, orders them in time, splits into segments across AIS
gaps, downsamples, and writes one MultiLineString feature per vessel to
`data/vessel_tracks.geojson`.
"""
import json
import math
import os
import subprocess
import sys
import time

KPLER = os.environ.get("KPLER", ".claude/skills/kpler/kpler")
FROM = os.environ.get("TRACKS_FROM", "2024-01-01")
TO = os.environ.get("TRACKS_TO", "")   # empty = up to now
LIMIT = 12000
GAP_HOURS = 12          # start a new segment when AIS drops for longer than this
MIN_STEP_DEG = 0.01     # drop points closer than ~1 km to the previous kept point
# Clip to the Bontang->Benoa corridor. Kpler AIS only reaches back to ~Aug 2024,
# so out-of-region operations (e.g. a vessel that later left the route) are
# excluded rather than drawing misleading lines across other seas.
REGION = {"lon_min": 110.0, "lon_max": 121.0, "lat_min": -11.0, "lat_max": 4.0}
OUT = "data/vessel_tracks.geojson"

# Bontang-route vessels. `gfw_file` (if set) is a committed Global Fishing Watch
# track export used instead of Kpler positions; otherwise positions come from the
# Kpler vessel id. Hai Yang Shi You 301 left the route before Kpler's AIS history
# begins (~Aug 2024), so it has no in-region track and is dropped downstream.
VESSELS = [
    {"name": "Triputra",             "kpler_id": 68583, "colour": "#3987e5",
     "gfw_file": "data/gfw_tracks/Triputra.geojson"},
]


def load_gfw_points(path):
    """Flatten a Global Fishing Watch track export (LineString features with a
    coordinateProperties.times epoch-ms array) into the same point dicts that
    build_segments expects."""
    import datetime
    with open(path) as f:
        gj = json.load(f)
    points = []
    for feat in gj.get("features", []):
        coords = (feat.get("geometry") or {}).get("coordinates") or []
        times = ((feat.get("properties") or {}).get("coordinateProperties") or {}).get("times") or []
        for i, c in enumerate(coords):
            t = times[i] if i < len(times) else None
            iso = (datetime.datetime.fromtimestamp(t / 1000, datetime.timezone.utc)
                   .strftime("%Y-%m-%dT%H:%M:%S") if t else "")
            points.append({"received_time": iso, "lon": c[0], "lat": c[1]})
    return points


def fetch_positions(vessel_id):
    cmd = [KPLER, "positions", str(vessel_id), "--from", FROM,
           "--limit", str(LIMIT), "--format", "ndjson"]
    if TO:
        cmd += ["--to", TO]
    for attempt in range(4):
        proc = subprocess.run(cmd, capture_output=True, text=True)
        lines = [l for l in proc.stdout.splitlines() if l.strip()]
        if lines:
            return [json.loads(l) for l in lines]
        time.sleep(5)
    return []


def build_segments(points):
    """points: list of dicts with received_time, lat, lon (any order). Returns
    a list of coordinate lists, split on time gaps and spatially downsampled."""
    pts = []
    for p in points:
        try:
            lat, lon = float(p["lat"]), float(p["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        if not (REGION["lon_min"] <= lon <= REGION["lon_max"]
                and REGION["lat_min"] <= lat <= REGION["lat_max"]):
            continue
        pts.append((p.get("received_time", ""), lon, lat))
    pts.sort(key=lambda x: x[0])

    segments, seg, last_t, last_kept = [], [], None, None
    for t, lon, lat in pts:
        if last_t is not None and _hours_between(last_t, t) > GAP_HOURS:
            if len(seg) > 1:
                segments.append(seg)
            seg, last_kept = [], None
        if last_kept is None or math.hypot(lon - last_kept[0], lat - last_kept[1]) >= MIN_STEP_DEG:
            seg.append([round(lon, 5), round(lat, 5)])
            last_kept = (lon, lat)
        last_t = t
    if len(seg) > 1:
        segments.append(seg)
    return segments


def _hours_between(a, b):
    from datetime import datetime
    fmt = "%Y-%m-%dT%H:%M:%S"
    try:
        return abs((datetime.strptime(b[:19], fmt) - datetime.strptime(a[:19], fmt)).total_seconds()) / 3600
    except ValueError:
        return 0


def main():
    features = []
    for v in VESSELS:
        name, vid, colour = v["name"], v["kpler_id"], v["colour"]
        gfw = v.get("gfw_file")
        if gfw and os.path.exists(gfw):
            pts = load_gfw_points(gfw)
            source = f"GFW {gfw}"
        else:
            pts = fetch_positions(vid)
            source = f"Kpler {vid}"
            time.sleep(3)
        segs = build_segments(pts)
        npts = sum(len(s) for s in segs)
        print(f"{name} ({source}): {len(pts)} raw -> {len(segs)} segments, {npts} points"
              f"{' [no in-region track, skipped]' if npts == 0 else ''}",
              file=sys.stderr)
        if npts == 0:
            continue
        features.append({
            "type": "Feature",
            "properties": {"vessel": name, "vessel_id": vid, "colour": colour,
                           "source": "GFW" if gfw and os.path.exists(gfw) else "Kpler",
                           "segments": len(segs), "points": npts},
            "geometry": {"type": "MultiLineString", "coordinates": segs},
        })

    os.makedirs("data", exist_ok=True)
    with open(OUT, "w") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f)
    print(f"wrote {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
