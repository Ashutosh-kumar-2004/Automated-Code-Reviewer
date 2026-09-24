import { bffProxy } from "@/lib/proxy";
import { NextRequest } from "next/server";

export async function GET() {
  return bffProxy("/api/v1/repos");
}

export async function POST(req: NextRequest) {
  const body = await req.json();
  return bffProxy("/api/v1/repos", {
    method: "POST",
    body,
  });
}
