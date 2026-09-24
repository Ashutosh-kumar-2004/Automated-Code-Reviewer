import { bffProxy } from "@/lib/proxy";
import { NextRequest } from "next/server";

export async function POST(req: NextRequest) {
  const body = await req.json();
  return bffProxy("/api/v1/scans", {
    method: "POST",
    body,
  });
}
