import { apiClient } from "@/services/api-client";
import type { ApiUserQueue } from "@/types";

export function getCurrentQueue() {
  return apiClient.get<ApiUserQueue>("/me/queue/", { requiresAuth: true });
}

export function replaceSynchronizedQueue(input: {
  trackIds: string[];
  currentIndex: number;
  positionSeconds: number;
}) {
  return apiClient.put<ApiUserQueue, typeof input>("/me/queue/", {
    body: input,
    requiresAuth: true,
  });
}

export function clearSynchronizedQueue() {
  return apiClient.delete<void>("/me/queue/", { requiresAuth: true });
}

export function updateSynchronizedQueuePosition(input: {
  currentIndex: number;
  positionSeconds: number;
}) {
  return apiClient.patch<ApiUserQueue, typeof input>("/me/queue/position/", {
    body: input,
    requiresAuth: true,
  });
}

export function updateSynchronizedQueueShuffle(isShuffleEnabled: boolean) {
  return apiClient.patch<ApiUserQueue, { isShuffleEnabled: boolean }>(
    "/me/queue/shuffle/",
    { body: { isShuffleEnabled }, requiresAuth: true },
  );
}

export function updateSynchronizedQueueRepeat(
  repeatMode: "off" | "one" | "all",
) {
  return apiClient.patch<ApiUserQueue, { repeatMode: "off" | "one" | "all" }>(
    "/me/queue/repeat/",
    { body: { repeatMode }, requiresAuth: true },
  );
}
