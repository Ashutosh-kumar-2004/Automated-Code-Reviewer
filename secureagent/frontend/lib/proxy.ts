/**
 * BFF proxy helper — used by all /api/* Route Handlers.
 * Mints a BFF JWT and forwards the request to FastAPI.
 * The GitHub access_token from the session is also forwarded
 * to FastAPI's /auth/validate endpoint on login, but never
 * to other endpoints.
 */
import { auth } from "@/lib/auth";
import { mintBffJwt, BACKEND_URL } from "@/lib/bff";
import { NextRequest, NextResponse } from "next/server";

type ProxyOptions = {
  method?: string;
  body?: unknown;
  searchParams?: URLSearchParams;
};

export async function bffProxy(
  backendPath: string,
  options: ProxyOptions = {}
): Promise<NextResponse> {
  const session = await auth();
  if (!session?.user) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const userId = (session as any).githubId as string;
  const login = (session as any).login as string;

  // Mint a short-lived BFF JWT (server-side only)
  const bffToken = await mintBffJwt(userId, login);

  const url = new URL(`${BACKEND_URL}${backendPath}`);
  if (options.searchParams) {
    options.searchParams.forEach((v, k) => url.searchParams.set(k, v));
  }

  const headers: Record<string, string> = {
    Authorization: `Bearer ${bffToken}`,
    "Content-Type": "application/json",
  };

  const fetchOptions: RequestInit = {
    method: options.method || "GET",
    headers,
  };

  if (options.body) {
    fetchOptions.body = JSON.stringify(options.body);
  }

  try {
    let resp = await fetch(url.toString(), fetchOptions);

    // If 401 (e.g. user not found in backend yet), try auto-syncing user and retry once
    if (resp.status === 401 && (session as any)?.accessToken) {
      try {
        await fetch(`${BACKEND_URL}/api/v1/auth/validate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            github_id: String(userId),
            login: login || "user",
            email: session.user.email || null,
            avatar_url: (session as any).avatarUrl || session.user.image || null,
            access_token: (session as any).accessToken,
          }),
        });
        // Retry original request
        resp = await fetch(url.toString(), fetchOptions);
      } catch (syncErr) {
        console.error("Auto-sync error:", syncErr);
      }
    }

    const contentType = resp.headers.get("content-type") || "";

    if (contentType.includes("text/event-stream")) {
      // Re-stream SSE — pass through as-is
      return new NextResponse(resp.body, {
        status: resp.status,
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
          Connection: "keep-alive",
          "X-Accel-Buffering": "no",
        },
      });
    }

    if (resp.status === 204) {
      return new NextResponse(null, { status: 204 });
    }

    if (contentType.includes("text/markdown") || contentType.includes("text/plain")) {
      const text = await resp.text();
      const contentDisposition = resp.headers.get("content-disposition");
      return new NextResponse(text, {
        status: resp.status,
        headers: {
          "Content-Type": contentType,
          ...(contentDisposition ? { "Content-Disposition": contentDisposition } : {}),
        },
      });
    }

    const data = await resp.json().catch(() => null);
    return NextResponse.json(data, { status: resp.status });
  } catch (err) {
    console.error(`BFF proxy error for ${backendPath}:`, err);
    return NextResponse.json(
      { detail: "Backend connection failed" },
      { status: 502 }
    );
  }
}

/**
 * Get the session's GitHub access token (for /auth/validate only).
 * MUST NOT be used for any other purpose.
 */
export async function getSessionAccessToken(): Promise<string | null> {
  const session = await auth();
  return (session as any)?.accessToken ?? null;
}
