import { playlists } from "@/data";
import { mockApiResponse } from "@/services/mock-api";
import type { Playlist } from "@/types";

export async function getFeaturedPlaylists(): Promise<Playlist[]> {
  return mockApiResponse(
    playlists.filter((playlist) => playlist.isFeatured),
  );
}

export async function getMoodPlaylists(): Promise<Playlist[]> {
  const moodPlaylists = playlists.filter((playlist) =>
    ["premka-kavita", "barshako-saanjh", "jiwan-ra-darshan"].includes(
      playlist.slug,
    ),
  );

  return mockApiResponse(moodPlaylists);
}

export async function getPlaylistBySlug(
  slug: string,
): Promise<Playlist | null> {
  const playlist = playlists.find((item) => item.slug === slug) ?? null;
  return mockApiResponse(playlist, undefined, null);
}
