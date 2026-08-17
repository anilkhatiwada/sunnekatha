"use client";

import { useCallback, useEffect, useLayoutEffect, useRef } from "react";

import { usePlayerStore } from "@/features/player/player-store";
import { usePreferencesStore } from "@/features/profile/preferences-store";
import { getSimilarTracks } from "@/services/track-service";
import {
  PROGRESS_UPDATE_INTERVAL_SECONDS,
  recordRecentlyPlayed,
  saveListeningProgress,
} from "@/services/progress-service";
import { mapPlayableTrack } from "@/services/api-mappers";
import { getTrackStream } from "@/services/media-service";
import {
  getAudioAdvertisementSessionId,
  getNextAudioAdvertisement,
  recordAudioAdvertisementStarted,
} from "@/services/audio-ad-service";
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
        message: "Audio playback stopped. Please try again.",
      };
    case MediaError.MEDIA_ERR_NETWORK:
      return {
        code: "network-error",
        message: "A network error interrupted audio loading.",
      };
    case MediaError.MEDIA_ERR_DECODE:
      return {
        code: "decode-error",
        message: "This audio file could not be played.",
      };
    case MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED:
      return {
        code: "unsupported-audio",
        message: "This browser does not support the audio source.",
      };
    default:
      return {
        code: "unknown-audio-error",
        message: "Audio playback encountered a problem.",
      };
  }
}

function isExpectedPlayInterruption(error: unknown) {
  return error instanceof DOMException && error.name === "AbortError";
}

