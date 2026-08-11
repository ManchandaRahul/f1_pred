import { getQualifying, getRaces, getSeasonResults, getStandings } from "@/lib/f1-api";
import { predict, predictRace } from "@/lib/predictor";
export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  const fresh = params.get("refresh") === "1";
  const { drivers, source } = await getStandings(fresh);
  const round = params.get("round");
  if (!round) return Response.json({ predictions: predict(drivers), source, model: "championship-form-v1" });
  const [{ races }, seasonForm] = await Promise.all([getRaces(fresh), getSeasonResults(fresh)]);
  const race = races.find((item) => item.round === round);
  if (!race) return Response.json({ error: "Race not found" }, { status: 404 });
  const qualifyingPositions = await getQualifying(round, fresh);
  const prediction = predictRace(drivers, race, qualifyingPositions, seasonForm.results);
  return Response.json({ ...prediction, source, race, qualifyingAvailable: prediction.stage === "race-week", liveFormThroughRound: seasonForm.throughRound });
}
