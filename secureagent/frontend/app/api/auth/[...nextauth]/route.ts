/**
 * NextAuth route handler — handles GitHub OAuth callbacks.
 * This is the only NextAuth endpoint; all other /api/* are BFF proxies.
 */
import { handlers } from "@/lib/auth";

export const { GET, POST } = handlers;
