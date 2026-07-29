"use client";

import { useCallback } from "react";

import { usePlayerStore } from "@/features/player/player-store";
import { getTrackStream, mapPlayableTrack } from "@/services";
import type { CatalogTrack, Track } from "@/types";

function isPlayableTrack(track: CatalogTrack): track is Track {
  return "audioUrl" in track && typeof track.audioUrl === "string";
}

export function useCatalogPlayback() {
  const play = usePlayerStore((state) => state.play);
  const replaceQueue = usePlayerStore((state) => state.replaceQueue);
  const setLoading = usePlayerStore((state) => state.setLoading);
  const setPlaybackError = usePlayerStore((state) => state.setPlaybackError);

  const playTrack = useCallback(
    async (track: CatalogTrack) => {
      if (isPlayableTrack(track)) {
        play(track);
        return;
      }

      setLoading(true);
      setPlaybackError(null);
      try {
        const stream = await getTrackStream(track.slug);
        play(mapPlayableTrack(stream));
      } catch {
        setLoading(false);
        setPlaybackError({
          code: "stream-unavailable",
          message: "यो रचना अहिले बजाउन सकिएन। कृपया फेरि प्रयास गर्नुहोस्।",
        });
      }
    },
    [play, setLoading, setPlaybackError],
  );

  const playCollection = useCallback(
    async (tracks: CatalogTrack[], startIndex = 0) => {
      const selected = tracks.slice(startIndex);
      if (selected.length === 0) return;
      if (selected.every(isPlayableTrack)) {
        replaceQueue(selected);
        return;
      }
      await playTrack(selected[0]);
    },
    [playTrack, replaceQueue],
  );

  return { playTrack, playCollection };
}
