import { genres, moods, tracks } from "@/data";
import { mockApiResponse } from "@/services/mock-api";
import type { ContentType, Genre, Mood, Track } from "@/types";

export async function getExploreTracks(
  filters: {
    contentType?: ContentType;
    genre?: string;
    mood?: string;
  } = {},
): Promise<Track[]> {
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
  return mockApiResponse(genres);
}

export async function getMoods(): Promise<Mood[]> {
  return mockApiResponse(moods);
}
