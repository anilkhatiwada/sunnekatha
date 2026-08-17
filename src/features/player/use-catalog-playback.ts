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
        play(track, "manual");
        return;
      }

      setLoading(true);
      setPlaybackError(null);
      try {
        const stream = await getTrackStream(track.slug);
        play(mapPlayableTrack(stream), "manual");
      } catch {
        setLoading(false);
        setPlaybackError({
          code: "stream-unavailable",
          message: "This track cannot be played right now. Please try again.",
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
        replaceQueue(selected, 0, "playlist");
        return;
      }
      setLoading(true);
      setPlaybackError(null);
      try {
        const playable = await Promise.all(
          selected.map(async (track) =>
            isPlayableTrack(track)
              ? track
              : mapPlayableTrack(await getTrackStream(track.slug, "auto", true)),
          ),
        );
        replaceQueue(playable, 0, "playlist");
      } catch {
        setLoading(false);
        setPlaybackError({
          code: "stream-unavailable",
          message:
            "Some playlist tracks cannot be played right now. Please try again.",
        });
      }
    },
    [replaceQueue, setLoading, setPlaybackError],
  );

  const continueTrack = useCallback(
    async (track: CatalogTrack, startPosition: number) => {
      setLoading(true);
      setPlaybackError(null);
      try {
        const playable = isPlayableTrack(track)
          ? track
          : mapPlayableTrack(
              await getTrackStream(track.slug, "auto", true),
            );
        play(playable, "continue", startPosition);
      } catch {
        setLoading(false);
        setPlaybackError({
          code: "stream-unavailable",
          message: "This track cannot be resumed right now. Please try again.",
        });
      }
    },
    [play, setLoading, setPlaybackError],
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
          message: "This playlist cannot be played right now.",
        });
      }
    },
    [playCollection, setLoading, setPlaybackError],
  );

  return { playTrack, continueTrack, playCollection, playPlaylist };
}
