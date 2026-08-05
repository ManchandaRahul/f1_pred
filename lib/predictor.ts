import type { Driver, Prediction, Race } from "./types";
import trainedModel from "@/model/race-winner-v1.json";
/** Deterministic inference approximation. Replace coefficients using scripts/train.py output for production. */
export function predict(drivers: Driver[]): Prediction[] {
  const max = Math.max(...drivers.map(d => d.points), 1);
  return drivers.map(d => { const score = Math.round((0.65 * d.points / max + 0.35 * d.wins / Math.max(...drivers.map(x => x.wins), 1)) * 100); return { driver: d.name, team: d.team, form: Math.round((d.points / max) * 100), winProbability: score, confidence: confidenceFor(score) }; }).sort((a,b) => b.winProbability-a.winProbability);
}

/** Race-specific baseline: championship form adjusted by a stable circuit affinity signal.
 * Replace circuitAffinity with trained historical circuit features when a model is deployed. */
type TrainedModel = { featureNames: string[]; means: Record<string, number>; scales: Record<string, number>; coefficients: number[]; intercept: number; calibration?: { coefficient: number; intercept: number } };
const model = trainedModel as TrainedModel;
const sigmoid = (value: number) => 1 / (1 + Math.exp(-value));
const confidenceFor = (score: number): Prediction["confidence"] => score >= 70 ? "High" : score >= 42 ? "Medium" : "Low";
export function predictRace(drivers: Driver[], race: Race, qualifyingPositions: Record<string, number> = {}): Prediction[] {
  const pointsMax = Math.max(...drivers.map((d) => d.points), 1);
  const winsMax = Math.max(...drivers.map((d) => d.wins), 1);
  const hasModel = model.featureNames.length > 0 && model.coefficients.length === model.featureNames.length;
  const hash = (value: string) => [...value].reduce((total, char) => total + char.charCodeAt(0), 0);
  return drivers.map((d) => {
    const form = 0.65 * (d.points / pointsMax) + 0.35 * (d.wins / winsMax);
    const circuitAffinity = 0.84 + ((hash(`${race.circuit}-${d.code}`) % 33) / 100);
    const teamPoints = drivers.filter((driver) => driver.team === d.team).reduce((total, driver) => total + driver.points, 0);
    const values: Record<string, number> = { ...model.means, driver_points_before: d.points, driver_wins_before: d.wins, team_points_before: teamPoints, qualifying_position: qualifyingPositions[d.code] ?? model.means.qualifying_position, grid_position: qualifyingPositions[d.code] ?? model.means.grid_position };
    const linearScore = model.featureNames.reduce((total, feature, index) => total + (((values[feature] ?? model.means[feature]) - model.means[feature]) / (model.scales[feature] || 1)) * model.coefficients[index], model.intercept);
    const probability = hasModel ? sigmoid(model.calibration ? model.calibration.coefficient * linearScore + model.calibration.intercept : linearScore) : form * circuitAffinity;
    const score = Math.round(Math.min(95, Math.max(3, probability * 100)));
    return { driver: d.name, team: d.team, form: Math.round(form * 100), winProbability: score, confidence: confidenceFor(score) };
  }).sort((a, b) => b.winProbability - a.winProbability);
}
