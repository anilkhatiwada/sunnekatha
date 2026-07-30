"use client";

import { Bell, CircleUserRound, LogIn, Search } from "lucide-react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { Logo } from "@/components/layout/logo";
import { PwaInstallButton } from "@/components/pwa/pwa-install-button";
import { useAuth } from "@/features/auth/auth-provider";
import { getUnreadNotificationCount, queryKeys } from "@/services";

export function AppHeader() {
  const { user } = useAuth();
  const unreadQuery = useQuery({
    queryKey: queryKeys.notifications.unread(),
    queryFn: getUnreadNotificationCount,
    enabled: Boolean(user),
    staleTime: 30_000,
  });
  return (
    <header className="sticky top-0 z-20 h-16 border-b border-border/70 bg-background/82 backdrop-blur-xl">
      <div className="flex h-full items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <Logo className="lg:hidden" />

        <div className="hidden min-w-0 lg:block">
          <p className="font-nepali text-sm text-muted-foreground">
            नेपाली श्रव्य साहित्य
          </p>
          <p className="truncate text-xs text-muted-foreground/65">
            Stories that stay with you
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <PwaInstallButton />
          {user ? (
            <Link
              href="/notifications"
              aria-label={`सूचनाहरू${unreadQuery.data?.unreadCount ? `, ${unreadQuery.data.unreadCount} नपढिएका` : ""}`}
              className="relative inline-flex size-11 items-center justify-center rounded-full border border-border bg-surface text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground focus-visible:outline-2 focus-visible:outline-primary"
            >
              <Bell aria-hidden="true" className="size-[1.1rem]" />
              {unreadQuery.data?.unreadCount ? (
                <span className="absolute top-1.5 right-1.5 min-w-4 rounded-full bg-primary px-1 text-center text-[0.6rem] font-bold leading-4 text-background">
                  {Math.min(unreadQuery.data.unreadCount, 99)}
                </span>
              ) : null}
            </Link>
          ) : null}
          <Link
            href={user ? "/profile" : "/login"}
            aria-label={
              user ? `${user.displayName} को प्रोफाइल` : "साइन इन गर्नुहोस्"
            }
            className="inline-flex size-11 items-center justify-center rounded-full border border-border bg-surface text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground focus-visible:outline-2 focus-visible:outline-primary"
          >
            {user ? (
              <CircleUserRound aria-hidden="true" className="size-[1.1rem]" />
            ) : (
              <LogIn aria-hidden="true" className="size-[1.1rem]" />
            )}
          </Link>
          <Link
            href="/search"
            aria-label="सामग्री खोज्नुहोस्"
            className="inline-flex size-11 items-center justify-center rounded-full border border-border bg-surface text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground focus-visible:outline-2 focus-visible:outline-primary sm:w-auto sm:gap-2 sm:px-4"
          >
            <Search aria-hidden="true" className="size-[1.1rem]" />
            <span className="hidden font-nepali text-sm sm:inline">
              खोज्नुहोस्
            </span>
          </Link>
        </div>
      </div>
    </header>
  );
}
