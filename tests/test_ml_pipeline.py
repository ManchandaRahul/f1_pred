import json
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import build_dataset


def race(season: int, position: int) -> dict:
    return {
        "round": "1",
        "date": f"{season}-03-01",
        "raceName": "Test Grand Prix",
        "Circuit": {"circuitId": "test_track"},
        "Results": [{
            "position": str(position),
            "grid": "2",
            "points": "12",
            "status": "Finished",
            "Driver": {"driverId": "test_driver", "code": "TST"},
            "Constructor": {"constructorId": "test_team"},
        }],
    }


class DatasetTests(unittest.TestCase):
    def test_circuit_history_crosses_season_boundary_without_target_leakage(self):
        def fake_races(season: int, kind: str):
            if kind == "qualifying":
                return []
            return [race(season, 4 if season == 2020 else 1)]

        history = build_dataset.new_circuit_history()
        with patch.object(build_dataset, "races", side_effect=fake_races):
            first = build_dataset.build_season(2020, history)
            second = build_dataset.build_season(2021, history)
        self.assertEqual(first[0]["driver_points_before"], 0)
        self.assertEqual(first[0]["circuit_driver_avg_finish"], 15)
        self.assertEqual(second[0]["circuit_driver_avg_finish"], 4)

    def test_exported_model_contains_all_prediction_stages(self):
        artifact = json.loads(Path("model/race-winner-v3.json").read_text(encoding="utf-8"))
        self.assertEqual(artifact["version"], "race-winner-gbt-v3")
        self.assertGreater(artifact["trainingRows"], 4000)
        self.assertEqual(set(artifact["models"]), {"early", "sprintWeek", "raceWeek"})
        self.assertGreater(len(artifact["models"]["early"]["trees"]), 100)
        self.assertIn("qualifying_position", artifact["models"]["raceWeek"]["featureNames"])
        self.assertNotIn("qualifying_position", artifact["models"]["early"]["featureNames"])
        self.assertIn("sprint_position", artifact["models"]["sprintWeek"]["featureNames"])


if __name__ == "__main__":
    unittest.main()
