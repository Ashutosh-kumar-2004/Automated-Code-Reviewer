import { bffProxy } from "@/lib/proxy";
import { NextRequest } from "next/server";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  return bffProxy(`/api/v1/repos/${id}`);
}

export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  return bffProxy(`/api/v1/repos/${id}`, { method: "DELETE" });
}
