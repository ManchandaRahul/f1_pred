"""Build a leak-free historical F1 dataset using only Python's standard library.

Usage: python scripts/build_dataset.py --start 2016 --end 2025
Outputs: data/historical_race_features.csv and data/dataset_metadata.json
"""
from __future__ import annotations
import argparse, csv, json, time
from collections import defaultdict, deque
from pathlib import Path
from urllib.request import Request, urlopen

BASE = "https://api.jolpi.ca/ergast/f1"; OUT = Path("data")
def fetch(path: str) -> dict:
    request = Request(f"{BASE}/{path}", headers={"User-Agent": "ApexF1DatasetBuilder/1.0"})
    with urlopen(request, timeout=45) as response: return json.load(response)
def races(season: int, kind: str) -> list[dict]:
    """Jolpica caps pages at 100 records; merge pages so no races are omitted."""
    offset, merged = 0, {}
    collection_key = "Results" if kind == "results" else "QualifyingResults"
    while True:
        data = fetch(f"{season}/{kind}.json?limit=100&offset={offset}")["MRData"]
        page = data["RaceTable"].get("Races", [])
        for race in page:
            target = merged.setdefault(race["round"], {key: value for key, value in race.items() if key != collection_key})
            target.setdefault(collection_key, []).extend(race.get(collection_key, []))
        offset += int(data["limit"])
        if offset >= int(data["total"]): break
        time.sleep(.25)
    return sorted(merged.values(), key=lambda item: int(item["round"]))
def mean(values: deque, default: float) -> float: return sum(values) / len(values) if values else default
def build_season(season: int) -> list[dict]:
    qualifying = {(race["round"], result["Driver"]["driverId"]): int(result["position"]) for race in races(season, "qualifying") for result in race.get("QualifyingResults", [])}
    points, wins, team_points = defaultdict(float), defaultdict(int), defaultdict(float)
    driver_finish, team_finish, circuit_finish = defaultdict(lambda: deque(maxlen=5)), defaultdict(lambda: deque(maxlen=5)), defaultdict(lambda: deque(maxlen=10)); dnf = defaultdict(lambda: deque(maxlen=10)); rows = []
    for race in sorted(races(season, "results"), key=lambda item: int(item["round"])):
        circuit, round_id, results = race["Circuit"]["circuitId"], race["round"], race.get("Results", [])
        for result in results:
            driver, team = result["Driver"]["driverId"], result["Constructor"]["constructorId"]
            position = int(result["position"]) if result.get("position", "").isdigit() else 20; grid = int(result.get("grid") or 20) or 20
            rows.append({"season": season, "round": int(round_id), "race_name": race["raceName"], "circuit_id": circuit, "driver_id": driver, "constructor_id": team, "driver_points_before": points[driver], "driver_wins_before": wins[driver], "driver_avg_finish_last5": mean(driver_finish[driver], 15), "team_points_before": team_points[team], "team_avg_finish_last5": mean(team_finish[team], 15), "circuit_driver_avg_finish": mean(circuit_finish[(circuit, driver)], 15), "dnf_rate_last10": mean(dnf[driver], 0), "grid_position": grid, "qualifying_position": qualifying.get((round_id, driver), grid), "target_win": int(position == 1)})
        for result in results:
            driver, team = result["Driver"]["driverId"], result["Constructor"]["constructorId"]
            position = int(result["position"]) if result.get("position", "").isdigit() else 20; status = result.get("status", "")
            points[driver] += float(result.get("points", 0)); team_points[team] += float(result.get("points", 0)); wins[driver] += int(position == 1)
            driver_finish[driver].append(position); team_finish[team].append(position); circuit_finish[(circuit, driver)].append(position); dnf[driver].append(int("Finished" not in status and "+" not in status))
    return rows
def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--start", type=int, default=2016); parser.add_argument("--end", type=int, default=2025); args = parser.parse_args()
    if args.start > args.end: raise ValueError("--start must be no later than --end")
    rows = []
    for season in range(args.start, args.end + 1): print(f"Fetching {season}..."); rows.extend(build_season(season)); time.sleep(.4)
    OUT.mkdir(exist_ok=True)
    with (OUT / "historical_race_features.csv").open("w", newline="", encoding="utf-8") as file: writer = csv.DictWriter(file, fieldnames=rows[0].keys()); writer.writeheader(); writer.writerows(rows)
    (OUT / "dataset_metadata.json").write_text(json.dumps({"seasons": [args.start, args.end], "rows": len(rows), "positive_rows": sum(int(row["target_win"]) for row in rows), "provider": "Jolpica F1 (Ergast-compatible)"}, indent=2)); print(f"Wrote {len(rows)} rows")
if __name__ == "__main__": main()
