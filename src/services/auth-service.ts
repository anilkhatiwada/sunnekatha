import { apiClient } from "@/services/api-client";
import { setAuthTokens } from "@/services/auth-session";
import type { LoginResponse } from "@/types";

export async function loginWithGoogle(
  credential: string,
): Promise<LoginResponse["user"]> {
  const response = await apiClient.post<
    LoginResponse,
    { credential: string }
  >("/auth/google/", {
    body: { credential },
    headers: { "X-SunneKatha-Auth": "google" },
  });
  setAuthTokens({
    access: response.access,
    refresh: response.refresh,
  });
  return response.user;
}
