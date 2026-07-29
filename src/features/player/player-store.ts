"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type {
  PersistedPlayerState,
  PlayerState,
  PlayerStore,
} from "@/features/player/player-types";
import {
  clamp,
  clampQueueIndex,
  createQueueItem,
  DEFAULT_PLAYBACK_SPEED,
  DEFAULT_VOLUME,
  getRandomQueueIndex,
  getTrackAtIndex,
  PREVIOUS_RESTART_THRESHOLD_SECONDS,
} from "@/features/player/player-utils";

const initialState: PlayerState = {
  currentTrack: null,
  queue: [],
  currentQueueIndex: -1,
  isPlaying: false,
  currentTime: 0,
  duration: 0,
  volume: DEFAULT_VOLUME,
  isMuted: false,
  playbackSpeed: DEFAULT_PLAYBACK_SPEED,
  isShuffleEnabled: false,
  repeatMode: "off",
  isLoading: false,
  playbackError: null,
};

export const usePlayerStore = create<PlayerStore>()(
  persist(
    (set, get) => ({
      ...initialState,

      play: (track) => {
        if (!track) {
          if (get().currentTrack) {
            set({ isPlaying: true, playbackError: null });
          }
          return;
        }

        const existingIndex = get().queue.findIndex(
          (item) => item.track.id === track.id,
        );
        const queue =
          existingIndex >= 0 ? get().queue : [...get().queue, createQueueItem(track)];
        const currentQueueIndex =
          existingIndex >= 0 ? existingIndex : queue.length - 1;

        set({
          queue,
          currentQueueIndex,
          currentTrack: track,
          currentTime: 0,
          duration: track.duration,
          isPlaying: true,
          isLoading: false,
          playbackError: null,
        });
      },

      pause: () => set({ isPlaying: false }),
      togglePlay: () => {
        if (get().currentTrack) {
          set((state) => ({ isPlaying: !state.isPlaying }));
        }
      },

      next: () => {
        const state = get();
        if (state.queue.length === 0) return;

        let nextIndex: number;
        if (state.isShuffleEnabled) {
          nextIndex = getRandomQueueIndex(
            state.queue.length,
            state.currentQueueIndex,
          );
        } else if (state.currentQueueIndex < state.queue.length - 1) {
          nextIndex = state.currentQueueIndex + 1;
        } else if (state.repeatMode === "all") {
          nextIndex = 0;
        } else {
          set({ isPlaying: false, currentTime: state.duration });
          return;
        }

        const currentTrack = getTrackAtIndex(state.queue, nextIndex);
        set({
          currentQueueIndex: nextIndex,
          currentTrack,
          currentTime: 0,
          duration: currentTrack?.duration ?? 0,
          isPlaying: true,
          isLoading: false,
          playbackError: null,
        });
      },

      previous: () => {
        const state = get();
        if (state.currentTime > PREVIOUS_RESTART_THRESHOLD_SECONDS) {
          set({ currentTime: 0 });
          return;
        }

        const previousIndex =
          state.currentQueueIndex > 0
            ? state.currentQueueIndex - 1
            : state.repeatMode === "all" && state.queue.length > 0
              ? state.queue.length - 1
              : state.currentQueueIndex;
        const currentTrack = getTrackAtIndex(state.queue, previousIndex);

        set({
          currentQueueIndex: previousIndex,
          currentTrack,
          currentTime: 0,
          duration: currentTrack?.duration ?? 0,
          isPlaying: currentTrack ? state.isPlaying : false,
          playbackError: null,
        });
      },

      seek: (time) =>
        set((state) => ({
          currentTime: clamp(time, 0, state.duration || 0),
        })),
      setCurrentTime: (time) =>
        set((state) => ({
          currentTime: clamp(time, 0, Math.max(state.duration, time, 0)),
        })),
      setDuration: (duration) => {
        const normalizedDuration = Number.isFinite(duration)
          ? Math.max(0, duration)
          : 0;
        set((state) => ({
          duration: normalizedDuration,
          currentTime: clamp(state.currentTime, 0, normalizedDuration),
        }));
      },
      setVolume: (volume) => {
        const normalizedVolume = clamp(volume, 0, 1);
        set({
          volume: normalizedVolume,
          isMuted: normalizedVolume <= 0,
        });
      },
      setMuted: (isMuted) => set({ isMuted }),
      toggleMuted: () => set((state) => ({ isMuted: !state.isMuted })),
      setPlaybackSpeed: (speed) =>
        set({ playbackSpeed: clamp(speed, 0.5, 3) }),
      toggleShuffle: () =>
        set((state) => ({ isShuffleEnabled: !state.isShuffleEnabled })),
      setRepeatMode: (repeatMode) => set({ repeatMode }),

      addToQueue: (track) =>
        set((state) => ({ queue: [...state.queue, createQueueItem(track)] })),
      playNext: (track) =>
        set((state) => {
          const insertionIndex = Math.max(state.currentQueueIndex + 1, 0);
          const queue = [...state.queue];
          queue.splice(insertionIndex, 0, createQueueItem(track));
          return { queue };
        }),
      playQueueItem: (queueItemId) => {
        const state = get();
        const currentQueueIndex = state.queue.findIndex(
          (item) => item.id === queueItemId,
        );
        const currentTrack = getTrackAtIndex(
          state.queue,
          currentQueueIndex,
        );
        if (!currentTrack) return;

        set({
          currentQueueIndex,
          currentTrack,
          currentTime: 0,
          duration: currentTrack.duration,
          isPlaying: true,
          isLoading: false,
          playbackError: null,
        });
      },
      moveQueueItem: (queueItemId, targetIndex) =>
        set((state) => {
          const sourceIndex = state.queue.findIndex(
            (item) => item.id === queueItemId,
          );
          if (sourceIndex < 0 || state.queue.length < 2) return state;

          const normalizedTargetIndex = clampQueueIndex(
            targetIndex,
            state.queue.length,
          );
          if (sourceIndex === normalizedTargetIndex) return state;

          const queue = [...state.queue];
          const [movedItem] = queue.splice(sourceIndex, 1);
          queue.splice(normalizedTargetIndex, 0, movedItem);
          const currentQueueIndex = state.currentTrack
            ? queue.findIndex(
                (item) =>
                  item.id === state.queue[state.currentQueueIndex]?.id,
              )
            : -1;

          return { queue, currentQueueIndex };
        }),
      removeFromQueue: (queueItemId) =>
        set((state) => {
          const removedIndex = state.queue.findIndex(
            (item) => item.id === queueItemId,
          );
          if (removedIndex < 0) return state;

          const queue = state.queue.filter((item) => item.id !== queueItemId);
          if (removedIndex > state.currentQueueIndex) {
            return { queue };
          }

          const currentQueueIndex =
            removedIndex < state.currentQueueIndex
              ? state.currentQueueIndex - 1
              : clampQueueIndex(state.currentQueueIndex, queue.length);
          const currentTrack = getTrackAtIndex(queue, currentQueueIndex);

          return {
            queue,
            currentQueueIndex,
            currentTrack,
            currentTime: removedIndex === state.currentQueueIndex ? 0 : state.currentTime,
            duration:
              removedIndex === state.currentQueueIndex
                ? currentTrack?.duration ?? 0
                : state.duration,
            isPlaying: currentTrack ? state.isPlaying : false,
          };
        }),
      clearQueue: () =>
        set({
          queue: [],
          currentQueueIndex: -1,
          currentTrack: null,
          currentTime: 0,
          duration: 0,
          isPlaying: false,
          isLoading: false,
          playbackError: null,
        }),
      replaceQueue: (tracks, startIndex = 0) => {
        const queue = tracks.map(createQueueItem);
        const currentQueueIndex = clampQueueIndex(startIndex, queue.length);
        const currentTrack = getTrackAtIndex(queue, currentQueueIndex);

        set({
          queue,
          currentQueueIndex,
          currentTrack,
          currentTime: 0,
          duration: currentTrack?.duration ?? 0,
          isPlaying: Boolean(currentTrack),
          isLoading: false,
          playbackError: null,
        });
      },

      setLoading: (isLoading) => set({ isLoading }),
      setPlaybackError: (playbackError) =>
        set({
          playbackError,
          isLoading: false,
          ...(playbackError ? { isPlaying: false } : {}),
        }),
    }),
    {
      name: "sunnekatha-player",
      version: 1,
      partialize: (state): PersistedPlayerState => ({
        queue: state.queue,
        currentQueueIndex: state.currentQueueIndex,
        volume: state.volume,
        playbackSpeed: state.playbackSpeed,
        repeatMode: state.repeatMode,
      }),
      merge: (persistedState, currentState) => {
        const persisted = persistedState as Partial<PersistedPlayerState>;
        const queue = Array.isArray(persisted.queue) ? persisted.queue : [];
        const currentQueueIndex = clampQueueIndex(
          persisted.currentQueueIndex ?? -1,
          queue.length,
        );
        const currentTrack = getTrackAtIndex(queue, currentQueueIndex);

        return {
          ...currentState,
          queue,
          currentQueueIndex,
          currentTrack,
          duration: currentTrack?.duration ?? 0,
          volume: clamp(persisted.volume ?? DEFAULT_VOLUME, 0, 1),
          playbackSpeed: clamp(
            persisted.playbackSpeed ?? DEFAULT_PLAYBACK_SPEED,
            0.5,
            3,
          ),
          repeatMode:
            persisted.repeatMode === "one" || persisted.repeatMode === "all"
              ? persisted.repeatMode
              : "off",
        };
      },
    },
  ),
);
