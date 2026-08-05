import { getStandings } from "@/lib/f1-api";
export async function GET(request: Request) { return Response.json(await getStandings(new URL(request.url).searchParams.get("refresh") === "1")); }
