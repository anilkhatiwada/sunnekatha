import type { ContentType } from "@/types";

export interface ExploreFilter {
  label: string;
  value: ContentType | "all";
}

export const EXPLORE_FILTERS: ExploreFilter[] = [
  { label: "सबै", value: "all" },
  { label: "कथा", value: "story" },
  { label: "कविता", value: "poem" },
  { label: "निबन्ध", value: "essay" },
  { label: "उपन्यास", value: "novel_chapter" },
  { label: "लोककथा", value: "folk_tale" },
  { label: "नाटक", value: "drama" },
];

export function normalizeExploreFilter(value?: string) {
  return (
    EXPLORE_FILTERS.find((filter) => filter.value === value)?.value ?? "all"
  );
}
