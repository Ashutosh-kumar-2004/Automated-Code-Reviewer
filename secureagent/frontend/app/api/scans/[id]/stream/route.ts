import { bffProxy } from "@/lib/proxy";
import { NextRequest } from "next/server";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  return bffProxy(`/api/v1/scans/${id}/stream`);
}
