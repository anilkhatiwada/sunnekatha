import type { AuthorSummary } from "@/types/author";
import type { ContentType, Language } from "@/types/common";
import type { NarratorSummary } from "@/types/narrator";

export interface LiteraryWorkSummary {
  title: string;
  type: "novel" | "collection";
  chapterNumber?: number;
}

export interface Track {
  id: string;
  slug: string;
  title: string;
  subtitle?: string;
  description?: string;
  contentType: ContentType;
  author: AuthorSummary;
  narrator: NarratorSummary;
  coverImage: string;
  audioUrl: string;
  duration: number;
  publishedAt: string;
  language: Language;
  genres: string[];
  moods: string[];
  playCount: number;
  isPremium: boolean;
  isExplicit: boolean;
  waveform?: number[];
  transcript?: string;
  literaryWork?: LiteraryWorkSummary;
}

export type CatalogTrack = Omit<Track, "audioUrl">;
