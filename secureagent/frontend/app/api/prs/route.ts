import { bffProxy } from "@/lib/proxy";
import { NextRequest } from "next/server";

export async function GET() {
  return bffProxy("/api/v1/prs");
}

export async function POST(req: NextRequest) {
  const body = await req.json();
  return bffProxy("/api/v1/prs", { method: "POST", body });
}
