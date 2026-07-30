"use client";

import { useCallback, useEffect, useLayoutEffect, useRef } from "react";

import { usePlayerStore } from "@/features/player/player-store";
import { usePreferencesStore } from "@/features/profile/preferences-store";
import {
  getResumePosition,
  PROGRESS_UPDATE_INTERVAL_SECONDS,
  recordRecentlyPlayed,
  saveListeningProgress,
} from "@/services/progress-service";
import { mapPlayableTrack } from "@/services/api-mappers";
import { getTrackStream } from "@/services/media-service";
import type { Track } from "@/types";

let audioInstance: HTMLAudioElement | null = null;

function getAudioInstance() {
  if (!audioInstance) {
    audioInstance = new Audio();
    audioInstance.preload = "metadata";
    audioInstance.hidden = true;
    audioInstance.setAttribute("data-sunnekatha-audio-engine", "true");
    document.body.appendChild(audioInstance);
  }

  return audioInstance;
}

export function playAudioFromUserGesture() {
  return getAudioInstance().play();
}

export function pauseAudioImmediately() {
  getAudioInstance().pause();
}

function getAudioError(audio: HTMLAudioElement) {
  switch (audio.error?.code) {
    case MediaError.MEDIA_ERR_ABORTED:
      return {
        code: "playback-aborted",
        message: "अडियो प्लेब्याक रोकियो। कृपया फेरि प्रयास गर्नुहोस्।",
      };
    case MediaError.MEDIA_ERR_NETWORK:
      return {
        code: "network-error",
        message: "अडियो लोड गर्न नेटवर्क समस्या भयो।",
      };
    case MediaError.MEDIA_ERR_DECODE:
      return {
        code: "decode-error",
        message: "यो अडियो फाइल चलाउन सकिएन।",
      };
    case MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED:
      return {
        code: "unsupported-audio",
        message: "यो अडियो स्रोत ब्राउजरले समर्थन गर्दैन।",
      };
    default:
      return {
        code: "unknown-audio-error",
        message: "अडियो चलाउँदा समस्या भयो।",
      };
  }
}

function isExpectedPlayInterruption(error: unknown) {
  return error instanceof DOMException && error.name === "AbortError";
}

