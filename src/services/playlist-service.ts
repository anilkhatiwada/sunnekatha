import { playlists } from "@/data";
import { environment } from "@/config/environment";
import { apiClient } from "@/services/api-client";
import { mapCompactPlaylist, mapPlaylistDetail } from "@/services/api-mappers";
import { mockApiResponse } from "@/services/mock-api";
import { nullOnNotFound, unwrapPage } from "@/services/public-api-utils";
import type { ApiPlaylistDetail, ApiPlaylistPage } from "@/types/backend-api";
import type { CatalogPlaylist } from "@/types";

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
      apiClient.get<ApiPlaylistDetail>(`/playlists/${slug}/`),
    );
    return payload ? mapPlaylistDetail(payload) : null;
  }
  const playlist = playlists.find((item) => item.slug === slug) ?? null;
  return mockApiResponse(playlist, undefined, null);
}
