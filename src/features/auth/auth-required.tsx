"use client";

import { LockKeyhole } from "lucide-react";
import Link from "next/link";

import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { useAuth } from "@/features/auth/auth-provider";

export function AuthRequired({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  if (isLoading) {
    return (
      <LoadingSkeleton className="mx-auto mt-16 h-56 max-w-xl rounded-2xl" />
    );
  }
  if (user) return children;

  return (
    <section className="mx-auto mt-16 max-w-xl rounded-2xl border border-border bg-surface p-8 text-center">
      <LockKeyhole className="mx-auto size-8 text-primary" aria-hidden="true" />
      <h1 className="mt-4 font-literary text-3xl font-semibold">
        Sign-in required
      </h1>
      <p className="mt-3 font-nepali text-muted-foreground">
        Sign in with Google to access your personal content.
      </p>
      <Link
        href="/login"
        className="mt-6 inline-flex rounded-full bg-primary px-5 py-2.5 font-nepali font-semibold text-background"
      >
        Sign in
      </Link>
    </section>
  );
}
