"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

import { AudioEngine } from "@/features/player/audio-engine";
import { PlayerKeyboardShortcuts } from "@/features/player/player-keyboard-shortcuts";
import { PreferencesController } from "@/features/profile/preferences-controller";
import { AuthProvider } from "@/features/auth/auth-provider";

interface AppProvidersProps {
  children: React.ReactNode;
}

export function AppProviders({ children }: AppProvidersProps) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60_000,
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <PreferencesController />
        <AudioEngine />
        <PlayerKeyboardShortcuts />
        {children}
      </AuthProvider>
    </QueryClientProvider>
  );
}
