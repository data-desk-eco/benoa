#!/usr/bin/env python3
"""Fetch every LNG cargo delivered to the Benoa FSU from Kpler and write a flat CSV.

This is the expensive, auth-gated step (`make etl`). It shells out to the Kpler
CLI in `.claude/skills/kpler/kpler`, which needs `gcloud auth login` against
project `data-desk-web` (credentials auto-load from Secret Manager `kpler-env`).

Output `data/benoa_lng_trades.csv` is committed to the repo; the CI-safe
`make data` step rebuilds the DuckDB tables from it without touching Kpler.
"""
import csv
import json
import os
import subprocess
import sys
import time

# Kpler entity IDs (resolve with `kpler search "benoa"` / `kpler search "lng" --categories PRODUCT`)
BENOA_ZONE = 4141          # port/zone that trades are queried against
BENOA_INSTALLATION = 3845  # the Benoa LNG FSU — keep only cargoes discharging here
LNG_PRODUCT = 1750

KPLER = os.environ.get("KPLER", ".claude/skills/kpler/kpler")
PAGE = 200                 # API caps --size; paginate with --offset
MAX_OFFSET = 20000         # safety stop
OUT = "data/benoa_lng_trades.csv"


def fetch_page(offset):
    """One page of trades as a list of dicts, with retries for rate limiting."""
    for attempt in range(4):
        proc = subprocess.run(
            [KPLER, "trades", "--locations", str(BENOA_ZONE),
             "--products", str(LNG_PRODUCT), "--size", str(PAGE), "--offset", str(offset)],
            capture_output=True, text=True,
        )
        lines = [l for l in proc.stdout.splitlines() if l.strip()]
        if lines:
            return [json.loads(l) for l in lines]
        # Empty can mean "end of data" or a transient rate-limit; back off and retry.
        time.sleep(5)
    return []


def dest_installation(r):
    for key in ("portCallDestination", "forecastPortCallDestination"):
        inst = (r.get(key) or {}).get("installation") or {}
        if inst.get("id"):
            return inst.get("id")
    return None


def origin(r):
    for key in ("portCallOrigin", "forecastPortCallOrigin"):
        inst = (r.get(key) or {}).get("installation") or {}
        if inst.get("fullname"):
            return inst.get("fullname"), inst.get("country")
    return None, None


def quantity(r, field):
    for key in ("flowQuantityToDestination", "flowQuantityFromOrigin"):
        val = (r.get(key) or {}).get(field)
        if val:
            return val
    return None


def delivery_date(r):
    return (r.get("end") or r.get("start") or "")[:10]


def vessel(r):
    vs = r.get("vessels") or []
    return vs[0].get("name") if vs else None


def main():
    rows, offset = [], 0
    while offset <= MAX_OFFSET:
        page = fetch_page(offset)
        n = len(page)
        print(f"offset {offset}: {n} records", file=sys.stderr)
        rows.extend(page)
        if n < PAGE:
            break
        offset += PAGE
        time.sleep(4)

    out_rows = []
    for r in rows:
        if dest_installation(r) != BENOA_INSTALLATION:
            continue
        date = delivery_date(r)
        if not date:
            continue
        o, oc = origin(r)
        out_rows.append({
            "trade_id": r.get("id"),
            "date": date,
            "year": int(date[:4]),
            "origin": o,
            "origin_country": oc,
            "volume_m3": quantity(r, "volume"),
            "mass_t": quantity(r, "mass"),
            "vessel": vessel(r),
            "status": r.get("status"),
        })

    out_rows.sort(key=lambda x: (x["date"], x["trade_id"]))
    os.makedirs("data", exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "trade_id", "date", "year", "origin", "origin_country",
            "volume_m3", "mass_t", "vessel", "status"])
        w.writeheader()
        w.writerows(out_rows)
    print(f"wrote {len(out_rows)} cargoes to {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
