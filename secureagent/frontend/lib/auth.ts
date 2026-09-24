/**
 * NextAuth (Auth.js v5) configuration.
 * Stored server-side — never exposed to the browser.
 * The GitHub access_token is stored in the server-side session,
 * then sent to FastAPI via the BFF JWT mechanism (lib/bff.ts).
 */
import NextAuth from "next-auth";
import GitHub from "next-auth/providers/github";
import { BACKEND_URL } from "@/lib/bff";

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    GitHub({
      clientId: process.env.GITHUB_CLIENT_ID!,
      clientSecret: process.env.GITHUB_CLIENT_SECRET!,
      authorization: {
        params: {
          scope: "read:user user:email repo",
        },
      },
    }),
  ],
  callbacks: {
    async jwt({ token, account, profile }) {
      // Store GitHub OAuth data in the JWT at sign-in time
      if (account && profile) {
        token.githubId = String((profile as any).id);
        token.login = (profile as any).login;
        token.avatarUrl = (profile as any).avatar_url;
        token.accessToken = account.access_token;

        // Sync with FastAPI backend
        try {
          await fetch(`${BACKEND_URL}/api/v1/auth/validate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              github_id: token.githubId,
              login: token.login,
              email: (profile as any).email || null,
              avatar_url: token.avatarUrl || null,
              access_token: account.access_token,
            }),
          });
        } catch (e) {
          console.error("Failed to sync user with FastAPI backend:", e);
        }
      }
      return token;
    },
    async session({ session, token }) {
      // Make user metadata available to server-side code (Route Handlers)
      // accessToken is ONLY in the JWT — never serialized into the session object
      // that gets sent to the browser.
      session.user.id = token.sub!;
      (session as any).githubId = token.githubId;
      (session as any).login = token.login;
      (session as any).avatarUrl = token.avatarUrl;
      (session as any).accessToken = token.accessToken; // server-side only
      return session;
    },
  },
  pages: {
    signIn: "/login",
    error: "/login",
  },
  session: {
    strategy: "jwt",
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
  secret: process.env.NEXTAUTH_SECRET,
});
