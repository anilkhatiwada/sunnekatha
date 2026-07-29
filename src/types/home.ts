import type {
  Author,
  CatalogTrack,
  Genre,
  ListeningProgress,
  Mood,
  Narrator,
} from "@/types";
import type { CatalogPlaylist } from "@/types/playlist";

export interface HomeAlbum {
  id: string;
  slug: string;
  title: string;
  titleEnglish?: string;
  coverImage: string;
  authorName: string;
  albumType: string;
  releaseDate: string | null;
}

export type HomeSection =
  | {
      id: string;
      title: string;
      titleEnglish?: string;
      kind: "tracks";
      items: CatalogTrack[];
    }
  | {
      id: string;
      title: string;
      titleEnglish?: string;
      kind: "playlists";
      items: CatalogPlaylist[];
    }
  | {
      id: string;
      title: string;
      titleEnglish?: string;
      kind: "authors";
      items: Author[];
    }
  | {
      id: string;
      title: string;
      titleEnglish?: string;
      kind: "narrators";
      items: Narrator[];
    }
  | {
      id: string;
      title: string;
      titleEnglish?: string;
      kind: "moods" | "genres";
      items: (Mood | Genre)[];
    }
  | {
      id: string;
      title: string;
      titleEnglish?: string;
      kind: "albums";
      items: HomeAlbum[];
    }
  | {
      id: string;
      title: string;
      titleEnglish?: string;
      kind: "continue-listening";
      items: HomeContinueListeningItem[];
    };

export interface HomePageData {
  hero: HomeHero | null;
  sections: HomeSection[];
}

export interface HomeContinueListeningItem {
  track: CatalogTrack;
  progress: ListeningProgress;
}

export type HomeHero =
  | { kind: "playlist"; content: CatalogPlaylist }
  | { kind: "track"; content: CatalogTrack }
  | { kind: "album"; content: HomeAlbum };
