"""Build a chronological, leak-free F1 race dataset from Jolpica.

The state for driver/team form resets each season, while circuit history is
carried across seasons. Only information available before each race is written
to the feature columns.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = os.environ.get("F1_API_BASE_URL", "https://api.jolpi.ca/ergast/f1")
OUT = Path("data")


def fetch(path: str) -> dict:
    request = Request(f"{BASE}/{path}", headers={"User-Agent": "ApexF1DatasetBuilder/2.0"})
    for attempt in range(4):
        try:
            with urlopen(request, timeout=60) as response:
                return json.load(response)
        except (HTTPError, URLError, TimeoutError):
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def races(season: int, kind: str) -> list[dict]:
    """Merge Jolpica's 100-row pages back into complete race objects."""
    offset, merged = 0, {}
    collection_key = {"results": "Results", "qualifying": "QualifyingResults", "sprint": "SprintResults"}[kind]
    while True:
        data = fetch(f"{season}/{kind}.json?limit=100&offset={offset}")["MRData"]
        for race in data["RaceTable"].get("Races", []):
            target = merged.setdefault(race["round"], {key: value for key, value in race.items() if key != collection_key})
            target.setdefault(collection_key, []).extend(race.get(collection_key, []))
        offset += int(data["limit"])
        if offset >= int(data["total"]):
            break
        time.sleep(0.2)
    return sorted(merged.values(), key=lambda item: int(item["round"]))


def mean(values: deque, default: float) -> float:
    return sum(values) / len(values) if values else default


def new_circuit_history() -> dict[str, defaultdict]:
    return {
        "driver": defaultdict(lambda: deque(maxlen=8)),
        "team": defaultdict(lambda: deque(maxlen=12)),
    }


def build_season(season: int, circuit_history: dict[str, defaultdict]) -> list[dict]:
    qualifying = {
        (race["round"], result["Driver"]["driverId"]): int(result["position"])
        for race in races(season, "qualifying")
        for result in race.get("QualifyingResults", [])
    }
    sprint = {
        (race["round"], result["Driver"]["driverId"]): int(result["position"]) if result.get("position", "").isdigit() else 20
        for race in races(season, "sprint")
        for result in race.get("SprintResults", [])
    }
    sprint_rounds = {round_id for round_id, _ in sprint}
    points, wins, team_points = defaultdict(float), defaultdict(int), defaultdict(float)
    driver_finish = defaultdict(lambda: deque(maxlen=5))
    team_finish = defaultdict(lambda: deque(maxlen=10))
    dnf = defaultdict(lambda: deque(maxlen=10))
    rows: list[dict] = []

    for race in races(season, "results"):
        circuit = race["Circuit"]["circuitId"]
        round_id = race["round"]
        results = race.get("Results", [])
        for result in results:
            driver = result["Driver"]["driverId"]
            driver_code = result["Driver"].get("code") or driver[:3].upper()
            team = result["Constructor"]["constructorId"]
            position = int(result["position"]) if result.get("position", "").isdigit() else 20
            grid = int(result.get("grid") or 20) or 20
            rows.append({
                "season": season,
                "round": int(round_id),
                "race_date": race.get("date", ""),
                "race_name": race["raceName"],
                "circuit_id": circuit,
                "driver_id": driver,
                "driver_code": driver_code,
                "constructor_id": team,
                "driver_points_before": points[driver],
                "driver_wins_before": wins[driver],
                "driver_avg_finish_last5": mean(driver_finish[driver], 15),
                "team_points_before": team_points[team],
                "team_avg_finish_last5": mean(team_finish[team], 15),
                "circuit_driver_avg_finish": mean(circuit_history["driver"][(circuit, driver)], 15),
                "circuit_team_avg_finish": mean(circuit_history["team"][(circuit, team)], 15),
                "dnf_rate_last10": mean(dnf[driver], 0),
                "sprint_available": int(round_id in sprint_rounds),
                "sprint_position": sprint.get((round_id, driver), 0),
                "grid_position": grid,
                "qualifying_position": qualifying.get((round_id, driver), grid),
                "finish_position": position,
                "target_win": int(position == 1),
            })

        for result in results:
            driver = result["Driver"]["driverId"]
            team = result["Constructor"]["constructorId"]
            position = int(result["position"]) if result.get("position", "").isdigit() else 20
            status = result.get("status", "")
            points[driver] += float(result.get("points", 0))
            team_points[team] += float(result.get("points", 0))
            wins[driver] += int(position == 1)
            driver_finish[driver].append(position)
            team_finish[team].append(position)
            circuit_history["driver"][(circuit, driver)].append(position)
            circuit_history["team"][(circuit, team)].append(position)
            dnf[driver].append(int("Finished" not in status and "+" not in status))
    return rows


def main() -> None:
    current_year = datetime.now(timezone.utc).year
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=2016)
    parser.add_argument("--end", type=int, default=current_year)
    args = parser.parse_args()
    if args.start > args.end:
        raise ValueError("--start must be no later than --end")

    rows: list[dict] = []
    circuit_history = new_circuit_history()
    for season in range(args.start, args.end + 1):
        print(f"Fetching {season}...", flush=True)
        rows.extend(build_season(season, circuit_history))
        time.sleep(0.35)
    if not rows:
        raise RuntimeError("Jolpica returned no completed race results")

    OUT.mkdir(exist_ok=True)
    with (OUT / "historical_race_features.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    last_row = max(rows, key=lambda row: (int(row["season"]), int(row["round"])))
    metadata = {
        "seasons": [args.start, args.end],
        "rows": len(rows),
        "positive_rows": sum(int(row["target_win"]) for row in rows),
        "data_through": {"season": int(last_row["season"]), "round": int(last_row["round"]), "date": last_row["race_date"]},
        "provider": "Jolpica F1 (Ergast-compatible)",
    }
    (OUT / "dataset_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Wrote {len(rows)} rows through {last_row['season']} round {last_row['round']}")


if __name__ == "__main__":
    main()
