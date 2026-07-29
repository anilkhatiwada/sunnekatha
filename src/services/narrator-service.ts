import { narrators, playlists, tracks } from "@/data";
import { mockApiResponse } from "@/services/mock-api";
import type { Narrator, Playlist, Track } from "@/types";

export async function getPopularNarrators(): Promise<Narrator[]> {
  const popularNarrators = [...narrators]
    .sort((a, b) => b.followerCount - a.followerCount)
    .slice(0, 8);

  return mockApiResponse(popularNarrators);
}

export async function getNarratorBySlug(
  slug: string,
): Promise<Narrator | null> {
  const narrator = narrators.find((item) => item.slug === slug) ?? null;
  return mockApiResponse(narrator, undefined, null);
}

export async function getNarratorTracks(
  narratorId: string,
): Promise<Track[]> {
  const narratedTracks = tracks
    .filter((track) => track.narrator.id === narratorId)
    .sort((a, b) => b.playCount - a.playCount);

  return mockApiResponse(narratedTracks);
}

export async function getNarratorFeaturedPlaylists(
  narratorId: string,
): Promise<Playlist[]> {
  const featuredPlaylists = playlists
    .map((playlist) => ({
      playlist,
      narratedTrackCount: playlist.tracks.filter(
        (track) => track.narrator.id === narratorId,
      ).length,
    }))
    .filter(({ narratedTrackCount }) => narratedTrackCount > 0)
    .sort(
      (a, b) =>
        b.narratedTrackCount - a.narratedTrackCount ||
        Number(b.playlist.isFeatured) - Number(a.playlist.isFeatured),
    )
    .slice(0, 6)
    .map(({ playlist }) => playlist);

  return mockApiResponse(featuredPlaylists);
}
