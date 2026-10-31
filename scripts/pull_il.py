"""Pull MLB injured-list transactions 2023-03 .. 2025-11 from the MLB StatsAPI (one request per month).

Keeps rows whose description mentions "injured list" and that involve one of the 30 MLB clubs
(minor-league IL moves are dropped). Output: data/labels/il_transactions.csv
"""
import csv
import re
import time
from datetime import date, timedelta
from pathlib import Path

import requests

API = "https://statsapi.mlb.com/api/v1"
OUT = Path(__file__).resolve().parents[1] / "data" / "labels" / "il_transactions.csv"
UA = {"User-Agent": "PitchIntegrityMonitor/0.1 (research; github.com/debi910/pitch-integrity-monitor)"}


def get(url, **params):
    for attempt in range(4):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=60)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            print(f"  retry {attempt + 1}: {e}", flush=True)
            time.sleep(5 * 2 ** attempt)
    raise RuntimeError(f"failed: {url} {params}")


def months(start, end):
    cur = start
    while cur <= end:
        nxt = (cur + timedelta(days=32)).replace(day=1)
        yield cur, nxt - timedelta(days=1)
        cur = nxt


def kind(desc):
    d = desc.lower()
    if "transferred" in d:
        return "transferred"
    if "placed" in d:
        return "placed"
    if "activated" in d or "reinstated" in d:
        return "activated"
    return "other"


def il_days(desc):
    days = re.findall(r"(\d+)-day injured list", desc, flags=re.I)
    return days[-1] if days else ""          # transfers: the destination list


def main():
    mlb = {t["id"]: t["name"] for t in get(f"{API}/teams", sportId=1, season=2025)["teams"]}
    rows, seen = [], set()
    for a, b in months(date(2023, 3, 1), date(2025, 11, 30)):
        tx = get(f"{API}/transactions", startDate=a.isoformat(), endDate=b.isoformat()).get("transactions", [])
        n0 = len(rows)
        for t in tx:
            desc = t.get("description", "")
            if "injured list" not in desc.lower() or "person" not in t:
                continue
            team = t.get("toTeam") or t.get("fromTeam") or {}
            if team.get("id") not in mlb or t["id"] in seen:
                continue
            seen.add(t["id"])
            rows.append({"date": t.get("date", "")[:10], "effective_date": (t.get("effectiveDate") or t.get("date", ""))[:10],
                         "person_id": t["person"]["id"], "person_name": t["person"].get("fullName", ""),
                         "team": team.get("name", ""), "type": kind(desc), "il_days": il_days(desc),
                         "description": desc})
        print(f"{a:%Y-%m}: {len(tx):,} transactions, {len(rows) - n0} MLB IL rows", flush=True)
        time.sleep(1.0)
    rows.sort(key=lambda r: (r["date"], r["person_id"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {OUT} ({len(rows):,} rows)")
    counts = {}
    for r in rows:
        k = (r["date"][:4], r["type"])
        counts[k] = counts.get(k, 0) + 1
    for y in ("2023", "2024", "2025"):
        print(y, {t: counts.get((y, t), 0) for t in ("placed", "transferred", "activated", "other")})


if __name__ == "__main__":
    main()
