import { playlists } from "@/data";
import { environment } from "@/config/environment";
import { apiClient } from "@/services/api-client";
import { mapCompactPlaylist, mapPlaylistDetail } from "@/services/api-mappers";
import { mockApiResponse } from "@/services/mock-api";
import { nullOnNotFound, unwrapPage } from "@/services/public-api-utils";
import type { ApiPlaylistDetail, ApiPlaylistPage } from "@/types/backend-api";
import type { CatalogPlaylist } from "@/types";

export interface PlaylistWriteInput extends Record<string, unknown> {
  titleNe: string;
  titleEn?: string;
  descriptionNe?: string;
  descriptionEn?: string;
  visibility?: "private" | "unlisted" | "public";
}

export async function getPublicPlaylists(): Promise<CatalogPlaylist[]> {
  const payload = await apiClient.get<ApiPlaylistPage>("/playlists/", {
    query: { pageSize: 40 },
  });
  return unwrapPage(payload).map(mapCompactPlaylist);
}

export async function getMyPlaylists(): Promise<CatalogPlaylist[]> {
  const payload = await apiClient.get<ApiPlaylistPage>("/playlists/", {
    query: { mine: true, pageSize: 100 },
    requiresAuth: true,
  });
  return unwrapPage(payload).map(mapCompactPlaylist);
}

export async function createPlaylist(input: PlaylistWriteInput) {
  const payload = await apiClient.post<
    ApiPlaylistDetail,
    PlaylistWriteInput
  >("/playlists/", {
    body: input,
    requiresAuth: true,
  });
  return mapPlaylistDetail(payload);
}

export async function updatePlaylist(
  slug: string,
  input: Partial<PlaylistWriteInput>,
) {
  const payload = await apiClient.patch<
    ApiPlaylistDetail,
    Partial<PlaylistWriteInput>
  >(`/playlists/${slug}/`, {
    body: input,
    requiresAuth: true,
  });
  return mapPlaylistDetail(payload);
}

export function deletePlaylist(slug: string) {
  return apiClient.delete<void>(`/playlists/${slug}/`, {
    requiresAuth: true,
  });
}

export async function addTrackToPlaylist(slug: string, trackId: string) {
  return mapPlaylistDetail(
    await apiClient.post<ApiPlaylistDetail, { trackId: string }>(
      `/playlists/${slug}/tracks/add/`,
      { body: { trackId }, requiresAuth: true },
    ),
  );
}

export async function removeTrackFromPlaylist(
  slug: string,
  trackId: string,
) {
  return mapPlaylistDetail(
    await apiClient.post<ApiPlaylistDetail, { trackId: string }>(
      `/playlists/${slug}/tracks/remove/`,
      { body: { trackId }, requiresAuth: true },
    ),
  );
}

export async function reorderPlaylistTracks(
  slug: string,
  trackIds: string[],
) {
  return mapPlaylistDetail(
    await apiClient.patch<ApiPlaylistDetail, { trackIds: string[] }>(
      `/playlists/${slug}/tracks/reorder/`,
      { body: { trackIds }, requiresAuth: true },
    ),
  );
}

export async function changePlaylistVisibility(
  slug: string,
  visibility: "private" | "unlisted" | "public",
) {
  return mapPlaylistDetail(
    await apiClient.patch<
      ApiPlaylistDetail,
      { visibility: "private" | "unlisted" | "public" }
    >(`/playlists/${slug}/visibility/`, {
      body: { visibility },
      requiresAuth: true,
    }),
  );
}

export async function duplicatePlaylist(slug: string, titleNe?: string) {
  return mapPlaylistDetail(
    await apiClient.post<ApiPlaylistDetail, { titleNe?: string }>(
      `/playlists/${slug}/duplicate/`,
      { body: titleNe ? { titleNe } : {}, requiresAuth: true },
    ),
  );
}

export async function getFeaturedPlaylists(): Promise<CatalogPlaylist[]> {
  if (environment.apiMode === "remote") {
    const payload = await apiClient.get<ApiPlaylistPage>(
      "/playlists/featured/",
      { query: { pageSize: 12 } },
    );
    return unwrapPage(payload).map(mapCompactPlaylist);
  }
  return mockApiResponse(
    playlists.filter((playlist) => playlist.isFeatured),
  );
}

export async function getMoodPlaylists(): Promise<CatalogPlaylist[]> {
  if (environment.apiMode === "remote") return [];
  const moodPlaylists = playlists.filter((playlist) =>
    ["premka-kavita", "barshako-saanjh", "jiwan-ra-darshan"].includes(
      playlist.slug,
    ),
  );

  return mockApiResponse(moodPlaylists);
}

export async function getPlaylistBySlug(
  slug: string,
): Promise<CatalogPlaylist | null> {
  if (environment.apiMode === "remote") {
    const payload = await nullOnNotFound(
      apiClient.get<ApiPlaylistDetail>(`/playlists/${slug}/`, {
        requiresAuth: true,
      }),
    );
    return payload ? mapPlaylistDetail(payload) : null;
  }
  const playlist = playlists.find((item) => item.slug === slug) ?? null;
  return mockApiResponse(playlist, undefined, null);
}
