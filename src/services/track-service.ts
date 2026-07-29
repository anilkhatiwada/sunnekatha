import { tracks, userLibrary } from "@/data";
import { mockApiResponse } from "@/services/mock-api";
import type { ContinueListeningItem, Track } from "@/types";

export async function getTrendingTracks(): Promise<Track[]> {
  const trending = [...tracks]
    .sort((a, b) => b.playCount - a.playCount)
    .slice(0, 12);

  return mockApiResponse(trending);
}

export async function getRecentlyAddedTracks(): Promise<Track[]> {
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

export async function getTrackBySlug(slug: string): Promise<Track | null> {
  const track = tracks.find((item) => item.slug === slug) ?? null;
  return mockApiResponse(track, undefined, null);
}

export async function getSimilarTracks(
  trackId: string,
  limit = 6,
): Promise<Track[]> {
  const sourceTrack = tracks.find((track) => track.id === trackId);

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
