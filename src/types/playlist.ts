import type { CatalogTrack, Track } from "@/types/track";

export interface Playlist {
  id: string;
  slug: string;
  title: string;
  description: string;
  coverImage: string;
  curatorName: string;
  trackCount: number;
  totalDuration: number;
  tracks: Track[];
  category: string;
  isFeatured: boolean;
  playlistType?: string;
  visibility?: "private" | "unlisted" | "public";
  isPublished?: boolean;
  isOwnedByCurrentUser?: boolean;
}

export type CatalogPlaylist = Omit<Playlist, "tracks"> & {
  tracks: CatalogTrack[];
};