export function AudioEngine() {
  const currentTrack = usePlayerStore((state) => state.currentTrack);
  const playbackPhase = usePlayerStore((state) => state.playbackPhase);
  const playbackStartPosition = usePlayerStore(
    (state) => state.playbackStartPosition,
  );
  const currentAdvertisement = usePlayerStore(
    (state) => state.currentAdvertisement,
  );
  const playbackSource = usePlayerStore((state) => state.playbackSource);
  const playbackSequence = usePlayerStore((state) => state.playbackSequence);
  const isPlaying = usePlayerStore((state) => state.isPlaying);
  const currentTime = usePlayerStore((state) => state.currentTime);
  const volume = usePlayerStore((state) => state.volume);
  const isMuted = usePlayerStore((state) => state.isMuted);
  const playbackSpeed = usePlayerStore((state) => state.playbackSpeed);
  const sleepTimerMinutes = usePlayerStore(
    (state) => state.sleepTimerMinutes,
  );
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
  const setSleepTimer = usePlayerStore((state) => state.setSleepTimer);
  const activeTrack = useRef<Track | null>(null);
  const pendingResumeTime = useRef(0);
  const wasPlaying = useRef(false);
  const lastRecordedProgress = useRef<{
    trackId: string;
    second: number;
  } | null>(null);
  const refreshedTrackId = useRef<string | null>(null);
  const preparationKey = useRef<string | null>(null);
  const recordedAdvertisementKey = useRef<string | null>(null);
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
    if (!currentTrack || playbackPhase !== "preparing") return;

    const nextSequence = playbackSequence + 1;
    const key = `${currentTrack.id}:${nextSequence}`;
    if (preparationKey.current === key) return;
    preparationKey.current = key;
    let isCancelled = false;

    const request = {
      sessionId: getAudioAdvertisementSessionId(),
      playbackSequence: nextSequence,
      trackId: currentTrack.id,
      source: playbackSource,
    };
    void getNextAudioAdvertisement(request)
      .then((response) => {
        if (isCancelled) return;
        const state = usePlayerStore.getState();
        if (
          state.currentTrack?.id === currentTrack.id &&
          state.playbackPhase === "preparing"
        ) {
          state.preparePlayback(response.advertisement, nextSequence);
        }
      })
      .catch(() => {
        if (isCancelled) return;
        const state = usePlayerStore.getState();
        if (
          state.currentTrack?.id === currentTrack.id &&
          state.playbackPhase === "preparing"
        ) {
          // Ad delivery must never prevent the requested literature from playing.
          state.preparePlayback(null, nextSequence);
        }
      });

    return () => {
      isCancelled = true;
    };
  }, [currentTrack, playbackPhase, playbackSequence, playbackSource]);

  useEffect(() => {
    const audio = getAudioInstance();

    const handleLoadStart = () => setLoading(true);
    const handleWaiting = () => setLoading(true);
    const handleReady = () => {
      setLoading(false);
      setPlaybackError(null);
    };
    const handlePlaying = () => {
      handleReady();
      const state = usePlayerStore.getState();
      const advertisement = state.currentAdvertisement;
      const track = state.currentTrack;
      if (
        state.playbackPhase !== "advertisement" ||
        !advertisement ||
        !track
      ) {
        return;
      }

      const key = `${advertisement.id}:${state.playbackSequence}`;
      if (recordedAdvertisementKey.current === key) return;
      recordedAdvertisementKey.current = key;
      void recordAudioAdvertisementStarted(advertisement.id, {
        sessionId: getAudioAdvertisementSessionId(),
        playbackSequence: state.playbackSequence,
        trackId: track.id,
        source: state.playbackSource,
      }).catch(() => {
        // Playback remains uninterrupted if analytics delivery is unavailable.
      });
    };
    const handleDurationChange = () => {
      if (
        usePlayerStore.getState().playbackPhase !== "preparing" &&
        Number.isFinite(audio.duration)
      ) {
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
      if (usePlayerStore.getState().playbackPhase !== "content") {
        setCurrentTime(audio.currentTime);
        return;
      }
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
    const handleEnded = async () => {
      const state = usePlayerStore.getState();
      if (state.playbackPhase === "advertisement") {
        state.finishAdvertisement();
        return;
      }
      if (state.playbackPhase === "introduction") {
        state.finishIntroduction();
        return;
      }
      const track = activeTrack.current;

      if (track) {
        flushProgress(track, track.duration, track.duration);
      }

      if (state.repeatMode === "one") {
        if (track) state.play(track, "queue");
        return;
      }

      if (usePreferencesStore.getState().autoplay) {
        const hasQueuedSuccessor = state.isShuffleEnabled
          ? state.queue.length > 1
          : state.currentQueueIndex < state.queue.length - 1 ||
            (state.repeatMode === "all" && state.queue.length > 0);

        if (hasQueuedSuccessor) {
          state.next();
          return;
        }

        state.setLoading(true);
        try {
          const queuedTrackIds = new Set(
            state.queue.map((item) => item.track.id),
          );
          const relatedTracks = await getSimilarTracks(track?.slug ?? "", 6);
          const recommendation = relatedTracks.find(
            (candidate) => !queuedTrackIds.has(candidate.id),
          );
          if (!recommendation) throw new Error("No recommendation available.");

          const stream = await getTrackStream(recommendation.slug, "auto", true);
          const latestState = usePlayerStore.getState();
          if (
            latestState.currentTrack?.id !== track?.id ||
            !latestState.isPlaying
          ) {
            latestState.setLoading(false);
            return;
          }
          latestState.play(mapPlayableTrack(stream), "autoplay");
        } catch {
          const latestState = usePlayerStore.getState();
          if (latestState.currentTrack?.id === track?.id) {
            latestState.pause();
            latestState.setCurrentTime(track?.duration ?? latestState.duration);
          }
          latestState.setLoading(false);
        }
      } else {
        state.pause();
        state.setCurrentTime(track?.duration ?? state.duration);
      }
    };
    const handleError = async () => {
      const state = usePlayerStore.getState();
      if (state.playbackPhase === "advertisement") {
        state.finishAdvertisement();
        return;
      }
      if (state.playbackPhase === "introduction") {
        state.finishIntroduction();
        return;
      }
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
    audio.addEventListener("playing", handlePlaying);
    audio.addEventListener("durationchange", handleDurationChange);
    audio.addEventListener("loadedmetadata", handleLoadedMetadata);
    audio.addEventListener("timeupdate", handleTimeUpdate);
    audio.addEventListener("ended", handleEnded);
    audio.addEventListener("error", handleError);

    return () => {
      audio.removeEventListener("loadstart", handleLoadStart);
      audio.removeEventListener("waiting", handleWaiting);
      audio.removeEventListener("canplay", handleReady);
      audio.removeEventListener("playing", handlePlaying);
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
        const phaseChanged = state.playbackPhase !== previousState.playbackPhase;

        if ((trackChanged || phaseChanged) && state.currentTrack) {
          refreshedTrackId.current = null;
          const previousTrack = activeTrack.current;

          if (previousTrack && previousState.playbackPhase === "content") {
            flushProgress(previousTrack, audio.currentTime, audio.duration);
          }

          if (state.playbackPhase === "preparing") {
            audio.pause();
            audio.removeAttribute("src");
            activeTrack.current = null;
            setLoading(true);
            return;
          }

          const isAdvertisement = state.playbackPhase === "advertisement";
          const isIntroduction = state.playbackPhase === "introduction";
          const isContent = state.playbackPhase === "content";
          activeTrack.current = isContent ? state.currentTrack : null;
          if (isContent) recordRecentlyPlayed(state.currentTrack.id);
          const resumeTime = isContent ? state.playbackStartPosition : 0;
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
          audio.src = isAdvertisement
            ? state.currentAdvertisement?.url ?? state.currentTrack.audioUrl
            : isIntroduction
              ? state.currentTrack.introduction?.url ?? state.currentTrack.audioUrl
              : state.currentTrack.audioUrl;
          audio.load();
          setCurrentTime(resumeTime);
        }

        if (
          state.currentTrack &&
          state.isPlaying &&
          (!previousState.isPlaying || trackChanged || phaseChanged)
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
                  ? "Press Play to start the audio."
                  : "Audio could not be played. Please try again.",
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

    if (playbackPhase === "preparing") {
      audio.pause();
      return;
    }

    const isAdvertisement = playbackPhase === "advertisement";
    const isIntroduction = playbackPhase === "introduction";
    const isContent = playbackPhase === "content";
    const expectedSource = isAdvertisement
      ? currentAdvertisement?.url
      : isIntroduction
        ? currentTrack.introduction?.url
        : currentTrack.audioUrl;
    if (previousTrack?.id === currentTrack.id && audio.src === expectedSource) return;

    if (previousTrack) {
      flushProgress(previousTrack, audio.currentTime, audio.duration);
    }

    activeTrack.current = isContent ? currentTrack : null;
    if (isContent) recordRecentlyPlayed(currentTrack.id);
    const resumeTime = isContent ? playbackStartPosition : 0;
    pendingResumeTime.current = resumeTime;
    lastRecordedProgress.current =
      resumeTime > 0
        ? { trackId: currentTrack.id, second: Math.floor(resumeTime) }
        : null;
    setLoading(true);
    setPlaybackError(null);
    audio.src = expectedSource ?? currentTrack.audioUrl;
    audio.load();
    setCurrentTime(resumeTime);
  }, [
    currentTrack,
    currentAdvertisement,
    playbackPhase,
    playbackStartPosition,
    flushProgress,
    setCurrentTime,
    setLoading,
    setPlaybackError,
  ]);

  useLayoutEffect(() => {
    const audio = getAudioInstance();

    if (!currentTrack || !isPlaying || playbackPhase === "preparing") {
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
            ? "Press Play to start the audio."
            : "Audio could not be played. Please try again.",
      });
    });
  }, [currentTrack, isPlaying, playbackPhase, setPlaybackError]);

  useEffect(() => {
    if (wasPlaying.current && !isPlaying) {
      if (playbackPhase === "content") flushProgress();
    }
    wasPlaying.current = isPlaying;
  }, [flushProgress, isPlaying, playbackPhase]);

  useEffect(() => {
    const handlePageExit = () => {
      if (usePlayerStore.getState().playbackPhase === "content") flushProgress();
    };

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
      playbackPhase === "content" &&
      Number.isFinite(currentTime) &&
      Math.abs(audio.currentTime - currentTime) > 0.1
    ) {
      if (audio.readyState >= HTMLMediaElement.HAVE_METADATA) {
        audio.currentTime = currentTime;
      } else {
        pendingResumeTime.current = currentTime;
      }
    }
  }, [currentTime, currentTrack, playbackPhase]);

  useEffect(() => {
    const audio = getAudioInstance();
    audio.volume = volume;
    audio.muted = isMuted;
  }, [isMuted, volume]);

  useEffect(() => {
    getAudioInstance().playbackRate = playbackSpeed;
  }, [playbackSpeed]);

  useEffect(() => {
    if (!sleepTimerMinutes) return;

    const timeoutId = window.setTimeout(() => {
      getAudioInstance().pause();
      usePlayerStore.getState().pause();
      usePlayerStore.getState().setSleepTimer(0);
    }, sleepTimerMinutes * 60_000);

    return () => window.clearTimeout(timeoutId);
  }, [setSleepTimer, sleepTimerMinutes]);

  useEffect(() => {
    if (!("mediaSession" in navigator)) return;

    if (currentTrack) {
      navigator.mediaSession.metadata = new MediaMetadata({
        title:
          playbackPhase === "advertisement" && currentAdvertisement
            ? currentAdvertisement.title
            : currentTrack.title,
        artist:
          playbackPhase === "advertisement"
            ? "Advertisement · SunneKatha"
            : `${currentTrack.author.name} · ${currentTrack.narrator.name}`,
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
  }, [
    currentAdvertisement,
    currentTrack,
    next,
    pause,
    play,
    playbackPhase,
    previous,
    seek,
  ]);

  return null;
}
