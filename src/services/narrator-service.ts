import { narrators, playlists, tracks } from "@/data";
import { environment } from "@/config/environment";
import { apiClient } from "@/services/api-client";
import {
  mapCompactTrack,
  mapNarrator,
  mapNarratorSummary,
} from "@/services/api-mappers";
import { mockApiResponse } from "@/services/mock-api";
import { nullOnNotFound, unwrapPage } from "@/services/public-api-utils";
import type {
  ApiNarrator,
  ApiNarratorSummary,
  ApiTrackPage,
} from "@/types/backend-api";
import type { CatalogPlaylist, CatalogTrack, Narrator } from "@/types";

export async function getPopularNarrators(): Promise<Narrator[]> {
  if (environment.apiMode === "remote") {
    const payload = await apiClient.get<{
      count: number;
      next: string | null;
      previous: string | null;
      results: ApiNarratorSummary[];
    }>("/narrators/featured/", { query: { pageSize: 8 } });
    return unwrapPage(payload).map((value) => ({
      ...mapNarratorSummary(value),
      biography: "",
      followerCount: value.followerCount ?? 0,
      narratedTracks: [],
    }));
  }
  const popularNarrators = [...narrators]
    .sort((a, b) => b.followerCount - a.followerCount)
    .slice(0, 8);

  return mockApiResponse(popularNarrators);
}

export async function getNarratorBySlug(
  slug: string,
): Promise<Narrator | null> {
  if (environment.apiMode === "remote") {
    const payload = await nullOnNotFound(
      apiClient.get<ApiNarrator>(`/narrators/${slug}/`),
    );
    return payload ? mapNarrator(payload) : null;
  }
  const narrator = narrators.find((item) => item.slug === slug) ?? null;
  return mockApiResponse(narrator, undefined, null);
}

export async function getNarratorTracks(
  narratorId: string,
): Promise<CatalogTrack[]> {
  if (environment.apiMode === "remote") {
    const payload = await apiClient.get<ApiTrackPage>(
      `/tracks/narrator/${narratorId}/`,
      { query: { ordering: "-play_count_cache", pageSize: 40 } },
    );
    return unwrapPage(payload).map(mapCompactTrack);
  }
  const narratedTracks = tracks
    .filter((track) => track.narrator.id === narratorId)
    .sort((a, b) => b.playCount - a.playCount);

  return mockApiResponse(narratedTracks);
}

export async function getNarratorFeaturedPlaylists(
  narratorId: string,
): Promise<CatalogPlaylist[]> {
  if (environment.apiMode === "remote") return [];
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
