import type { Driver, Race } from "./types";
export const fallbackDrivers: Driver[] = [
  { position: 1, name: "Oscar Piastri", code: "PIA", team: "McLaren", points: 198, wins: 5, nationality: "Australian" },
  { position: 2, name: "Lando Norris", code: "NOR", team: "McLaren", points: 176, wins: 2, nationality: "British" },
  { position: 3, name: "Max Verstappen", code: "VER", team: "Red Bull Racing", points: 155, wins: 2, nationality: "Dutch" },
  { position: 4, name: "George Russell", code: "RUS", team: "Mercedes", points: 136, wins: 1, nationality: "British" },
  { position: 5, name: "Charles Leclerc", code: "LEC", team: "Ferrari", points: 104, wins: 0, nationality: "Monegasque" }
];
export const fallbackRaces: Race[] = [
  { round: "14", name: "Hungarian Grand Prix", date: "2026-07-26", circuit: "Hungaroring", locality: "Mogyoród", country: "Hungary", status: "upcoming" },
  { round: "15", name: "Dutch Grand Prix", date: "2026-08-23", circuit: "Circuit Zandvoort", locality: "Zandvoort", country: "Netherlands", status: "upcoming" },
  { round: "16", name: "Italian Grand Prix", date: "2026-09-06", circuit: "Autodromo Nazionale Monza", locality: "Monza", country: "Italy", status: "upcoming" },
  { round: "13", name: "Belgian Grand Prix", date: "2026-07-19", circuit: "Circuit de Spa-Francorchamps", locality: "Stavelot", country: "Belgium", status: "completed" }
];
