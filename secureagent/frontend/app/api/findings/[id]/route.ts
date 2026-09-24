import { bffProxy } from "@/lib/proxy";
import { NextRequest } from "next/server";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  return bffProxy(`/api/v1/findings/${id}`);
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const body = await req.json();
  return bffProxy(`/api/v1/findings/${id}`, {
    method: "PATCH",
    body,
  });
}
