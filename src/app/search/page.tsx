import type { Metadata } from "next";

import { SearchPageContent } from "@/features/search/search-page";

export const metadata: Metadata = {
  title: "Search",
  description: "Search Nepali audio literature, authors, narrators, and collections.",
};

interface SearchPageProps {
  searchParams: Promise<{ q?: string | string[] }>;
}

export default async function SearchPage({ searchParams }: SearchPageProps) {
  const params = await searchParams;
  const query = Array.isArray(params.q) ? params.q[0] : params.q;

  return <SearchPageContent initialQuery={query ?? ""} />;
}
