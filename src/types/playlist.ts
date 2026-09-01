import type { CatalogTrack, Track } from "@/types/track";
import type { LiteraryWork } from "@/types/catalog";

export type PlaylistContentItem =
  | { id: string; position: number; kind: "track"; content: CatalogTrack }
  | { id: string; position: number; kind: "work"; content: LiteraryWork };

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
  items?: PlaylistContentItem[];
}

export type CatalogPlaylist = Omit<Playlist, "tracks"> & {
  tracks: CatalogTrack[];
};
