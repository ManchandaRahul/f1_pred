import { fallbackDrivers, fallbackRaces } from "./fallback-data";
import type { CompletedRaceResult, Driver, Race } from "./types";

const base = process.env.F1_API_BASE_URL ?? "https://api.jolpi.ca/ergast/f1";

type JolpicaDriver = { driverId: string; code?: string; givenName: string; familyName: string; nationality: string };
type JolpicaConstructor = { constructorId: string; name: string };
type JolpicaCircuit = { circuitId: string; circuitName: string; Location: { locality: string; country: string } };
type JolpicaResult = { position: string; status?: string; Driver: JolpicaDriver; Constructor: JolpicaConstructor };
type JolpicaRace = { round: string; raceName: string; date: string; time?: string; Circuit: JolpicaCircuit; Results?: JolpicaResult[]; QualifyingResults?: Array<{ position: string; Driver: JolpicaDriver }> };
type JolpicaResponse = { MRData?: { limit?: string; total?: string; RaceTable?: { Races?: JolpicaRace[] }; StandingsTable?: { StandingsLists?: Array<{ DriverStandings?: Array<{ position: string; points: string; wins: string; Driver: JolpicaDriver; Constructors?: JolpicaConstructor[] }> }> } } };

async function f1Fetch(path: string, fresh = false): Promise<JolpicaResponse> {
  const response = await fetch(`${base}/${path}`, fresh ? { cache: "no-store" } : { next: { revalidate: 900 } });
  if (!response.ok) throw new Error(`F1 source returned ${response.status}`);
  return response.json() as Promise<JolpicaResponse>;
}

export async function getStandings(fresh = false): Promise<{ drivers: Driver[]; source: "live" | "fallback" }> {
  try {
    const json = await f1Fetch("current/driverstandings.json", fresh);
    const rows = json.MRData?.StandingsTable?.StandingsLists?.[0]?.DriverStandings ?? [];
    if (!rows.length) throw new Error("No current standings");
    return {
      source: "live",
      drivers: rows.map((row) => ({
        id: row.Driver.driverId,
        position: Number(row.position),
        name: `${row.Driver.givenName} ${row.Driver.familyName}`,
        code: row.Driver.code ?? row.Driver.driverId.slice(0, 3).toUpperCase(),
        teamId: row.Constructors?.[0]?.constructorId ?? "unknown",
        team: row.Constructors?.[0]?.name ?? "—",
        points: Number(row.points),
        wins: Number(row.wins),
        nationality: row.Driver.nationality
      }))
    };
  } catch (error) {
    console.error("Standings source unavailable; using fallback data", error);
    return { drivers: fallbackDrivers, source: "fallback" };
  }
}

export async function getRaces(fresh = false): Promise<{ races: Race[]; source: "live" | "fallback" }> {
  try {
    const json = await f1Fetch("current.json", fresh);
    const now = new Date().toISOString().slice(0, 10);
    const rows = json.MRData?.RaceTable?.Races ?? [];
    if (!rows.length) throw new Error("No current calendar");
    return {
      source: "live",
      races: rows.map((row) => ({
        round: row.round,
        name: row.raceName,
        date: row.date,
        time: row.time,
        circuitId: row.Circuit.circuitId,
        circuit: row.Circuit.circuitName,
        locality: row.Circuit.Location.locality,
        country: row.Circuit.Location.country,
        status: row.date < now ? "completed" : "upcoming"
      }))
    };
  } catch (error) {
    console.error("Calendar source unavailable; using fallback data", error);
    const now = new Date().toISOString().slice(0, 10);
    return { races: fallbackRaces.map((race) => ({ ...race, status: race.date < now ? "completed" : "upcoming" })), source: "fallback" };
  }
}

export async function getQualifying(round: string, fresh = false): Promise<Record<string, number>> {
  try {
    const json = await f1Fetch(`current/${round}/qualifying.json`, fresh);
    const results = json.MRData?.RaceTable?.Races?.[0]?.QualifyingResults ?? [];
    return Object.fromEntries(results.map((result) => [result.Driver.code ?? result.Driver.driverId.slice(0, 3).toUpperCase(), Number(result.position)]));
  } catch {
    return {};
  }
}

export async function getSeasonResults(fresh = false): Promise<{ results: CompletedRaceResult[]; throughRound: number }> {
  try {
    const first = await f1Fetch("current/results.json?limit=100&offset=0", fresh);
    const limit = Number(first.MRData?.limit ?? 100);
    const total = Number(first.MRData?.total ?? 0);
    const offsets = Array.from({ length: Math.max(0, Math.ceil(total / limit) - 1) }, (_, index) => (index + 1) * limit);
    const pages = await Promise.all(offsets.map((offset) => f1Fetch(`current/results.json?limit=${limit}&offset=${offset}`, fresh)));
    const races = [first, ...pages].flatMap((page) => page.MRData?.RaceTable?.Races ?? []);
    const results: CompletedRaceResult[] = races.flatMap((race) => (race.Results ?? []).map((result) => ({
      round: Number(race.round),
      circuitId: race.Circuit.circuitId,
      driverId: result.Driver.driverId,
      driverCode: result.Driver.code ?? result.Driver.driverId.slice(0, 3).toUpperCase(),
      teamId: result.Constructor.constructorId,
      position: Number(result.position),
      status: result.status ?? ""
    })));
    return { results, throughRound: Math.max(0, ...results.map((result) => result.round)) };
  } catch (error) {
    console.error("Completed-race form source unavailable; using model priors", error);
    return { results: [], throughRound: 0 };
  }
}
