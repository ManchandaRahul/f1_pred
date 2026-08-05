import { fallbackDrivers, fallbackRaces } from "./fallback-data";
import type { Driver, Race } from "./types";
const base = process.env.F1_API_BASE_URL ?? "https://api.jolpi.ca/ergast/f1";
async function f1Fetch(path: string, fresh = false) { const r = await fetch(`${base}/${path}`, fresh ? { cache: "no-store" } : { next: { revalidate: 900 } }); if (!r.ok) throw new Error(`F1 source returned ${r.status}`); return r.json(); }
export async function getStandings(fresh = false): Promise<{ drivers: Driver[]; source: "live" | "fallback" }> {
  try { const json = await f1Fetch("current/driverstandings.json", fresh); const rows = json.MRData?.StandingsTable?.StandingsLists?.[0]?.DriverStandings ?? [];
    if (!rows.length) throw new Error("No current standings");
    return { source: "live", drivers: rows.map((d: any) => ({ position: Number(d.position), name: `${d.Driver.givenName} ${d.Driver.familyName}`, code: d.Driver.code ?? d.Driver.driverId.slice(0,3).toUpperCase(), team: d.Constructors?.[0]?.name ?? "—", points: Number(d.points), wins: Number(d.wins), nationality: d.Driver.nationality })) };
  } catch { return { drivers: fallbackDrivers, source: "fallback" }; }
}
export async function getRaces(fresh = false): Promise<{ races: Race[]; source: "live" | "fallback" }> {
  try { const json = await f1Fetch("current.json", fresh); const now = new Date().toISOString().slice(0,10); const rows = json.MRData?.RaceTable?.Races ?? [];
    if (!rows.length) throw new Error("No current calendar");
    return { source: "live", races: rows.map((r: any) => ({ round: r.round, name: r.raceName, date: r.date, time: r.time, circuit: r.Circuit.circuitName, locality: r.Circuit.Location.locality, country: r.Circuit.Location.country, status: r.date < now ? "completed" : "upcoming" })) };
  } catch { return { races: fallbackRaces, source: "fallback" }; }
}
export async function getQualifying(round: string, fresh = false): Promise<Record<string, number>> {
  try {
    const json = await f1Fetch(`current/${round}/qualifying.json`, fresh);
    const results = json.MRData?.RaceTable?.Races?.[0]?.QualifyingResults ?? [];
    return Object.fromEntries(results.map((result: any) => [result.Driver.code ?? result.Driver.driverId.toUpperCase(), Number(result.position)]));
  } catch { return {}; }
}
