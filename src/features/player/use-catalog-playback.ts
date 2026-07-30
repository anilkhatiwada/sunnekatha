"use client";

import { useCallback } from "react";

import { usePlayerStore } from "@/features/player/player-store";
import {
  getPlaylistBySlug,
  getTrackStream,
  mapPlayableTrack,
} from "@/services";
import type { CatalogPlaylist, CatalogTrack, Track } from "@/types";

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
      setLoading(true);
      setPlaybackError(null);
      try {
        const playable = await Promise.all(
          selected.map(async (track) =>
            isPlayableTrack(track)
              ? track
              : mapPlayableTrack(await getTrackStream(track.slug)),
          ),
        );
        replaceQueue(playable);
      } catch {
        setLoading(false);
        setPlaybackError({
          code: "stream-unavailable",
          message:
            "प्लेलिस्टका केही रचना अहिले बजाउन सकिएनन्। फेरि प्रयास गर्नुहोस्।",
        });
      }
    },
    [replaceQueue, setLoading, setPlaybackError],
  );

  const playPlaylist = useCallback(
    async (playlist: CatalogPlaylist) => {
      if (playlist.tracks.length > 0) {
        await playCollection(playlist.tracks);
        return;
      }
      setLoading(true);
      setPlaybackError(null);
      try {
        const detail = await getPlaylistBySlug(playlist.slug);
        if (!detail?.tracks.length) {
          throw new Error("Playlist is empty.");
        }
        await playCollection(detail.tracks);
      } catch {
        setLoading(false);
        setPlaybackError({
          code: "playlist-unavailable",
          message: "यो प्लेलिस्ट अहिले बजाउन सकिएन।",
        });
      }
    },
    [playCollection, setLoading, setPlaybackError],
  );

  return { playTrack, playCollection, playPlaylist };
}
