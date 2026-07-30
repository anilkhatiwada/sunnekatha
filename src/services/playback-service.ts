"use client";

import { environment } from "@/config/environment";
import { hasStoredSession } from "@/services/auth-service";
import { apiClient } from "@/services/api-client";
import type { ApiPlaybackSession } from "@/types";

export type PlaybackUpdateEvent =
  | "resumed"
  | "paused"
  | "seeked"
  | "error";

function createClientEventId() {
  return crypto.randomUUID();
}

function getDeviceId() {
  const key = "sunnekatha:device-id";
  const existing = window.localStorage.getItem(key);
  if (existing) return existing;
  const value = crypto.randomUUID();
  window.localStorage.setItem(key, value);
  return value;
}

function canSyncPlayback() {
  return environment.apiMode === "remote" && hasStoredSession();
}

export async function startPlaybackSession(
  trackId: string,
  positionSeconds: number,
) {
  if (!canSyncPlayback()) return null;
  return apiClient.post<
    ApiPlaybackSession,
    {
      trackId: string;
      deviceId: string;
      positionSeconds: number;
      clientEventId: string;
    }
  >("/me/playback-sessions/", {
    body: {
      trackId,
      deviceId: getDeviceId(),
      positionSeconds,
      clientEventId: createClientEventId(),
    },
    requiresAuth: true,
  });
}

export async function updatePlaybackSession(
  sessionId: string,
  input: {
    listenedSeconds: number;
    eventType?: PlaybackUpdateEvent;
    positionSeconds?: number;
  },
) {
  if (!canSyncPlayback()) return null;
  return apiClient.patch<
    ApiPlaybackSession,
    typeof input & { clientEventId: string }
  >(`/me/playback-sessions/${sessionId}/`, {
    body: { ...input, clientEventId: createClientEventId() },
    requiresAuth: true,
  });
}

export async function endPlaybackSession(
  sessionId: string,
  input: {
    listenedSeconds: number;
    completed: boolean;
    positionSeconds: number;
  },
) {
  if (!canSyncPlayback()) return null;
  return apiClient.post<
    ApiPlaybackSession,
    typeof input & { clientEventId: string }
  >(`/me/playback-sessions/${sessionId}/end/`, {
    body: { ...input, clientEventId: createClientEventId() },
    requiresAuth: true,
  });
}
