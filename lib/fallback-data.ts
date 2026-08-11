import type { Driver, Race } from "./types";

export const fallbackDrivers: Driver[] = [
  { id: "antonelli", position: 1, name: "Andrea Kimi Antonelli", code: "ANT", teamId: "mercedes", team: "Mercedes", points: 219, wins: 6, nationality: "Italian" },
  { id: "hamilton", position: 2, name: "Lewis Hamilton", code: "HAM", teamId: "ferrari", team: "Ferrari", points: 169, wins: 1, nationality: "British" },
  { id: "russell", position: 3, name: "George Russell", code: "RUS", teamId: "mercedes", team: "Mercedes", points: 160, wins: 2, nationality: "British" },
  { id: "leclerc", position: 4, name: "Charles Leclerc", code: "LEC", teamId: "ferrari", team: "Ferrari", points: 138, wins: 1, nationality: "Monegasque" },
  { id: "norris", position: 5, name: "Lando Norris", code: "NOR", teamId: "mclaren", team: "McLaren", points: 128, wins: 1, nationality: "British" }
];

export const fallbackRaces: Race[] = [
  { round: "11", name: "Hungarian Grand Prix", date: "2026-07-26", circuitId: "hungaroring", circuit: "Hungaroring", locality: "Mogyoród", country: "Hungary", status: "completed" },
  { round: "12", name: "Dutch Grand Prix", date: "2026-08-23", circuitId: "zandvoort", circuit: "Circuit Zandvoort", locality: "Zandvoort", country: "Netherlands", status: "upcoming" },
  { round: "13", name: "Italian Grand Prix", date: "2026-09-06", circuitId: "monza", circuit: "Autodromo Nazionale Monza", locality: "Monza", country: "Italy", status: "upcoming" },
  { round: "10", name: "Belgian Grand Prix", date: "2026-07-19", circuitId: "spa", circuit: "Circuit de Spa-Francorchamps", locality: "Stavelot", country: "Belgium", status: "completed" }
];
