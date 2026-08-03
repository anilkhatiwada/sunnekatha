import type { ContentType } from "@/types";

export interface ExploreFilter {
  label: string;
  value: ContentType | "all";
}

export function normalizeExploreFilter(value?: string) {
  return value?.trim() || "all";
}
