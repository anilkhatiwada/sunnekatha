"use client";

import { useEffect, useRef } from "react";

import { usePlayerStore } from "@/features/player/player-store";
import {
  endPlaybackSession,
  getServerListeningProgress,
  startPlaybackSession,
  updatePlaybackSession,
} from "@/services";

const SESSION_UPDATE_INTERVAL_MS = 20_000;

interface ActiveSession {
  id: string;
  trackId: string;
  listenedSeconds: number;
  activeSince: number | null;
}

function accrueListening(session: ActiveSession) {
  if (session.activeSince === null) return session.listenedSeconds;
  const now = Date.now();
  session.listenedSeconds += Math.max(0, (now - session.activeSince) / 1000);
  session.activeSince = now;
  return session.listenedSeconds;
}

export function PlaybackSyncController() {
  const sessionRef = useRef<ActiveSession | null>(null);

  useEffect(() => {
    const endCurrentSession = async (snapshot?: {
      currentTime: number;
      duration: number;
    }) => {
      const session = sessionRef.current;
      if (!session) return;
      sessionRef.current = null;
      const state = usePlayerStore.getState();
      const currentTime = snapshot?.currentTime ?? state.currentTime;
      const duration = snapshot?.duration ?? state.duration;
      const listenedSeconds = accrueListening(session);
      await endPlaybackSession(session.id, {
        listenedSeconds,
        completed: duration > 0 && currentTime / duration >= 0.9,
        positionSeconds: currentTime,
      }).catch(() => null);
    };

    const unsubscribe = usePlayerStore.subscribe((state, previous) => {
      const trackChanged =
        state.currentTrack?.id !== previous.currentTrack?.id;

      if (trackChanged) {
        void endCurrentSession({
          currentTime: previous.currentTime,
          duration: previous.duration,
        });
        const track = state.currentTrack;
        if (!track) return;

        void getServerListeningProgress(track.id).then((progress) => {
          if (
            progress &&
            !progress.isCompleted &&
            usePlayerStore.getState().currentTrack?.id === track.id &&
            usePlayerStore.getState().currentTime < 1
          ) {
            usePlayerStore.getState().seek(progress.progressSeconds);
          }
        });
        void startPlaybackSession(track.id, state.currentTime)
          .then((session) => {
            if (!session) {
              return;
            }
            if (usePlayerStore.getState().currentTrack?.id !== track.id) {
              void endPlaybackSession(session.id, {
                listenedSeconds: session.listenedSeconds,
                completed: false,
                positionSeconds: state.currentTime,
              }).catch(() => null);
              return;
            }
            sessionRef.current = {
              id: session.id,
              trackId: track.id,
              listenedSeconds: session.listenedSeconds,
              activeSince: state.isPlaying ? Date.now() : null,
            };
          })
          .catch(() => null);
        return;
      }

      const session = sessionRef.current;
      if (!session || !state.currentTrack) return;
      if (state.isPlaying === previous.isPlaying) return;

      if (state.isPlaying) {
        session.activeSince = Date.now();
        void updatePlaybackSession(session.id, {
          listenedSeconds: session.listenedSeconds,
          eventType: "resumed",
          positionSeconds: state.currentTime,
        }).catch(() => null);
      } else {
        const listenedSeconds = accrueListening(session);
        session.activeSince = null;
        void updatePlaybackSession(session.id, {
          listenedSeconds,
          eventType: "paused",
          positionSeconds: state.currentTime,
        }).catch(() => null);
      }
    });

    const updateTimer = window.setInterval(() => {
      const session = sessionRef.current;
      const state = usePlayerStore.getState();
      if (!session || !state.isPlaying) return;
      const listenedSeconds = accrueListening(session);
      void updatePlaybackSession(session.id, {
        listenedSeconds,
        positionSeconds: state.currentTime,
      }).catch(() => null);
    }, SESSION_UPDATE_INTERVAL_MS);

    return () => {
      unsubscribe();
      window.clearInterval(updateTimer);
      void endCurrentSession();
    };
  }, []);

  return null;
}
