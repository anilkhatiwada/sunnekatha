import type { Track } from "@/types/track";

export interface AuthorSummary {
  id: string;
  slug: string;
  name: string;
  nameEnglish?: string;
  image: string;
}

export interface Author extends AuthorSummary {
  biography: string;
  birthYear?: number;
  deathYear?: number;
  genres: string[];
  popularTracks: Track[];
}
