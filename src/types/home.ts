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

interface HomeSectionBase {
  id: string;
  title: string;
  titleEnglish?: string;
  subtitle?: string;
  subtitleEnglish?: string;
  layout: HomeSectionLayout;
  viewAllHref?: string;
}

export type HomeSection =
  | {
      kind: "tracks";
      items: CatalogTrack[];
    } & HomeSectionBase
  | {
      kind: "playlists";
      items: CatalogPlaylist[];
    } & HomeSectionBase
  | {
      kind: "authors";
      items: Author[];
    } & HomeSectionBase
  | {
      kind: "narrators";
      items: Narrator[];
    } & HomeSectionBase
  | {
      kind: "moods" | "genres";
      items: (Mood | Genre)[];
    } & HomeSectionBase
  | {
      kind: "categories";
      items: Genre[];
    } & HomeSectionBase
  | {
      kind: "albums";
      items: HomeAlbum[];
    } & HomeSectionBase
  | {
      kind: "continue-listening";
      items: HomeContinueListeningItem[];
    } & HomeSectionBase;

export type HomeSectionLayout = "rail" | "grid";

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
