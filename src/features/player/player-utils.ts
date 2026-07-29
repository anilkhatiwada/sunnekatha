import type { QueueItem, Track } from "@/types";

export const DEFAULT_VOLUME = 0.8;
export const DEFAULT_PLAYBACK_SPEED = 1;
export const PREVIOUS_RESTART_THRESHOLD_SECONDS = 5;

export function clamp(value: number, minimum: number, maximum: number) {
  if (!Number.isFinite(value)) {
    return minimum;
  }

  return Math.min(Math.max(value, minimum), maximum);
}

export function clampQueueIndex(index: number, queueLength: number) {
  if (queueLength === 0) {
    return -1;
  }

  return Math.trunc(clamp(index, 0, queueLength - 1));
}

export function createQueueItem(track: Track): QueueItem {
  return {
    id: `${track.id}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    track,
    addedAt: new Date().toISOString(),
  };
}

export function getTrackAtIndex(queue: QueueItem[], index: number) {
  return queue[index]?.track ?? null;
}

export function getRandomQueueIndex(
  queueLength: number,
  currentIndex: number,
) {
  if (queueLength <= 1) {
    return currentIndex;
  }

  const candidate = Math.floor(Math.random() * (queueLength - 1));
  return candidate >= currentIndex ? candidate + 1 : candidate;
}
