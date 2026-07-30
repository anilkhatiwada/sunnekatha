import {
  authors,
  narrators,
  playlists,
  tracks,
  userLibrary,
} from "@/data";
import { environment } from "@/config/environment";
import { apiClient } from "@/services/api-client";
import {
  mapAuthorSummary,
  mapCompactPlaylist,
  mapCompactTrack,
  mapListeningProgress,
  mapNarratorSummary,
} from "@/services/api-mappers";
import { mockApiResponse } from "@/services/mock-api";
import { unwrapPage } from "@/services/public-api-utils";
import type {
  ApiAuthorPage,
  ApiContinueListeningPage,
  ApiListeningHistoryPage,
  ApiNarratorPage,
  ApiPlaylistPage,
  ApiRecentlyPlayedPage,
  ApiRelationshipResponse,
  ApiTrackPage,
  Author,
  Narrator,
  Playlist,
  RemoteUserLibrary,
  Track,
  UserLibrary,
  ListeningHistoryItem,
} from "@/types";

export interface LibraryCatalog {
  tracks: Track[];
  playlists: Playlist[];
  authors: Author[];
  narrators: Narrator[];
}

export async function getListeningHistory(): Promise<ListeningHistoryItem[]> {
  const page = await apiClient.get<ApiListeningHistoryPage>(
    "/me/listening-history/",
    {
      query: { pageSize: 50 },
      requiresAuth: true,
    },
  );
  return unwrapPage(page).map((item) => ({
    track: mapCompactTrack(item.track),
    firstListenedAt: item.firstListenedAt,
    lastListenedAt: item.lastListenedAt,
    totalListenedSeconds: item.totalListenedSeconds,
    playCount: item.playCount,
    completionCount: item.completionCount,
  }));
}

export async function getInitialUserLibrary(): Promise<UserLibrary> {
  return mockApiResponse(userLibrary);
}

export async function getLibraryCatalog(): Promise<LibraryCatalog> {
  return mockApiResponse({
    tracks,
    playlists,
    authors,
    narrators,
  });
}

export async function getRemoteUserLibrary(): Promise<RemoteUserLibrary> {
  if (environment.apiMode !== "remote") {
    const trackById = new Map(tracks.map((track) => [track.id, track]));
    return mockApiResponse({
      favoriteTracks: tracks.filter((track) =>
        userLibrary.favoriteTrackIds.includes(track.id),
      ),
      savedPlaylists: playlists.filter((playlist) =>
        userLibrary.savedPlaylistIds.includes(playlist.id),
      ),
      followedAuthors: authors.filter((author) =>
        userLibrary.followedAuthorIds.includes(author.id),
      ),
      followedNarrators: narrators.filter((narrator) =>
        userLibrary.followedNarratorIds.includes(narrator.id),
      ),
      recentlyPlayed: userLibrary.recentlyPlayedTrackIds.flatMap((id) => {
        const track = trackById.get(id);
        return track
          ? [{ track, lastListenedAt: new Date().toISOString() }]
          : [];
      }),
      continueListening: userLibrary.listeningProgress.flatMap((progress) => {
        const track = trackById.get(progress.trackId);
        return track && !progress.isCompleted ? [{ track, progress }] : [];
      }),
    });
  }

  const [
    favoritePage,
    playlistPage,
    authorPage,
    narratorPage,
    recentlyPlayedPage,
    continueListeningPage,
  ] = await Promise.all([
    apiClient.get<ApiTrackPage>("/library/tracks/", {
      query: { pageSize: 100 },
      requiresAuth: true,
    }),
    apiClient.get<ApiPlaylistPage>("/library/playlists/", {
      query: { pageSize: 100 },
      requiresAuth: true,
    }),
    apiClient.get<ApiAuthorPage>("/library/authors/", {
      query: { pageSize: 100 },
      requiresAuth: true,
    }),
    apiClient.get<ApiNarratorPage>("/library/narrators/", {
      query: { pageSize: 100 },
      requiresAuth: true,
    }),
    apiClient.get<ApiRecentlyPlayedPage>("/me/recently-played/", {
      query: { pageSize: 20 },
      requiresAuth: true,
    }),
    apiClient.get<ApiContinueListeningPage>("/me/continue-listening/", {
      query: { pageSize: 50 },
      requiresAuth: true,
    }),
  ]);

  return {
    favoriteTracks: unwrapPage(favoritePage).map(mapCompactTrack),
    savedPlaylists: unwrapPage(playlistPage).map(mapCompactPlaylist),
    followedAuthors: unwrapPage(authorPage).map((author) => ({
      ...mapAuthorSummary(author),
      biography: "",
      genres: [],
      popularTracks: [],
    })),
    followedNarrators: unwrapPage(narratorPage).map((narrator) => ({
      ...mapNarratorSummary(narrator),
      biography: "",
      followerCount: narrator.followerCount ?? 0,
      narratedTracks: [],
    })),
    recentlyPlayed: unwrapPage(recentlyPlayedPage).map((item) => ({
      track: mapCompactTrack(item.track),
      lastListenedAt: item.lastListenedAt,
    })),
    continueListening: unwrapPage(continueListeningPage).map((item) => ({
      track: mapCompactTrack(item.track),
      progress: mapListeningProgress(item.progress),
    })),
  };
}

export type LibraryRelationship =
  | "favoriteTrack"
  | "savedPlaylist"
  | "followedAuthor"
  | "followedNarrator";

const RELATIONSHIP_PATHS: Record<
  LibraryRelationship,
  (id: string) => string
> = {
  favoriteTrack: (id) => `/library/tracks/${id}/favorite/`,
  savedPlaylist: (id) => `/library/playlists/${id}/save/`,
  followedAuthor: (id) => `/library/authors/${id}/follow/`,
  followedNarrator: (id) => `/library/narrators/${id}/follow/`,
};

export function updateLibraryRelationship(
  relationship: LibraryRelationship,
  id: string,
  isActive: boolean,
) {
  const path = RELATIONSHIP_PATHS[relationship](id);
  return isActive
    ? apiClient.post<ApiRelationshipResponse>(path, {
        requiresAuth: true,
      })
    : apiClient.delete<void>(path, { requiresAuth: true });
}
