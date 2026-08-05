"""Train an exportable logistic-regression race-winner model with no third-party packages.

Usage: python scripts/train_model.py
The latest season is held out for evaluation; model/race-winner-v1.json is used by Next.js.
"""
from __future__ import annotations
import csv, json, math
from datetime import datetime, timezone
from pathlib import Path

FEATURES = ["driver_points_before", "driver_wins_before", "driver_avg_finish_last5", "team_points_before", "team_avg_finish_last5", "circuit_driver_avg_finish", "dnf_rate_last10", "grid_position", "qualifying_position"]
DATA, OUT = Path("data/historical_race_features.csv"), Path("model/race-winner-v1.json")
def sigmoid(value: float) -> float: return 1 / (1 + math.exp(-max(-30, min(30, value))))
def auc(labels, scores):
    positives, negatives = sum(labels), len(labels) - sum(labels)
    if not positives or not negatives: return 0.5
    ranked = sorted(zip(scores, labels)); rank_sum = sum(index + 1 for index, (_, label) in enumerate(ranked) if label)
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)
def average_precision(labels, scores):
    total, hits, score = sum(labels), 0, 0.0
    if not total: return 0.0
    for index, (_, label) in enumerate(sorted(zip(scores, labels), reverse=True), 1):
        hits += label
        if label: score += hits / index
    return score / total
def main() -> None:
    if not DATA.exists(): raise FileNotFoundError("Run scripts/build_dataset.py first")
    with DATA.open(encoding="utf-8") as file: rows = [{key: float(value) if key not in {"race_name", "circuit_id", "driver_id", "constructor_id"} else value for key, value in row.items()} for row in csv.DictReader(file)]
    holdout = max(int(row["season"]) for row in rows); train, test = [row for row in rows if int(row["season"]) < holdout], [row for row in rows if int(row["season"]) == holdout]
    means = {feature: sum(row[feature] for row in train) / len(train) for feature in FEATURES}; scales = {feature: max(1e-6, (sum((row[feature] - means[feature]) ** 2 for row in train) / len(train)) ** .5) for feature in FEATURES}
    weights, bias, learning_rate = [0.0] * len(FEATURES), 0.0, .035
    positives = sum(row["target_win"] for row in train); pos_weight = (len(train) - positives) / max(positives, 1)
    for _ in range(1400):
        gradients, bias_gradient = [0.0] * len(FEATURES), 0.0
        for row in train:
            vector = [(row[feature] - means[feature]) / scales[feature] for feature in FEATURES]; target = row["target_win"]; weight = pos_weight if target else 1.0; error = (sigmoid(sum(a * b for a, b in zip(weights, vector)) + bias) - target) * weight
            for index, value in enumerate(vector): gradients[index] += error * value
            bias_gradient += error
        for index in range(len(weights)): weights[index] -= learning_rate * (gradients[index] / len(train) + .002 * weights[index])
        bias -= learning_rate * bias_gradient / len(train)
    scores = [sigmoid(sum(weights[index] * ((row[feature] - means[feature]) / scales[feature]) for index, feature in enumerate(FEATURES)) + bias) for row in test]; labels = [int(row["target_win"]) for row in test]
    output = {"version": "race-winner-logistic-v1", "trainedAt": datetime.now(timezone.utc).isoformat(), "featureNames": FEATURES, "means": means, "scales": scales, "coefficients": weights, "intercept": bias, "metrics": {"holdout_season": holdout, "training_rows": len(train), "test_rows": len(test), "test_roc_auc": round(auc(labels, scores), 4), "test_average_precision": round(average_precision(labels, scores), 4), "test_brier_score": round(sum((score - label) ** 2 for score, label in zip(scores, labels)) / len(labels), 4)}, "limitations": "Race-week grid and qualifying inputs are unavailable until published; their historical means are used before then."}
    OUT.parent.mkdir(exist_ok=True); OUT.write_text(json.dumps(output, indent=2)); print(json.dumps(output["metrics"], indent=2))
if __name__ == "__main__": main()
