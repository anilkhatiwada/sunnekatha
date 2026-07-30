import type { Author } from "@/types/author";
import type { Genre, Mood } from "@/types/library";
import type { Narrator } from "@/types/narrator";
import type { CatalogPlaylist } from "@/types/playlist";
import type { CatalogTrack } from "@/types/track";

export interface SearchResults {
  tracks: CatalogTrack[];
  playlists: CatalogPlaylist[];
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

export interface SearchSuggestion {
  id: string;
  type: string;
  slug: string;
  label: string;
  labelEnglish?: string;
}

export interface SearchTrackPage {
  results: CatalogTrack[];
  count: number;
  nextPage: number | null;
}
