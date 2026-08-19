"""Train exportable early-week and race-week gradient-boosted F1 models.

Evaluation is chronological and race-grouped. The deployed models are then
refit on every completed race in the dataset, including the current season.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

DATA = Path("data/historical_race_features.csv")
METADATA = Path("data/dataset_metadata.json")
OUT = Path("model/race-winner-v3.json")
ARTIFACT_VERSION = "race-winner-gbt-v3"

EARLY_FEATURES = [
    "driver_points_before",
    "driver_wins_before",
    "driver_avg_finish_last5",
    "team_points_before",
    "team_avg_finish_last5",
    "circuit_driver_avg_finish",
    "circuit_team_avg_finish",
    "dnf_rate_last10",
]
SPRINT_WEEK_FEATURES = EARLY_FEATURES + ["sprint_position"]
RACE_WEEK_FEATURES = EARLY_FEATURES + ["sprint_available", "sprint_position", "grid_position", "qualifying_position"]


def sample_weights(target: pd.Series) -> np.ndarray:
    positives = max(1, int(target.sum()))
    return np.where(target.to_numpy() == 1, (len(target) - positives) / positives, 1.0)


def train(frame: pd.DataFrame, features: list[str]) -> GradientBoostingClassifier:
    model = GradientBoostingClassifier(
        loss="log_loss",
        learning_rate=0.035,
        n_estimators=180,
        max_depth=2,
        min_samples_leaf=12,
        subsample=0.85,
        max_features=None,
        init="zero",
        random_state=44,
    )
    return model.fit(frame[features], frame.target_win, sample_weight=sample_weights(frame.target_win))


def field_probabilities(frame: pd.DataFrame, raw_scores: np.ndarray) -> np.ndarray:
    output = np.zeros(len(frame), dtype=float)
    groups = frame.reset_index(drop=True).groupby(["season", "round"]).indices
    for indices in groups.values():
        values = raw_scores[indices]
        exponentials = np.exp(values - np.max(values))
        output[indices] = exponentials / exponentials.sum()
    return output


def evaluate(model: GradientBoostingClassifier, frame: pd.DataFrame, features: list[str]) -> dict:
    raw = model.decision_function(frame[features])
    probabilities = field_probabilities(frame, raw)
    labels = frame.target_win.to_numpy(dtype=int)
    top1 = top3 = reciprocal_rank = winner_log_loss = 0.0
    race_count = 0
    evaluation = frame.reset_index(drop=True).assign(probability=probabilities)
    for _, race in evaluation.groupby(["season", "round"]):
        ordered = race.sort_values("probability", ascending=False).reset_index(drop=True)
        winner_rank = int(ordered.index[ordered.target_win == 1][0]) + 1
        winner_probability = max(float(ordered.loc[winner_rank - 1, "probability"]), 1e-12)
        top1 += int(winner_rank == 1)
        top3 += int(winner_rank <= 3)
        reciprocal_rank += 1 / winner_rank
        winner_log_loss += -math.log(winner_probability)
        race_count += 1
    return {
        "races": race_count,
        "top1_accuracy": round(top1 / race_count, 4),
        "top3_accuracy": round(top3 / race_count, 4),
        "mean_reciprocal_rank": round(reciprocal_rank / race_count, 4),
        "winner_log_loss": round(winner_log_loss / race_count, 4),
        "row_roc_auc": round(float(roc_auc_score(labels, probabilities)), 4),
        "row_average_precision": round(float(average_precision_score(labels, probabilities)), 4),
        "row_brier_score": round(float(brier_score_loss(labels, probabilities)), 4),
    }


def export_model(model: GradientBoostingClassifier, features: list[str]) -> dict:
    trees = []
    for estimator in model.estimators_.ravel():
        tree = estimator.tree_
        trees.append({
            "childrenLeft": tree.children_left.astype(int).tolist(),
            "childrenRight": tree.children_right.astype(int).tolist(),
            "feature": tree.feature.astype(int).tolist(),
            "threshold": tree.threshold.tolist(),
            "value": tree.value[:, 0, 0].tolist(),
        })
    return {
        "featureNames": features,
        "learningRate": model.learning_rate,
        "trees": trees,
        "featureImportance": dict(zip(features, np.round(model.feature_importances_, 6).tolist())),
    }


def recent_profile(frame: pd.DataFrame, keys: list[str], tail: int) -> dict[str, float]:
    profiles: dict[str, float] = {}
    ordered = frame.sort_values(["season", "round"])
    for values, group in ordered.groupby(keys):
        key_values = values if isinstance(values, tuple) else (values,)
        profiles["|".join(str(value) for value in key_values)] = round(float(group.tail(tail).finish_position.mean()), 4)
    return profiles


def main() -> None:
    if not DATA.exists():
        raise FileNotFoundError("Run scripts/build_dataset.py first")
    frame = pd.read_csv(DATA).dropna(subset=RACE_WEEK_FEATURES + ["target_win", "finish_position"])
    years = sorted(int(year) for year in frame.season.unique())
    current_year = datetime.now(timezone.utc).year
    evaluation_year = years[-2] if years[-1] == current_year and len(years) >= 3 else years[-1]
    train_frame = frame[frame.season < evaluation_year]
    test_frame = frame[frame.season == evaluation_year]
    if min(len(train_frame), len(test_frame)) == 0:
        raise RuntimeError("Need multiple completed seasons for chronological evaluation")

    evaluation = {}
    for name, features, subset in (
        ("early", EARLY_FEATURES, test_frame),
        ("sprintWeek", SPRINT_WEEK_FEATURES, test_frame[test_frame.sprint_available == 1]),
        ("raceWeek", RACE_WEEK_FEATURES, test_frame),
    ):
        evaluation[name] = evaluate(train(train_frame[train_frame.sprint_available == 1] if name == "sprintWeek" else train_frame, features), subset, features)

    deployed_early = train(frame, EARLY_FEATURES)
    deployed_sprint_week = train(frame[frame.sprint_available == 1], SPRINT_WEEK_FEATURES)
    deployed_race_week = train(frame, RACE_WEEK_FEATURES)
    metadata = json.loads(METADATA.read_text(encoding="utf-8")) if METADATA.exists() else {}
    data_through = metadata.get("data_through", {"season": years[-1], "round": int(frame[frame.season == years[-1]]["round"].max())})
    previous = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    unchanged_data = previous.get("version") == ARTIFACT_VERSION and previous.get("dataThrough") == data_through and previous.get("trainingRows") == len(frame)
    trained_at = previous.get("trainedAt") if unchanged_data else datetime.now(timezone.utc).isoformat()

    output = {
        "version": ARTIFACT_VERSION,
        "trainedAt": trained_at,
        "dataThrough": data_through,
        "trainingRows": len(frame),
        "featureDefaults": {feature: round(float(frame[feature].mean()), 6) for feature in RACE_WEEK_FEATURES},
        "models": {
            "early": export_model(deployed_early, EARLY_FEATURES),
            "sprintWeek": export_model(deployed_sprint_week, SPRINT_WEEK_FEATURES),
            "raceWeek": export_model(deployed_race_week, RACE_WEEK_FEATURES),
        },
        "profiles": {
            "driverCircuitFinish": recent_profile(frame, ["circuit_id", "driver_id"], 8),
            "teamCircuitFinish": recent_profile(frame, ["circuit_id", "constructor_id"], 12),
        },
        "metrics": {"holdoutSeason": evaluation_year, **evaluation},
        "limitations": "Probabilities are relative to the entered field. The early model is used until qualifying is available; weather, tyre choice and incidents are not known inputs.",
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps({"version": ARTIFACT_VERSION, "dataThrough": data_through, "metrics": output["metrics"]}, indent=2))


if __name__ == "__main__":
    main()
