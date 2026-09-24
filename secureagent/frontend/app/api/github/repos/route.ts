import { bffProxy } from "@/lib/proxy";
import { NextRequest } from "next/server";

export async function GET(req: NextRequest) {
  return bffProxy("/api/v1/github/repos", {
    searchParams: req.nextUrl.searchParams,
  });
}