export function AudioEngine() {
  const currentTrack = usePlayerStore((state) => state.currentTrack);
  const isPlaying = usePlayerStore((state) => state.isPlaying);
  const currentTime = usePlayerStore((state) => state.currentTime);
  const volume = usePlayerStore((state) => state.volume);
  const isMuted = usePlayerStore((state) => state.isMuted);
  const playbackSpeed = usePlayerStore((state) => state.playbackSpeed);
  const next = usePlayerStore((state) => state.next);
  const previous = usePlayerStore((state) => state.previous);
  const play = usePlayerStore((state) => state.play);
  const pause = usePlayerStore((state) => state.pause);
  const seek = usePlayerStore((state) => state.seek);
  const setCurrentTime = usePlayerStore((state) => state.setCurrentTime);
  const setDuration = usePlayerStore((state) => state.setDuration);
  const setLoading = usePlayerStore((state) => state.setLoading);
  const setPlaybackError = usePlayerStore(
    (state) => state.setPlaybackError,
  );
  const updateTrackSource = usePlayerStore((state) => state.updateTrackSource);
  const activeTrack = useRef<Track | null>(null);
  const pendingResumeTime = useRef(0);
  const wasPlaying = useRef(false);
  const lastRecordedProgress = useRef<{
    trackId: string;
    second: number;
  } | null>(null);
  const refreshedTrackId = useRef<string | null>(null);
  const flushProgress = useCallback(
    (
      track = activeTrack.current,
      position = getAudioInstance().currentTime,
      duration = getAudioInstance().duration,
    ) => {
      if (!track) return;

      const safeDuration = Number.isFinite(duration)
        ? duration
        : track.duration;
      const saved = saveListeningProgress({
        trackId: track.id,
        progressSeconds: position,
        durationSeconds: safeDuration,
      });

      if (saved) {
        lastRecordedProgress.current = {
          trackId: track.id,
          second: Math.floor(saved.progressSeconds),
        };
      }
    },
    [],
  );

  useEffect(() => {
    const audio = getAudioInstance();

    const handleLoadStart = () => setLoading(true);
    const handleWaiting = () => setLoading(true);
    const handleReady = () => {
      setLoading(false);
      setPlaybackError(null);
    };
    const handleDurationChange = () => {
      if (Number.isFinite(audio.duration)) {
        setDuration(audio.duration);
      }
    };
    const handleLoadedMetadata = () => {
      const resumeTime = pendingResumeTime.current;
      if (resumeTime <= 0 || !Number.isFinite(audio.duration)) return;

      const safeResumeTime = Math.min(
        resumeTime,
        Math.max(0, audio.duration - 0.25),
      );
      audio.currentTime = safeResumeTime;
      setCurrentTime(safeResumeTime);
      pendingResumeTime.current = 0;
    };
    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime);

      const track = activeTrack.current;
      if (!track) return;

      const second = Math.floor(audio.currentTime);
      const lastRecorded = lastRecordedProgress.current;
      if (
        second < 1 ||
        (lastRecorded?.trackId === track.id &&
          Math.abs(second - lastRecorded.second) <
            PROGRESS_UPDATE_INTERVAL_SECONDS)
      ) {
        return;
      }

      flushProgress(track, audio.currentTime, audio.duration);
    };
    const handleEnded = () => {
      const state = usePlayerStore.getState();
      const track = activeTrack.current;

      if (track) {
        flushProgress(track, track.duration, track.duration);
      }

      if (state.repeatMode === "one") {
        audio.currentTime = 0;
        state.setCurrentTime(0);
        void audio.play().catch((error: unknown) => {
          if (!isExpectedPlayInterruption(error)) {
            state.setPlaybackError({
              code: "playback-failed",
              message: "अडियो फेरि चलाउन सकिएन।",
            });
          }
        });
        return;
      }

      if (usePreferencesStore.getState().autoplay) {
        state.next();
      } else {
        state.pause();
        state.setCurrentTime(track?.duration ?? state.duration);
      }
    };
    const handleError = async () => {
      const state = usePlayerStore.getState();
      const track = state.currentTrack;
      if (track && refreshedTrackId.current !== track.id) {
        refreshedTrackId.current = track.id;
        const resumeAt = audio.currentTime || state.currentTime;
        try {
          const refreshed = mapPlayableTrack(await getTrackStream(track.slug));
          updateTrackSource(refreshed);
          audio.src = refreshed.audioUrl;
          audio.load();
          const restorePosition = () => {
            audio.currentTime = Math.min(
              Math.max(0, resumeAt),
              Number.isFinite(audio.duration) ? audio.duration : resumeAt,
            );
            audio.removeEventListener("loadedmetadata", restorePosition);
          };
          audio.addEventListener("loadedmetadata", restorePosition);
          if (state.isPlaying) {
            await audio.play();
          }
          return;
        } catch {
          // Fall through to the stable player error below.
        }
      }
      setPlaybackError(getAudioError(audio));
    };

    audio.addEventListener("loadstart", handleLoadStart);
    audio.addEventListener("waiting", handleWaiting);
    audio.addEventListener("canplay", handleReady);
    audio.addEventListener("playing", handleReady);
    audio.addEventListener("durationchange", handleDurationChange);
    audio.addEventListener("loadedmetadata", handleLoadedMetadata);
    audio.addEventListener("timeupdate", handleTimeUpdate);
    audio.addEventListener("ended", handleEnded);
    audio.addEventListener("error", handleError);

    return () => {
      audio.removeEventListener("loadstart", handleLoadStart);
      audio.removeEventListener("waiting", handleWaiting);
      audio.removeEventListener("canplay", handleReady);
      audio.removeEventListener("playing", handleReady);
      audio.removeEventListener("durationchange", handleDurationChange);
      audio.removeEventListener("loadedmetadata", handleLoadedMetadata);
      audio.removeEventListener("timeupdate", handleTimeUpdate);
      audio.removeEventListener("ended", handleEnded);
      audio.removeEventListener("error", handleError);
    };
  }, [
    flushProgress,
    setCurrentTime,
    setDuration,
    setLoading,
    setPlaybackError,
    updateTrackSource,
  ]);

  useEffect(
    () =>
      usePlayerStore.subscribe((state, previousState) => {
        const audio = getAudioInstance();
        const trackChanged =
          state.currentTrack?.id !== previousState.currentTrack?.id;

        if (trackChanged && state.currentTrack) {
          refreshedTrackId.current = null;
          const previousTrack = activeTrack.current;

          if (previousTrack) {
            flushProgress(previousTrack, audio.currentTime, audio.duration);
          }

          activeTrack.current = state.currentTrack;
          recordRecentlyPlayed(state.currentTrack.id);
          const resumeTime = getResumePosition(state.currentTrack.id);
          pendingResumeTime.current = resumeTime;
          lastRecordedProgress.current =
            resumeTime > 0
              ? {
                  trackId: state.currentTrack.id,
                  second: Math.floor(resumeTime),
                }
              : null;
          setLoading(true);
          setPlaybackError(null);
          audio.src = state.currentTrack.audioUrl;
          audio.load();
          setCurrentTime(resumeTime);
        }

        if (
          state.currentTrack &&
          state.isPlaying &&
          (!previousState.isPlaying || trackChanged)
        ) {
          void audio.play().catch((error: unknown) => {
            if (isExpectedPlayInterruption(error)) return;

            setPlaybackError({
              code:
                error instanceof DOMException && error.name === "NotAllowedError"
                  ? "autoplay-blocked"
                  : "playback-failed",
              message:
                error instanceof DOMException && error.name === "NotAllowedError"
                  ? "अडियो चलाउन प्ले बटन थिच्नुहोस्।"
                  : "अडियो चलाउन सकिएन। कृपया फेरि प्रयास गर्नुहोस्।",
            });
          });
        } else if (!state.isPlaying && previousState.isPlaying) {
          audio.pause();
        }
      }),
    [
      flushProgress,
      setCurrentTime,
      setLoading,
      setPlaybackError,
    ],
  );

  useLayoutEffect(() => {
    const audio = getAudioInstance();
    const previousTrack = activeTrack.current;

    if (!currentTrack) {
      if (previousTrack) {
        flushProgress(previousTrack, audio.currentTime, audio.duration);
      }
      audio.pause();
      audio.removeAttribute("src");
      audio.load();
      activeTrack.current = null;
      pendingResumeTime.current = 0;
      return;
    }

    if (previousTrack?.id === currentTrack.id) return;

    if (previousTrack) {
      flushProgress(previousTrack, audio.currentTime, audio.duration);
    }

    activeTrack.current = currentTrack;
    recordRecentlyPlayed(currentTrack.id);
    const resumeTime = getResumePosition(currentTrack.id);
    pendingResumeTime.current = resumeTime;
    lastRecordedProgress.current =
      resumeTime > 0
        ? { trackId: currentTrack.id, second: Math.floor(resumeTime) }
        : null;
    setLoading(true);
    setPlaybackError(null);
    audio.src = currentTrack.audioUrl;
    audio.load();
    setCurrentTime(resumeTime);
  }, [
    currentTrack,
    flushProgress,
    setCurrentTime,
    setLoading,
    setPlaybackError,
  ]);

  useLayoutEffect(() => {
    const audio = getAudioInstance();

    if (!currentTrack || !isPlaying) {
      audio.pause();
      return;
    }

    void audio.play().catch((error: unknown) => {
      if (isExpectedPlayInterruption(error)) return;

      setPlaybackError({
        code:
          error instanceof DOMException && error.name === "NotAllowedError"
            ? "autoplay-blocked"
            : "playback-failed",
        message:
          error instanceof DOMException && error.name === "NotAllowedError"
            ? "अडियो चलाउन प्ले बटन थिच्नुहोस्।"
            : "अडियो चलाउन सकिएन। कृपया फेरि प्रयास गर्नुहोस्।",
      });
    });
  }, [currentTrack, isPlaying, setPlaybackError]);

  useEffect(() => {
    if (wasPlaying.current && !isPlaying) {
      flushProgress();
    }
    wasPlaying.current = isPlaying;
  }, [flushProgress, isPlaying]);

  useEffect(() => {
    const handlePageExit = () => flushProgress();

    window.addEventListener("pagehide", handlePageExit);
    window.addEventListener("beforeunload", handlePageExit);

    return () => {
      window.removeEventListener("pagehide", handlePageExit);
      window.removeEventListener("beforeunload", handlePageExit);
      flushProgress();
    };
  }, [flushProgress]);

  useEffect(() => {
    const audio = getAudioInstance();
    if (
      currentTrack &&
      Number.isFinite(currentTime) &&
      Math.abs(audio.currentTime - currentTime) > 0.1
    ) {
      if (audio.readyState >= HTMLMediaElement.HAVE_METADATA) {
        audio.currentTime = currentTime;
      } else {
        pendingResumeTime.current = currentTime;
      }
    }
  }, [currentTime, currentTrack]);

  useEffect(() => {
    const audio = getAudioInstance();
    audio.volume = volume;
    audio.muted = isMuted;
  }, [isMuted, volume]);

  useEffect(() => {
    getAudioInstance().playbackRate = playbackSpeed;
  }, [playbackSpeed]);

  useEffect(() => {
    if (!("mediaSession" in navigator)) return;

    if (currentTrack) {
      navigator.mediaSession.metadata = new MediaMetadata({
        title: currentTrack.title,
        artist: `${currentTrack.author.name} · ${currentTrack.narrator.name}`,
        album: "SunneKatha",
        artwork: [
          {
            src: currentTrack.coverImage,
            sizes: "512x512",
          },
        ],
      });
    } else {
      navigator.mediaSession.metadata = null;
    }

    const seekBy = (seconds: number) => {
      const state = usePlayerStore.getState();
      state.seek(state.currentTime + seconds);
    };

    const handlers: Partial<
      Record<MediaSessionAction, MediaSessionActionHandler>
    > = {
      play: () => play(),
      pause,
      nexttrack: next,
      previoustrack: previous,
      seekbackward: (details) => seekBy(-(details.seekOffset ?? 10)),
      seekforward: (details) => seekBy(details.seekOffset ?? 10),
      seekto: (details) => {
        if (details.seekTime !== undefined) {
          seek(details.seekTime);
        }
      },
    };

    for (const [action, handler] of Object.entries(handlers)) {
      try {
        navigator.mediaSession.setActionHandler(
          action as MediaSessionAction,
          handler,
        );
      } catch {
        // Some browsers expose Media Session but support only a subset of actions.
      }
    }

    return () => {
      for (const action of Object.keys(handlers)) {
        try {
          navigator.mediaSession.setActionHandler(
            action as MediaSessionAction,
            null,
          );
        } catch {
          // Unsupported actions need no cleanup.
        }
      }
    };
  }, [currentTrack, next, pause, play, previous, seek]);

  return null;
}
