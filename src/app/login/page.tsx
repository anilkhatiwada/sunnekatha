import type { Metadata } from "next";

import { GoogleSignIn } from "@/features/auth/google-sign-in";

export const metadata: Metadata = { title: "Sign in" };

export default function LoginPage() {
  return (
    <div className="mx-auto flex min-h-[65vh] max-w-lg items-center">
      <section className="w-full rounded-2xl border border-border bg-surface p-6 text-center sm:p-10">
        <p className="font-nepali text-sm font-medium text-primary">
          SunneKatha
        </p>
        <h1 className="mt-3 font-literary text-3xl font-semibold">
          Sign in to your account
        </h1>
        <p className="mt-3 mb-8 font-nepali leading-7 text-muted-foreground">
          Use your Google account to keep your library, listening progress, and playlists in sync.
        </p>
        <GoogleSignIn />
      </section>
    </div>
  );
}
