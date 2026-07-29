import { authors, playlists, tracks } from "@/data";
import { mockApiResponse } from "@/services/mock-api";
import type { Author, Playlist, Track } from "@/types";

export async function getPopularAuthors(): Promise<Author[]> {
  const popularAuthors = [...authors]
    .sort(
      (a, b) =>
        b.popularTracks.reduce((total, track) => total + track.playCount, 0) -
        a.popularTracks.reduce((total, track) => total + track.playCount, 0),
    )
    .slice(0, 8);

  return mockApiResponse(popularAuthors);
}

export async function getAuthorBySlug(slug: string): Promise<Author | null> {
  const author = authors.find((item) => item.slug === slug) ?? null;
  return mockApiResponse(author, undefined, null);
}

export async function getAuthorTracks(authorId: string): Promise<Track[]> {
  const authorTracks = tracks
    .filter((track) => track.author.id === authorId)
    .sort((a, b) => b.playCount - a.playCount);

  return mockApiResponse(authorTracks);
}

export async function getAuthorFeaturedCollections(
  authorId: string,
): Promise<Playlist[]> {
  const collections = playlists
    .map((playlist) => ({
      playlist,
      authoredTrackCount: playlist.tracks.filter(
        (track) => track.author.id === authorId,
      ).length,
    }))
    .filter(({ authoredTrackCount }) => authoredTrackCount > 0)
    .sort(
      (a, b) =>
        b.authoredTrackCount - a.authoredTrackCount ||
        Number(b.playlist.isFeatured) - Number(a.playlist.isFeatured),
    )
    .slice(0, 6)
    .map(({ playlist }) => playlist);

  return mockApiResponse(collections);
}

export async function getRelatedAuthors(
  authorId: string,
  limit = 6,
): Promise<Author[]> {
  const sourceAuthor = authors.find((author) => author.id === authorId);

  if (!sourceAuthor) {
    return mockApiResponse([]);
  }

  const relatedAuthors = authors
    .filter((author) => author.id !== authorId)
    .map((author) => ({
      author,
      sharedGenres: author.genres.filter((genre) =>
        sourceAuthor.genres.includes(genre),
      ).length,
    }))
    .filter(({ sharedGenres }) => sharedGenres > 0)
    .sort(
      (a, b) =>
        b.sharedGenres - a.sharedGenres ||
        b.author.popularTracks.reduce(
          (total, track) => total + track.playCount,
          0,
        ) -
          a.author.popularTracks.reduce(
            (total, track) => total + track.playCount,
            0,
          ),
    )
    .slice(0, limit)
    .map(({ author }) => author);

  return mockApiResponse(relatedAuthors);
}
