import { tracks, userLibrary } from "@/data";
import { environment } from "@/config/environment";
import { apiClient } from "@/services/api-client";
import { mapCompactTrack, mapDetailedTrack } from "@/services/api-mappers";
import { mockApiResponse } from "@/services/mock-api";
import { nullOnNotFound, unwrapPage } from "@/services/public-api-utils";
import type { ApiDetailedTrack, ApiTrackPage } from "@/types/backend-api";
import type { CatalogTrack, ContinueListeningItem } from "@/types";

export async function getTrendingTracks(): Promise<CatalogTrack[]> {
  if (environment.apiMode === "remote") {
    const payload = await apiClient.get<ApiTrackPage>("/tracks/trending/", {
      query: { pageSize: 12 },
    });
    return unwrapPage(payload).map(mapCompactTrack);
  }
  const trending = [...tracks]
    .sort((a, b) => b.playCount - a.playCount)
    .slice(0, 12);

  return mockApiResponse(trending);
}

export async function getRecentlyAddedTracks(): Promise<CatalogTrack[]> {
  if (environment.apiMode === "remote") {
    const payload = await apiClient.get<ApiTrackPage>("/tracks/recent/", {
      query: { pageSize: 12 },
    });
    return unwrapPage(payload).map(mapCompactTrack);
  }
  const recentlyAdded = [...tracks]
    .sort(
      (a, b) =>
        new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime(),
    )
    .slice(0, 12);

  return mockApiResponse(recentlyAdded);
}

export async function getContinueListening(): Promise<
  ContinueListeningItem[]
> {
  const trackById = new Map(tracks.map((track) => [track.id, track]));
  const items = userLibrary.listeningProgress
    .filter((progress) => !progress.isCompleted)
    .sort(
      (a, b) =>
        new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime(),
    )
    .flatMap((progress) => {
      const track = trackById.get(progress.trackId);
      return track ? [{ track, progress }] : [];
    });

  return mockApiResponse(items);
}

export async function getTrackBySlug(slug: string): Promise<CatalogTrack | null> {
  if (environment.apiMode === "remote") {
    const payload = await nullOnNotFound(
      apiClient.get<ApiDetailedTrack>(`/tracks/${slug}/`),
    );
    return payload ? mapDetailedTrack(payload) : null;
  }
  const track = tracks.find((item) => item.slug === slug) ?? null;
  return mockApiResponse(track, undefined, null);
}

export async function getSimilarTracks(
  trackSlug: string,
  limit = 6,
): Promise<CatalogTrack[]> {
  if (environment.apiMode === "remote") {
    const payload = await apiClient.get<ApiTrackPage>(
      `/tracks/${trackSlug}/related/`,
      { query: { pageSize: limit } },
    );
    return unwrapPage(payload).map(mapCompactTrack);
  }
  const sourceTrack = tracks.find(
    (track) => track.id === trackSlug || track.slug === trackSlug,
  );

  if (!sourceTrack) {
    return mockApiResponse([]);
  }

  const similarTracks = tracks
    .filter((track) => track.id !== sourceTrack.id)
    .map((track) => ({
      track,
      score:
        Number(track.contentType === sourceTrack.contentType) * 3 +
        track.genres.filter((genre) => sourceTrack.genres.includes(genre))
          .length *
          2 +
        track.moods.filter((mood) => sourceTrack.moods.includes(mood)).length +
        Number(track.author.id === sourceTrack.author.id),
    }))
    .filter(({ score }) => score > 0)
    .sort(
      (a, b) =>
        b.score - a.score || b.track.playCount - a.track.playCount,
    )
    .slice(0, limit)
    .map(({ track }) => track);

  return mockApiResponse(similarTracks);
}
