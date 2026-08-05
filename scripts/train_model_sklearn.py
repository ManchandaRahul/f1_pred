"""Recommended trainer: calibrated logistic regression, exportable to Next.js.

Install once: python -m pip install -r requirements-ml.txt
Run:          python scripts/train_model_sklearn.py
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler

FEATURES = ["driver_points_before", "driver_wins_before", "driver_avg_finish_last5", "team_points_before", "team_avg_finish_last5", "circuit_driver_avg_finish", "dnf_rate_last10", "grid_position", "qualifying_position"]
frame = pd.read_csv("data/historical_race_features.csv").dropna(subset=FEATURES + ["target_win"])
calibration_season, test_season = sorted(frame.season.unique())[-2:]
train, calibration, test = frame[frame.season < calibration_season], frame[frame.season == calibration_season], frame[frame.season == test_season]
if min(len(train), len(calibration), len(test)) == 0: raise RuntimeError("Need at least three completed seasons")
scaler = StandardScaler().fit(train[FEATURES])
base = LogisticRegression(class_weight="balanced", max_iter=3000, C=0.25).fit(scaler.transform(train[FEATURES]), train.target_win)
# Platt scaling repairs the deliberately class-balanced model probabilities using a later, unseen season.
calibration_logit = base.decision_function(scaler.transform(calibration[FEATURES])).reshape(-1, 1)
platt = LogisticRegression(C=1_000_000, max_iter=1000).fit(calibration_logit, calibration.target_win)
test_logit = base.decision_function(scaler.transform(test[FEATURES])); probabilities = platt.predict_proba(test_logit.reshape(-1, 1))[:, 1]
output = {"version": "race-winner-logistic-platt-v1", "trainedAt": datetime.now(timezone.utc).isoformat(), "featureNames": FEATURES, "means": dict(zip(FEATURES, scaler.mean_.tolist())), "scales": dict(zip(FEATURES, scaler.scale_.tolist())), "coefficients": base.coef_[0].tolist(), "intercept": float(base.intercept_[0]), "calibration": {"coefficient": float(platt.coef_[0][0]), "intercept": float(platt.intercept_[0]), "season": int(calibration_season)}, "metrics": {"training_seasons_through": int(calibration_season - 1), "calibration_season": int(calibration_season), "holdout_season": int(test_season), "training_rows": len(train), "calibration_rows": len(calibration), "test_rows": len(test), "test_roc_auc": round(float(roc_auc_score(test.target_win, probabilities)), 4), "test_average_precision": round(float(average_precision_score(test.target_win, probabilities)), 4), "test_brier_score": round(float(brier_score_loss(test.target_win, probabilities)), 4)}, "limitations": "Grid/qualifying are unavailable until race week; historical means are used before then."}
Path("model").mkdir(exist_ok=True); Path("model/race-winner-v1.json").write_text(json.dumps(output, indent=2)); print(json.dumps(output["metrics"], indent=2))
