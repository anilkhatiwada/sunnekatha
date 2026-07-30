import type { Author } from "@/types/author";
import type { Genre, Mood } from "@/types/library";
import type { Narrator } from "@/types/narrator";
import type { CatalogPlaylist } from "@/types/playlist";
import type { CatalogTrack } from "@/types/track";

export interface SearchCatalogResult {
  id: string;
  slug: string;
  title: string;
  titleEnglish?: string;
  coverImage: string;
  authorName: string;
}

export interface SearchResults {
  tracks: CatalogTrack[];
  works: SearchCatalogResult[];
  albums: SearchCatalogResult[];
  playlists: CatalogPlaylist[];
  authors: Author[];
  narrators: Narrator[];
  genres: Genre[];
  moods: Mood[];
}

export type SearchResultType =
  | "all"
  | "tracks"
  | "works"
  | "albums"
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
