export type Driver = { id: string; position: number; name: string; code: string; teamId: string; team: string; points: number; wins: number; nationality: string };
export type Race = { round: string; name: string; date: string; time?: string; circuitId: string; circuit: string; locality: string; country: string; status: "completed" | "upcoming" };
export type Prediction = { driver: string; team: string; winProbability: number; form: number; confidence: "High" | "Medium" | "Low" };
export type CompletedRaceResult = { round: number; circuitId: string; driverId: string; driverCode: string; teamId: string; position: number; status: string };
