export type Driver = { position: number; name: string; code: string; team: string; points: number; wins: number; nationality: string };
export type Race = { round: string; name: string; date: string; time?: string; circuit: string; locality: string; country: string; status: "completed" | "upcoming" };
export type Prediction = { driver: string; team: string; winProbability: number; form: number; confidence: "High" | "Medium" | "Low" };
