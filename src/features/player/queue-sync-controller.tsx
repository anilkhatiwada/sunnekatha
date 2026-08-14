"use client";

import { useEffect, useRef } from "react";

import { useAuth } from "@/features/auth/auth-provider";
import { usePlayerStore } from "@/features/player/player-store";
import {
  clearSynchronizedQueue,
  getCurrentQueue,
  getTrackStream,
  mapPlayableTrack,
  replaceSynchronizedQueue,
  updateSynchronizedQueuePosition,
  updateSynchronizedQueueRepeat,
  updateSynchronizedQueueShuffle,
} from "@/services";

const POSITION_SYNC_INTERVAL_MS = 30_000;
const QUEUE_SYNC_DEBOUNCE_MS = 900;

export function QueueSyncController() {
  const { user } = useAuth();
  const isRestoring = useRef(false);
  const isReady = useRef(false);

  useEffect(() => {
    if (!user) {
      isReady.current = false;
      return;
    }

    let isCancelled = false;
    const localState = usePlayerStore.getState();

    const restore = async () => {
      if (localState.queue.length > 0) {
        isReady.current = true;
        void replaceSynchronizedQueue({
          trackIds: localState.queue.map((item) => item.track.id),
          currentIndex: localState.currentQueueIndex,
          positionSeconds: localState.currentTime,
        }).catch(() => undefined);
        return;
      }

      isRestoring.current = true;
      try {
        const serverQueue = await getCurrentQueue();
        if (isCancelled || serverQueue.items.length === 0) return;
        const playableTracks = await Promise.all(
          serverQueue.items.map(async ({ track }) =>
            mapPlayableTrack(await getTrackStream(track.slug, "auto", true)),
          ),
        );
        if (isCancelled) return;
        usePlayerStore
          .getState()
          .replaceQueue(playableTracks, serverQueue.currentIndex, "queue");
        usePlayerStore.getState().pause();
        usePlayerStore
          .getState()
          .seek(Math.max(0, serverQueue.positionSeconds));
        if (
          usePlayerStore.getState().isShuffleEnabled !==
          serverQueue.isShuffleEnabled
        ) {
          usePlayerStore.getState().toggleShuffle();
        }
        usePlayerStore.getState().setRepeatMode(serverQueue.repeatMode);
      } catch {
        // Local playback remains available when restoration is unavailable.
      } finally {
        isRestoring.current = false;
        isReady.current = true;
      }
    };

    void restore();
    return () => {
      isCancelled = true;
    };
  }, [user]);

  useEffect(() => {
    if (!user) return;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let previousQueueSignature = queueSignature(usePlayerStore.getState());
    let previousQueueIndex = usePlayerStore.getState().currentQueueIndex;
    let previousShuffle = usePlayerStore.getState().isShuffleEnabled;
    let previousRepeat = usePlayerStore.getState().repeatMode;

    const unsubscribe = usePlayerStore.subscribe((state) => {
      if (!isReady.current || isRestoring.current) return;
      const nextSignature = queueSignature(state);
      if (nextSignature !== previousQueueSignature) {
        previousQueueSignature = nextSignature;
        clearTimeout(timer);
        timer = setTimeout(() => {
          if (state.queue.length === 0) {
            void clearSynchronizedQueue().catch(() => undefined);
          } else {
            void replaceSynchronizedQueue({
              trackIds: state.queue.map((item) => item.track.id),
              currentIndex: state.currentQueueIndex,
              positionSeconds: state.currentTime,
            }).catch(() => undefined);
          }
        }, QUEUE_SYNC_DEBOUNCE_MS);
      }
      if (
        state.currentQueueIndex !== previousQueueIndex &&
        state.queue.length > 0
      ) {
        previousQueueIndex = state.currentQueueIndex;
        void updateSynchronizedQueuePosition({
          currentIndex: state.currentQueueIndex,
          positionSeconds: state.currentTime,
        }).catch(() => undefined);
      }
      if (state.isShuffleEnabled !== previousShuffle) {
        previousShuffle = state.isShuffleEnabled;
        void updateSynchronizedQueueShuffle(state.isShuffleEnabled).catch(
          () => undefined,
        );
      }
      if (state.repeatMode !== previousRepeat) {
        previousRepeat = state.repeatMode;
        void updateSynchronizedQueueRepeat(state.repeatMode).catch(
          () => undefined,
        );
      }
    });

    const positionTimer = setInterval(() => {
      const state = usePlayerStore.getState();
      if (!isReady.current || state.queue.length === 0) return;
      void updateSynchronizedQueuePosition({
        currentIndex: state.currentQueueIndex,
        positionSeconds: state.currentTime,
      }).catch(() => undefined);
    }, POSITION_SYNC_INTERVAL_MS);

    return () => {
      unsubscribe();
      clearTimeout(timer);
      clearInterval(positionTimer);
    };
  }, [user]);

  return null;
}

function queueSignature(state: ReturnType<typeof usePlayerStore.getState>) {
  return state.queue.map((item) => item.id).join(",");
}
