import type { Track } from "@/types/track";

export interface NarratorSummary {
  id: string;
  slug: string;
  name: string;
  image: string;
}

export interface Narrator extends NarratorSummary {
  biography: string;
  followerCount: number;
  narratedTracks: Track[];
}
