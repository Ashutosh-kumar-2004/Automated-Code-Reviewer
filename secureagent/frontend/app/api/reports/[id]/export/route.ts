import { bffProxy } from "@/lib/proxy";
import { NextRequest } from "next/server";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const searchParams = req.nextUrl.searchParams;
  return bffProxy(`/api/v1/reports/${id}/export`, { searchParams });
}
