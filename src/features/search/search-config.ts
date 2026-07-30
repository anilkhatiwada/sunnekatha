import type { SearchResultType } from "@/types";

export interface SearchFilter {
  label: string;
  value: SearchResultType;
}

export const SEARCH_FILTERS: SearchFilter[] = [
  { label: "सबै", value: "all" },
  { label: "रचना", value: "tracks" },
  { label: "कृति", value: "works" },
  { label: "एल्बम", value: "albums" },
  { label: "प्लेलिस्ट", value: "playlists" },
  { label: "लेखक", value: "authors" },
  { label: "वाचक", value: "narrators" },
  { label: "विधा", value: "genres" },
  { label: "मूड", value: "moods" },
];
