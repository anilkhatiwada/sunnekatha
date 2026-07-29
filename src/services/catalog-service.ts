import { genres, moods, tracks } from "@/data";
import { environment } from "@/config/environment";
import { apiClient } from "@/services/api-client";
import { mapCompactTrack, mapTaxonomy } from "@/services/api-mappers";
import { mockApiResponse } from "@/services/mock-api";
import { unwrapPage } from "@/services/public-api-utils";
import type { ApiTaxonomy, ApiTrackPage } from "@/types/backend-api";
import type { CatalogTrack, ContentType, Genre, Mood } from "@/types";

export async function getExploreTracks(
  filters: {
    contentType?: ContentType;
    genre?: string;
    mood?: string;
  } = {},
): Promise<CatalogTrack[]> {
  if (environment.apiMode === "remote") {
    const payload = await apiClient.get<ApiTrackPage>("/explore/tracks/", {
      query: {
        contentType: filters.contentType,
        genre: filters.genre,
        mood: filters.mood,
        ordering: "-published_at",
        pageSize: 40,
      },
    });
    return unwrapPage(payload).map(mapCompactTrack);
  }
  const filteredTracks = tracks.filter(
    (track) =>
      (!filters.contentType || track.contentType === filters.contentType) &&
      (!filters.genre || track.genres.includes(filters.genre)) &&
      (!filters.mood || track.moods.includes(filters.mood)),
  );
  const newestTracks = [...filteredTracks].sort(
    (a, b) =>
      new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime(),
  );

  return mockApiResponse(newestTracks);
}

export async function getGenres(): Promise<Genre[]> {
  if (environment.apiMode === "remote") {
    const payload = await apiClient.get<ApiTaxonomy[]>("/genres/", {
      query: { active: true },
    });
    return payload.map(mapTaxonomy);
  }
  return mockApiResponse(genres);
}

export async function getMoods(): Promise<Mood[]> {
  if (environment.apiMode === "remote") {
    const payload = await apiClient.get<ApiTaxonomy[]>("/moods/", {
      query: { active: true },
    });
    return payload.map(mapTaxonomy);
  }
  return mockApiResponse(moods);
}
