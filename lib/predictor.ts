import trainedModel from "@/model/race-winner-v2.json";
import type { CompletedRaceResult, Driver, Prediction, Race } from "./types";

type ExportedTree = {
  childrenLeft: number[];
  childrenRight: number[];
  feature: number[];
  threshold: number[];
  value: number[];
};
type ExportedEnsemble = { featureNames: string[]; learningRate: number; trees: ExportedTree[] };
type ModelArtifact = {
  version: string;
  dataThrough: { season: number; round: number; date?: string };
  featureDefaults: Record<string, number>;
  models: { early: ExportedEnsemble; raceWeek: ExportedEnsemble };
  profiles: { driverCircuitFinish: Record<string, number>; teamCircuitFinish: Record<string, number> };
};

const model = trainedModel as ModelArtifact;
const mean = (values: number[], fallback: number) => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : fallback;
const isDnf = (status: string) => !status.includes("Finished") && !status.includes("+");
const confidenceForRace = (probability: number): Prediction["confidence"] => probability >= 30 ? "High" : probability >= 12 ? "Medium" : "Low";

function treeValue(tree: ExportedTree, values: number[]): number {
  let node = 0;
  while (tree.childrenLeft[node] !== -1) {
    node = values[tree.feature[node]] <= tree.threshold[node] ? tree.childrenLeft[node] : tree.childrenRight[node];
  }
  return tree.value[node];
}

function rawScore(ensemble: ExportedEnsemble, features: Record<string, number>): number {
  const values = ensemble.featureNames.map((name) => features[name] ?? model.featureDefaults[name] ?? 0);
  return ensemble.learningRate * ensemble.trees.reduce((total, tree) => total + treeValue(tree, values), 0);
}

function fieldPercentages(scores: number[]): number[] {
  const maximum = Math.max(...scores);
  const exponentials = scores.map((score) => Math.exp(score - maximum));
  const total = exponentials.reduce((sum, value) => sum + value, 0) || 1;
  const percentages = exponentials.map((value) => Math.round(value / total * 1000) / 10);
  const delta = Math.round((100 - percentages.reduce((sum, value) => sum + value, 0)) * 10) / 10;
  const largest = percentages.indexOf(Math.max(...percentages));
  percentages[largest] = Math.round((percentages[largest] + delta) * 10) / 10;
  return percentages;
}

export function predict(drivers: Driver[]): Prediction[] {
  const pointsMax = Math.max(...drivers.map((driver) => driver.points), 1);
  const winsMax = Math.max(...drivers.map((driver) => driver.wins), 1);
  const scores = drivers.map((driver) => 0.65 * driver.points / pointsMax + 0.35 * driver.wins / winsMax);
  const probabilities = fieldPercentages(scores.map((score) => score * 3));
  return drivers.map((driver, index) => ({
    driver: driver.name,
    team: driver.team,
    form: Math.round(driver.points / pointsMax * 100),
    winProbability: probabilities[index],
    confidence: confidenceForRace(probabilities[index])
  })).sort((a, b) => b.winProbability - a.winProbability);
}

export function predictRace(
  drivers: Driver[],
  race: Race,
  qualifyingPositions: Record<string, number> = {},
  completedResults: CompletedRaceResult[] = []
): { predictions: Prediction[]; stage: "early" | "race-week"; modelVersion: string; dataThrough: ModelArtifact["dataThrough"] } {
  const targetRound = Number(race.round);
  const priorResults = completedResults.filter((result) => result.round < targetRound).sort((a, b) => a.round - b.round);
  const qualifyingCount = drivers.filter((driver) => qualifyingPositions[driver.code] != null).length;
  const raceWeek = qualifyingCount >= Math.max(1, Math.ceil(drivers.length * 0.7));
  const ensemble = raceWeek ? model.models.raceWeek : model.models.early;
  const pointsMax = Math.max(...drivers.map((driver) => driver.points), 1);
  const winsMax = Math.max(...drivers.map((driver) => driver.wins), 1);

  const candidates = drivers.map((driver) => {
    const driverResults = priorResults.filter((result) => result.driverId === driver.id);
    const teamResults = priorResults.filter((result) => result.teamId === driver.teamId);
    const recentDriver = driverResults.slice(-5);
    const recentTeam = teamResults.slice(-10);
    const recentDnf = driverResults.slice(-10);
    const teamPoints = drivers.filter((candidate) => candidate.teamId === driver.teamId).reduce((total, candidate) => total + candidate.points, 0);
    const qualifying = qualifyingPositions[driver.code];
    const features: Record<string, number> = {
      ...model.featureDefaults,
      driver_points_before: driver.points,
      driver_wins_before: driver.wins,
      driver_avg_finish_last5: mean(recentDriver.map((result) => result.position), model.featureDefaults.driver_avg_finish_last5),
      team_points_before: teamPoints,
      team_avg_finish_last5: mean(recentTeam.map((result) => result.position), model.featureDefaults.team_avg_finish_last5),
      circuit_driver_avg_finish: model.profiles.driverCircuitFinish[`${race.circuitId}|${driver.id}`] ?? model.featureDefaults.circuit_driver_avg_finish,
      circuit_team_avg_finish: model.profiles.teamCircuitFinish[`${race.circuitId}|${driver.teamId}`] ?? model.featureDefaults.circuit_team_avg_finish,
      dnf_rate_last10: mean(recentDnf.map((result) => Number(isDnf(result.status))), model.featureDefaults.dnf_rate_last10),
      qualifying_position: qualifying ?? model.featureDefaults.qualifying_position,
      grid_position: qualifying ?? model.featureDefaults.grid_position,
    };
    const championshipForm = 0.65 * driver.points / pointsMax + 0.35 * driver.wins / winsMax;
    const recentForm = 1 - Math.min(1, features.driver_avg_finish_last5 / Math.max(drivers.length, 1));
    return { driver, score: rawScore(ensemble, features), form: Math.round((0.7 * championshipForm + 0.3 * recentForm) * 100) };
  });

  const percentages = fieldPercentages(candidates.map((candidate) => candidate.score));
  const predictions = candidates.map((candidate, index) => ({
    driver: candidate.driver.name,
    team: candidate.driver.team,
    form: candidate.form,
    winProbability: percentages[index],
    confidence: confidenceForRace(percentages[index])
  })).sort((a, b) => b.winProbability - a.winProbability);
  return { predictions, stage: raceWeek ? "race-week" : "early", modelVersion: model.version, dataThrough: model.dataThrough };
}
