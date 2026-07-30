import type { Metadata } from "next";

import {
  normalizeExploreFilter,
} from "@/features/explore/explore-config";
import { ExplorePageContent } from "@/features/explore/explore-page";

export const metadata: Metadata = {
  title: "अन्वेषण",
  description: "विधा, मूड र सर्जकअनुसार नेपाली श्रव्य साहित्य अन्वेषण गर्नुहोस्।",
};

interface ExplorePageProps {
  searchParams: Promise<{
    type?: string | string[];
    genre?: string | string[];
    mood?: string | string[];
    language?: string | string[];
    premium?: string | string[];
    explicit?: string | string[];
    ordering?: string | string[];
  }>;
}

export default async function ExplorePage({
  searchParams,
}: ExplorePageProps) {
  const params = await searchParams;
  const type = Array.isArray(params.type) ? params.type[0] : params.type;
  const genre = Array.isArray(params.genre) ? params.genre[0] : params.genre;
  const mood = Array.isArray(params.mood) ? params.mood[0] : params.mood;
  const language = first(params.language);
  const premium = parseBoolean(first(params.premium));
  const explicit = parseBoolean(first(params.explicit));
  const ordering = first(params.ordering);

  return (
    <ExplorePageContent
      activeFilter={normalizeExploreFilter(type)}
      genre={genre}
      mood={mood}
      language={language}
      premium={premium}
      explicit={explicit}
      ordering={ordering}
    />
  );
}

function first(value?: string | string[]) {
  return Array.isArray(value) ? value[0] : value;
}

function parseBoolean(value?: string) {
  return value === "true" ? true : value === "false" ? false : undefined;
}
