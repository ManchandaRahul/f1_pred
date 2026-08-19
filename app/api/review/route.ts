import { getRaces, getSeasonResults, getStandings } from "@/lib/f1-api";

export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  const round = Number(params.get("round"));
  if (!Number.isInteger(round) || round < 1) return Response.json({ error: "A valid round is required" }, { status: 400 });
  const fresh = params.get("refresh") === "1";
  const [{ races, source }, { results }, { drivers }] = await Promise.all([getRaces(fresh), getSeasonResults(fresh), getStandings(fresh)]);
  const race = races.find((item) => Number(item.round) === round);
  if (!race) return Response.json({ error: "Race not found" }, { status: 404 });
  const raceResults = results.filter((result) => result.round === round).sort((a, b) => a.position - b.position);
  const winner = raceResults[0];
  const driver = winner ? drivers.find((item) => item.id === winner.driverId) : undefined;
  return Response.json({
    source,
    race,
    completed: Boolean(winner),
    actualWinner: winner ? { driver: driver?.name ?? winner.driverCode, team: driver?.team ?? winner.teamId, code: winner.driverCode } : null
  });
}
