import type { Author } from "@/types/author";
import type { Genre, Mood } from "@/types/library";
import type { Narrator } from "@/types/narrator";
import type { Playlist } from "@/types/playlist";
import type { Track } from "@/types/track";

export interface SearchResults {
  tracks: Track[];
  playlists: Playlist[];
  authors: Author[];
  narrators: Narrator[];
  genres: Genre[];
  moods: Mood[];
}

export type SearchResultType =
  | "all"
  | "tracks"
  | "playlists"
  | "authors"
  | "narrators"
  | "genres"
  | "moods";

export interface SearchRequest {
  query: string;
  resultType?: SearchResultType;
}
