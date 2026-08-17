import { apiClient } from "@/services/api-client";
import type {
  AudioAdvertisement,
  PlaybackSource,
} from "@/features/player/player-types";

const SESSION_STORAGE_KEY = "sunnekatha-audio-ad-session";

interface AudioAdvertisementEligibilityResponse {
  advertisement: AudioAdvertisement | null;
  reason: string;
}

type AudioAdvertisementRequest = {
  sessionId: string;
  playbackSequence: number;
  trackId: string;
  source: PlaybackSource;
};

function fallbackUuid() {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (value) => {
    const random = Math.floor(Math.random() * 16);
    const digit = value === "x" ? random : (random & 0x3) | 0x8;
    return digit.toString(16);
  });
}

export function getAudioAdvertisementSessionId() {
  const existing = window.localStorage.getItem(SESSION_STORAGE_KEY);
  if (existing) return existing;
  const created = globalThis.crypto?.randomUUID?.() ?? fallbackUuid();
  window.localStorage.setItem(SESSION_STORAGE_KEY, created);
  return created;
}

export function getNextAudioAdvertisement(
  request: AudioAdvertisementRequest,
) {
  return apiClient.post<
    AudioAdvertisementEligibilityResponse,
    AudioAdvertisementRequest
  >("/audio-ads/next/", {
    body: request,
    requiresAuth: true,
  });
}

export function recordAudioAdvertisementStarted(
  advertisementId: string,
  request: AudioAdvertisementRequest,
) {
  return apiClient.post<{ counted: boolean }, AudioAdvertisementRequest>(
    `/audio-ads/${advertisementId}/started/`,
    { body: request, requiresAuth: true },
  );
}
