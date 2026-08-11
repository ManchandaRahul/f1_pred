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
| `/api/predictions` | Championship outlook or ML race-win probabilities |

Pass `?round=<round>` to `/api/predictions` for a selected race. The UI exposes this as the **Race Predictions** tab; **Championship Outlook** is intentionally kept separate. The Driver Standings tab has a **Refresh standings** control. It sends `?refresh=1`, bypassing the 15-minute server cache and requesting the upstream source immediately.

Set `F1_API_BASE_URL` only if you host or subscribe to an Ergast-compatible API. No token is needed by the default provider. Do not prefix server-only variables with `NEXT_PUBLIC_`.

## Prediction intelligence

Championship outlook remains a transparent points-and-wins form estimate. Race Predictions use `race-winner-gbt-v2`, a two-stage gradient-boosted tree system:

- **Early-week model:** current points and wins, live recent driver/team finishes, DNF rate, and cross-season driver/team circuit history.
- **Race-week model:** all early-week features plus grid and qualifying position. It activates automatically once qualifying is substantially complete.
- Probabilities are normalized across the current field and always total 100%.
- The API reads completed current-season results on every cached refresh, so recent form changes after each race even before the model is retrained.

The committed artifact was trained on 4,562 driver-race rows from 2016 through 2026 round 11. On the chronological 2025 holdout, the early model achieved 25.0% winner top-one and 66.7% top-three accuracy; the race-week model achieved 58.3% top-one and 100% top-three accuracy. These historical metrics are not guarantees and the predictions are not betting advice.

To rebuild through the latest completed race:

```bash
python -m pip install -r requirements-ml.txt
npm run model:update
```

The builder handles Jolpica's 100-row pagination and carries circuit history across season boundaries without exposing same-race results to the features. Training performs chronological, race-grouped evaluation and then refits both deployed models on all completed races through today. The resulting `model/race-winner-v2.json` is evaluated directly in TypeScript, so the Vercel runtime does not require Python.

The weekly GitHub Actions workflow runs every Monday and commits a new artifact only when newly completed race data changes the model. It can also be started manually from the Actions tab.

## Structure

```text
app/                 pages, global styling, serverless API routes
components/          reusable dashboard views
lib/                 domain types, F1 gateway, fallback data, predictor
scripts/build_dataset.py  historical data and feature generation
scripts/train_model_sklearn.py  chronological GBT training, evaluation, and export
scripts/update_model.py   rebuild-and-retrain entry point
model/                    deployable model artifact
.github/workflows/        weekly model evolution workflow
tests/                    dataset and artifact integrity tests
```

## Notes

- API route errors are contained and the UI has loading/error states.
- The F1 provider is changeable with one environment variable.
- The UI uses no chart dependency; the dashboard chart is an accessible CSS/SVG-free data bar implementation, keeping the client bundle small.
- Run `npm test`, `npm run lint`, and `npm run build` before deployment.
