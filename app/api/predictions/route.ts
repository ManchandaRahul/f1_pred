import { getQualifying, getRaces, getStandings } from "@/lib/f1-api";
import { predict, predictRace } from "@/lib/predictor";
import trainedModel from "@/model/race-winner-v1.json";
export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  const fresh = params.get("refresh") === "1";
  const { drivers, source } = await getStandings(fresh);
  const round = params.get("round");
  if (!round) return Response.json({ predictions: predict(drivers), source, model: "championship-form-v1" });
  const { races } = await getRaces(fresh);
  const race = races.find((item) => item.round === round);
  if (!race) return Response.json({ error: "Race not found" }, { status: 404 });
  const qualifyingPositions = await getQualifying(round, fresh);
  return Response.json({ predictions: predictRace(drivers, race, qualifyingPositions), source, race, qualifyingAvailable: Object.keys(qualifyingPositions).length > 0, model: trainedModel.version });
}
