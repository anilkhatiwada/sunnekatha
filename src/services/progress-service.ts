"use client";

import { useLibraryStore } from "@/features/library/library-store";
import type { ListeningProgress } from "@/types";

export const PROGRESS_UPDATE_INTERVAL_SECONDS = 15;

export interface SaveProgressInput {
  trackId: string;
  progressSeconds: number;
  durationSeconds: number;
}

/**
 * Local-first progress boundary. A future Django adapter can sync the normalized
 * record after this immediate local write without changing player code.
 */
export function saveListeningProgress({
  trackId,
  progressSeconds,
  durationSeconds,
}: SaveProgressInput): ListeningProgress | null {
  const safeDuration = Math.max(0, durationSeconds);
  const safeProgress = Math.min(
    safeDuration,
    Math.max(0, progressSeconds),
  );

  if (safeProgress < 1 || safeDuration <= 0) {
    return null;
  }

  useLibraryStore
    .getState()
    .updateListeningProgress(trackId, safeProgress, safeDuration);

  return (
    useLibraryStore
      .getState()
      .listeningProgress.find((item) => item.trackId === trackId) ?? null
  );
}

export function getSavedProgress(trackId: string) {
  return (
    useLibraryStore
      .getState()
      .listeningProgress.find((item) => item.trackId === trackId) ?? null
  );
}

export function getResumePosition(trackId: string) {
  const progress = getSavedProgress(trackId);

  return progress && !progress.isCompleted
    ? progress.progressSeconds
    : 0;
}

export function recordRecentlyPlayed(trackId: string) {
  useLibraryStore.getState().addRecentlyPlayed(trackId);
}
