import type { SearchResultType } from "@/types";

export interface SearchFilter {
  label: string;
  value: SearchResultType;
}

export const SEARCH_FILTERS: SearchFilter[] = [
  { label: "All", value: "all" },
  { label: "Track", value: "tracks" },
  { label: "Work", value: "works" },
  { label: "Album", value: "albums" },
  { label: "Playlist", value: "playlists" },
  { label: "Author", value: "authors" },
  { label: "Narrator", value: "narrators" },
  { label: "Genre", value: "genres" },
  { label: "Mood", value: "moods" },
];
