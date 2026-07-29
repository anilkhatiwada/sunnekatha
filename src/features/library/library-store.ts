"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { ListeningProgress, UserLibrary } from "@/types";

const COMPLETION_THRESHOLD = 0.9;

interface LibraryStore {
  hasHydrated: boolean;
  hasInitialized: boolean;
  savedPlaylistIds: string[];
  favoriteTrackIds: string[];
  followedAuthorIds: string[];
  followedNarratorIds: string[];
  recentlyPlayedTrackIds: string[];
  listeningProgress: ListeningProgress[];
  setHasHydrated: (hasHydrated: boolean) => void;
  initializeLibrary: (library: UserLibrary) => void;
  toggleSavedPlaylist: (playlistId: string) => void;
  toggleFavoriteTrack: (trackId: string) => void;
  toggleFollowedAuthor: (authorId: string) => void;
  toggleFollowedNarrator: (narratorId: string) => void;
  addRecentlyPlayed: (trackId: string) => void;
  updateListeningProgress: (
    trackId: string,
    progressSeconds: number,
    durationSeconds: number,
  ) => void;
}

export const useLibraryStore = create<LibraryStore>()(
  persist(
    (set) => ({
      hasHydrated: false,
      hasInitialized: false,
      savedPlaylistIds: [],
      favoriteTrackIds: [],
      followedAuthorIds: [],
      followedNarratorIds: [],
      recentlyPlayedTrackIds: [],
      listeningProgress: [],
      setHasHydrated: (hasHydrated) => set({ hasHydrated }),
      initializeLibrary: (library) =>
        set((state) => {
          if (state.hasInitialized) return state;

          return {
            hasInitialized: true,
            savedPlaylistIds: mergeIds(
              library.savedPlaylistIds,
              state.savedPlaylistIds,
            ),
            favoriteTrackIds: mergeIds(
              library.favoriteTrackIds,
              state.favoriteTrackIds,
            ),
            followedAuthorIds: mergeIds(
              library.followedAuthorIds,
              state.followedAuthorIds,
            ),
            followedNarratorIds: mergeIds(
              library.followedNarratorIds,
              state.followedNarratorIds,
            ),
            recentlyPlayedTrackIds: mergeIds(
              state.recentlyPlayedTrackIds,
              library.recentlyPlayedTrackIds,
            ).slice(0, 20),
            listeningProgress: mergeProgress(
              library.listeningProgress,
              state.listeningProgress,
            ),
          };
        }),
      toggleSavedPlaylist: (playlistId) =>
        set((state) => ({
          savedPlaylistIds: state.savedPlaylistIds.includes(playlistId)
            ? state.savedPlaylistIds.filter((id) => id !== playlistId)
            : [...state.savedPlaylistIds, playlistId],
        })),
      toggleFavoriteTrack: (trackId) =>
        set((state) => ({
          favoriteTrackIds: state.favoriteTrackIds.includes(trackId)
            ? state.favoriteTrackIds.filter((id) => id !== trackId)
            : [...state.favoriteTrackIds, trackId],
        })),
      toggleFollowedAuthor: (authorId) =>
        set((state) => ({
          followedAuthorIds: state.followedAuthorIds.includes(authorId)
            ? state.followedAuthorIds.filter((id) => id !== authorId)
            : [...state.followedAuthorIds, authorId],
        })),
      toggleFollowedNarrator: (narratorId) =>
        set((state) => ({
          followedNarratorIds: state.followedNarratorIds.includes(narratorId)
            ? state.followedNarratorIds.filter((id) => id !== narratorId)
            : [...state.followedNarratorIds, narratorId],
        })),
      addRecentlyPlayed: (trackId) =>
        set((state) => ({
          recentlyPlayedTrackIds: [
            trackId,
            ...state.recentlyPlayedTrackIds.filter((id) => id !== trackId),
          ].slice(0, 20),
        })),
      updateListeningProgress: (
        trackId,
        progressSeconds,
        durationSeconds,
      ) =>
        set((state) => {
          const safeDuration = Math.max(0, durationSeconds);
          const safeProgress = Math.min(
            safeDuration,
            Math.max(0, progressSeconds),
          );
          const progress: ListeningProgress = {
            trackId,
            progressSeconds: safeProgress,
            durationSeconds: safeDuration,
            isCompleted:
              safeDuration > 0 &&
              safeProgress / safeDuration >= COMPLETION_THRESHOLD,
            updatedAt: new Date().toISOString(),
          };

          return {
            listeningProgress: [
              progress,
              ...state.listeningProgress.filter(
                (item) => item.trackId !== trackId,
              ),
            ].slice(0, 50),
          };
        }),
    }),
    {
      name: "sunnekatha-library",
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
      partialize: (state) => ({
        hasInitialized: state.hasInitialized,
        savedPlaylistIds: state.savedPlaylistIds,
        favoriteTrackIds: state.favoriteTrackIds,
        followedAuthorIds: state.followedAuthorIds,
        followedNarratorIds: state.followedNarratorIds,
        recentlyPlayedTrackIds: state.recentlyPlayedTrackIds,
        listeningProgress: state.listeningProgress,
      }),
    },
  ),
);

function mergeIds(primary: string[], secondary: string[]) {
  return [...new Set([...primary, ...secondary])];
}

function mergeProgress(
  defaults: ListeningProgress[],
  current: ListeningProgress[],
) {
  const progressByTrack = new Map(
    defaults.map((progress) => [progress.trackId, progress]),
  );

  for (const progress of current) {
    progressByTrack.set(progress.trackId, progress);
  }

  return [...progressByTrack.values()].sort(
    (a, b) =>
      new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime(),
  );
}
