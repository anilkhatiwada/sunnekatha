import type { AuthorSummary } from "@/types/author";
import type { ContentType } from "@/types/common";
import type { CatalogTrack } from "@/types/track";
import type { ContentCategory } from "@/types/library";

export interface LiteraryWork {
  id: string;
  slug: string;
  title: string;
  titleEnglish?: string;
  subtitle?: string;
  description: string;
  contentType: ContentType;
  category?: ContentCategory;
  author: AuthorSummary;
  language: string;
  genres: string[];
  moods: string[];
  publicationYear?: number;
  coverImage: string;
  publishedAt: string;
  copyrightStatus: string;
  tracks: CatalogTrack[];
}

export interface Album {
  id: string;
  slug: string;
  title: string;
  titleEnglish?: string;
  description: string;
  coverImage: string;
  author: AuthorSummary;
  albumType: string;
  genres: string[];
  moods: string[];
  releaseDate?: string;
  tracks: CatalogTrack[];
}
