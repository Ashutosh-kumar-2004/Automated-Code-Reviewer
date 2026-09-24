import { bffProxy } from "@/lib/proxy";

export async function GET() {
  return bffProxy("/api/v1/reports");
}
