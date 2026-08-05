# Apex F1

A Vercel-ready Formula 1 dashboard built with Next.js, React, and TypeScript. It uses a distinct dark, glass-like visual system and exposes four responsive views: championship pulse, driver standings, race calendar, and an explainable winner outlook.

## Run locally

```bash
npm install
cp .env.example .env.local
npm run dev
```

Open `http://localhost:3000`. Deploy by importing this folder into Vercel or running `vercel`; the included `vercel.json` selects the Next.js runtime.

## Data layer

`/api/standings` and `/api/races` fetch the current season from [Jolpica F1](https://github.com/jolpica/jolpica-f1), the maintained Ergast-compatible F1 API. Responses are cached for 15 minutes. When the upstream service is unavailable or has no current-season data, the app returns clearly-labelled bundled demonstration data instead of failing the interface.

| Route | Purpose |
| --- | --- |
| `/api/standings` | Current championship driver standings |
| `/api/races` | Current calendar, circuit, location, and completed/upcoming status |
| `/api/predictions` | Ranking based on current points and wins |

Pass `?round=<round>` to `/api/predictions` for a selected race. The UI exposes this as the **Race Predictions** tab; **Championship Outlook** is intentionally kept separate. The Driver Standings tab has a **Refresh standings** control. It sends `?refresh=1`, bypassing the 15-minute server cache and requesting the upstream source immediately.

Set `F1_API_BASE_URL` only if you host or subscribe to an Ergast-compatible API. No token is needed by the default provider. Do not prefix server-only variables with `NEXT_PUBLIC_`.

## Prediction workflow

The shipped prediction route uses a deliberately interpretable baseline: normalized championship points (65%) and wins (35%). It produces a relative likelihood and confidence label, never a claim of certainty. This is suitable for the dashboard demo and is not betting advice.

For a trained race model, first build the complete dataset. Jolpica pages API results at 100 records, and the builder handles every page; a 2025 holdout should contain roughly 400 driver-race rows, not 100.

```bash
python scripts/build_dataset.py --start 2016 --end 2025
python -m pip install -r requirements-ml.txt
python scripts/train_model_sklearn.py
```

The builder fetches every season's results and qualifying sessions from Jolpica and produces one pre-race row per driver. It derives rolling driver/team form, points, wins, DNFs, grid and qualifying positions, and circuit history without leaking same-race results into features. The recommended trainer uses scikit-learn, keeps the last season as a holdout and the preceding season for Platt probability calibration, reports ROC-AUC, average precision, and Brier score, then writes `model/race-winner-v1.json`. That JSON is used directly by the Next.js prediction API. The manual refresh fetches qualifying data when it becomes available during race week; until then, the model uses learned historical means for those features.

## Structure

```text
app/                 pages, global styling, serverless API routes
components/          reusable dashboard views
lib/                 domain types, F1 gateway, fallback data, predictor
scripts/build_dataset.py  historical data and feature generation
scripts/train_model.py    time-split ML training and model export
scripts/train_model_sklearn.py  recommended calibrated scikit-learn trainer
model/                    deployable model artifact
```

## Notes

- API route errors are contained and the UI has loading/error states.
- The F1 provider is changeable with one environment variable.
- The UI uses no chart dependency; the dashboard chart is an accessible CSS/SVG-free data bar implementation, keeping the client bundle small.
