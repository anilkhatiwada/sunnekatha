"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useContext } from "react";

import {
  getCurrentUser,
  hasStoredSession,
  logoutCurrentUser,
  queryKeys,
} from "@/services";
import type { AuthenticatedUserDomain } from "@/services";

interface AuthContextValue {
  user: AuthenticatedUserDomain | null;
  isLoading: boolean;
  refreshUser: () => Promise<unknown>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const hasSession = hasStoredSession();
  const currentUser = useQuery({
    queryKey: queryKeys.auth.currentUser(),
    queryFn: getCurrentUser,
    enabled: hasSession,
    retry: false,
  });

  return (
    <AuthContext.Provider
      value={{
        user: currentUser.data ?? null,
        isLoading: hasSession && currentUser.isPending,
        refreshUser: () => currentUser.refetch(),
        logout: async () => {
          await logoutCurrentUser();
          queryClient.removeQueries({ queryKey: queryKeys.auth.all });
        },
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider.");
  return value;
}
