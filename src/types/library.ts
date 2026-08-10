import type { Author } from "@/types/author";
import type { Narrator } from "@/types/narrator";
import type { CatalogPlaylist } from "@/types/playlist";
import type { CatalogTrack, Track } from "@/types/track";

export interface Genre {
  id: string;
  slug: string;
  name: string;
  nameEnglish?: string;
  description: string;
  image?: string;
}

export interface Mood {
  id: string;
  slug: string;
  name: string;
  nameEnglish?: string;
  description: string;
  image?: string;
}

export type ContentCategory = Genre;

export interface ListeningProgress {
  trackId: string;
  progressSeconds: number;
  durationSeconds: number;
  isCompleted: boolean;
  updatedAt: string;
}

export interface QueueItem {
  id: string;
  track: Track;
  addedAt: string;
  source?: string;
}

export interface UserLibrary {
  favoriteTrackIds: string[];
  savedPlaylistIds: string[];
  followedAuthorIds: string[];
  followedNarratorIds: string[];
  recentlyPlayedTrackIds: string[];
  listeningProgress: ListeningProgress[];
}

export interface ContinueListeningItem {
  track: CatalogTrack;
  progress: ListeningProgress;
}

export interface RecentlyPlayedItem {
  track: CatalogTrack;
  lastListenedAt: string;
}

export interface ListeningHistoryItem extends RecentlyPlayedItem {
  firstListenedAt: string;
  totalListenedSeconds: number;
  playCount: number;
  completionCount: number;
}

export interface RemoteUserLibrary {
  favoriteTracks: CatalogTrack[];
  savedPlaylists: CatalogPlaylist[];
  followedAuthors: Author[];
  followedNarrators: Narrator[];
  recentlyPlayed: RecentlyPlayedItem[];
  continueListening: ContinueListeningItem[];
}
