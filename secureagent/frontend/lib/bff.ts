/**
 * BFF (Backend for Frontend) JWT utility.
 * SERVER-SIDE ONLY — never import in Client Components or pages.tsx.
 *
 * Mints a short-lived HS256 JWT that FastAPI will validate.
 * The browser never sees this token.
 */
import { SignJWT } from "jose";

const BACKEND_SECRET = process.env.BACKEND_SECRET!;
const JWT_EXPIRY_SECONDS = parseInt(process.env.JWT_EXPIRY_SECONDS || "600", 10);

if (!BACKEND_SECRET && process.env.NODE_ENV === "production") {
  throw new Error("BACKEND_SECRET environment variable is not set");
}

/**
 * Mint a short-lived HS256 JWT for authenticating with FastAPI.
 * @param userId  The internal user ID (stored in NextAuth session)
 * @param githubLogin  The GitHub username (for logging / display)
 */
export async function mintBffJwt(userId: string, githubLogin: string): Promise<string> {
  const secret = new TextEncoder().encode(BACKEND_SECRET);
  return new SignJWT({ sub: userId, login: githubLogin })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime(`${JWT_EXPIRY_SECONDS}s`)
    .sign(secret);
}

/**
 * Base URL of the FastAPI backend — server-side only.
 * Strips any trailing slash to prevent double-slash errors with cloud URLs.
 */
export const BACKEND_URL = (
  process.env.BACKEND_URL || "http://localhost:8000"
).replace(/\/+$/, "");

