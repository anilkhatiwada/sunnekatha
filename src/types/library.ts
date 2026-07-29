import type { Track } from "@/types/track";

export interface Genre {
  id: string;
  slug: string;
  name: string;
  nameEnglish?: string;
  description: string;
}

export interface Mood {
  id: string;
  slug: string;
  name: string;
  nameEnglish?: string;
  description: string;
}

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
  track: Track;
  progress: ListeningProgress;
}
