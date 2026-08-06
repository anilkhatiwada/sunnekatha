import { environment } from "@/config/environment";
import {
  getPopularAuthors,
} from "@/services/author-service";
import { apiClient } from "@/services/api-client";
import {
  DEFAULT_ARTWORK_PATH,
  DEFAULT_AVATAR_PATH,
  mapCompactPlaylist,
  mapCompactTrack,
  mapListeningProgress,
} from "@/services/api-mappers";
import {
  getPopularNarrators,
} from "@/services/narrator-service";
import {
  getFeaturedPlaylists,
  getMoodPlaylists,
} from "@/services/playlist-service";
import {
  getContinueListening,
  getRecentlyAddedTracks,
  getTrendingTracks,
} from "@/services/track-service";
import { ApiError } from "@/services/api-error";
import type {
  ApiAuthorSummary,
  ApiCompactPlaylist,
  ApiCompactTrack,
  ApiContinueListeningItem,
  ApiListeningProgress,
  ApiNarratorSummary,
} from "@/types/backend-api";
import type {
  Author,
  HomeAlbum,
  HomePageData,
  HomeSection,
  Mood,
  Narrator,
} from "@/types";

export async function getHomePage(): Promise<HomePageData> {
  if (environment.apiMode === "mock") return getMockHomePage();

  const payload = await apiClient.get<unknown>("/home/", {
    requiresAuth: true,
  });
  return mapHomeResponse(payload);
}

async function getMockHomePage(): Promise<HomePageData> {
  const [
    playlists,
    continuing,
    trending,
    recent,
    authors,
    narrators,
    moodPlaylists,
  ] = await Promise.all([
    getFeaturedPlaylists(),
    getContinueListening(),
    getTrendingTracks(),
    getRecentlyAddedTracks(),
    getPopularAuthors(),
    getPopularNarrators(),
    getMoodPlaylists(),
  ]);

  return {
    hero: playlists[0]
      ? { kind: "playlist", content: playlists[0] }
      : null,
    sections: [
      section("continue-listening", "अहिले सुन्दै हुनुहुन्छ", "continue-listening", continuing),
      section("featured-playlists", "विशेष प्लेलिस्टहरू", "playlists", playlists),
      section("trending-tracks", "यो हप्ता लोकप्रिय", "tracks", trending),
      section("recently-added", "भर्खरै थपिएका", "tracks", recent),
      section("popular-authors", "लोकप्रिय लेखकहरू", "authors", authors),
      section("popular-narrators", "लोकप्रिय वाचकहरू", "narrators", narrators),
      section("mood-collections", "मूडअनुसार सुन्नुहोस्", "playlists", moodPlaylists),
    ],
  };
}

function section<TKind extends HomeSection["kind"]>(
  id: string,
  title: string,
  kind: TKind,
  items: Extract<HomeSection, { kind: TKind }>["items"],
) {
  return { id, title, kind, items, layout: "rail" } as Extract<
    HomeSection,
    { kind: TKind }
  >;
}

export function mapHomeResponse(payload: unknown): HomePageData {
  if (!isRecord(payload) || !Array.isArray(payload.sections)) {
    throw malformedHomeResponse();
  }

  return {
    hero: mapHero(payload.hero),
    sections: payload.sections.flatMap(mapSection),
  };
}

function mapHero(value: unknown) {
  if (!isRecord(value)) return null;
  if (value.contentType === "playlist") {
    const playlist = parseHomePlaylist(value.content);
    return playlist
      ? { kind: "playlist" as const, content: mapCompactPlaylist(playlist) }
      : null;
  }
  if (value.contentType === "track") {
    const track = parseCompactTrack(value.content);
    return track
      ? { kind: "track" as const, content: mapCompactTrack(track) }
      : null;
  }
  if (value.contentType === "album") {
    const album = mapHomeAlbum(value.content);
    return album ? { kind: "album" as const, content: album } : null;
  }
  return null;
}

function mapSection(value: unknown): HomeSection[] {
  if (
    !isRecord(value) ||
    !isString(value.id) ||
    !isString(value.title) ||
    !Array.isArray(value.items)
  ) {
    return [];
  }
  const titleEnglish = isString(value.titleEnglish)
    ? value.titleEnglish
    : undefined;
  const subtitle =
    isString(value.subtitle) && value.subtitle ? value.subtitle : undefined;
  const subtitleEnglish =
    isString(value.subtitleEnglish) && value.subtitleEnglish
      ? value.subtitleEnglish
      : undefined;
  const layout = value.layout === "grid" ? ("grid" as const) : ("rail" as const);
  const base = {
    id: value.id,
    title: value.title,
    titleEnglish,
    subtitle,
    subtitleEnglish,
    layout,
  };
  const kind = classifySection(value.id, value.items, value.sectionType);

  if (kind === "tracks") {
    return [{
      ...base,
      kind,
      items: value.items.flatMap((item) => {
        const parsed = parseCompactTrack(item);
        return parsed ? [mapCompactTrack(parsed)] : [];
      }),
    }];
  }
  if (kind === "playlists") {
    return [{
      ...base,
      kind,
      items: value.items.flatMap((item) => {
        const parsed = parseHomePlaylist(item);
        return parsed ? [mapCompactPlaylist(parsed)] : [];
      }),
    }];
  }
  if (kind === "authors") {
    return [{
      ...base,
      kind,
      items: value.items.flatMap((item) => {
        const parsed = parseAuthor(item);
        return parsed ? [mapHomeAuthor(parsed)] : [];
      }),
    }];
  }
  if (kind === "narrators") {
    return [{
      ...base,
      kind,
      items: value.items.flatMap((item) => {
        const parsed = parseNarrator(item);
        return parsed ? [mapHomeNarrator(parsed)] : [];
      }),
    }];
  }
  if (kind === "continue-listening") {
    return [{
      ...base,
      kind,
      items: value.items.flatMap((item) => {
        const parsed = parseContinueListening(item);
        return parsed
          ? [{
              track: mapCompactTrack(parsed.track),
              progress: mapListeningProgress(parsed.progress),
            }]
          : [];
      }),
    }];
  }
  if (kind === "albums") {
    return [{
      ...base,
      kind,
      items: value.items.flatMap((item) => {
        const parsed = mapHomeAlbum(item);
        return parsed ? [parsed] : [];
      }),
    }];
  }
  if (kind === "moods" || kind === "genres") {
    return [{
      ...base,
      kind,
      items: value.items.flatMap((item) => {
        const parsed = mapHomeCollection(item);
        return parsed ? [parsed] : [];
      }),
    }];
  }
  return [];
}

function classifySection(id: string, items: unknown[], sectionType: unknown) {
  const explicitKinds: Record<string, HomeSection["kind"]> = {
    tracks: "tracks",
    playlists: "playlists",
    albums: "albums",
    authors: "authors",
    narrators: "narrators",
    genres: "genres",
    moods: "moods",
    continue_listening: "continue-listening",
  };
  if (isString(sectionType) && explicitKinds[sectionType]) {
    return explicitKinds[sectionType];
  }
  if (id === "continue-listening" || id === "resume") {
    return "continue-listening";
  }
  if (id.includes("playlist")) return "playlists";
  if (id.includes("author")) return "authors";
  if (id.includes("narrator")) return "narrators";
  if (id.includes("album")) return "albums";
  if (id.includes("mood")) return "moods";
  if (id.includes("genre")) return "genres";

  for (const item of items) {
    if (!isRecord(item)) continue;
    if ("progress" in item && "track" in item) return "continue-listening";
    if ("duration" in item && "narrator" in item) return "tracks";
    if ("curatorName" in item && "trackCount" in item) return "playlists";
    if ("albumType" in item) return "albums";
    if ("followerCount" in item) return "narrators";
    if ("name" in item) return "authors";
  }
  return "unknown";
}

function parseCompactTrack(value: unknown): ApiCompactTrack | null {
  if (
    !isRecord(value) ||
    !hasStrings(value, ["id", "slug", "title", "contentType", "publishedAt"]) ||
    !isRecord(value.author) ||
    !isRecord(value.narrator) ||
    !hasStrings(value.author, ["id", "slug", "name"]) ||
    !hasStrings(value.narrator, ["id", "slug", "name"]) ||
    typeof value.duration !== "number" ||
    typeof value.playCount !== "number" ||
    typeof value.isPremium !== "boolean" ||
    typeof value.isExplicit !== "boolean" ||
    !Array.isArray(value.genres) ||
    !Array.isArray(value.moods)
  ) {
    return null;
  }
  return value as unknown as ApiCompactTrack;
}

function parseHomePlaylist(value: unknown): ApiCompactPlaylist | null {
  if (
    !isRecord(value) ||
    !hasStrings(value, ["id", "slug", "title", "curatorName", "category"]) ||
    typeof value.trackCount !== "number" ||
    typeof value.totalDuration !== "number" ||
    typeof value.isFeatured !== "boolean"
  ) {
    return null;
  }
  return {
    id: value.id as string,
    slug: value.slug as string,
    title: value.title as string,
    titleEnglish: isString(value.titleEnglish) ? value.titleEnglish : "",
    coverImage: isString(value.coverImage) ? value.coverImage : null,
    curatorName: value.curatorName as string,
    trackCount: value.trackCount as number,
    totalDuration: value.totalDuration as number,
    category: value.category as string,
    playlistType: isString(value.playlistType)
      ? value.playlistType
      : (value.category as string),
    visibility: isVisibility(value.visibility) ? value.visibility : "public",
    isFeatured: value.isFeatured as boolean,
    isPublished:
      typeof value.isPublished === "boolean" ? value.isPublished : true,
    createdAt: isString(value.createdAt) ? value.createdAt : "",
    updatedAt: isString(value.updatedAt) ? value.updatedAt : "",
  };
}

function parseAuthor(value: unknown): ApiAuthorSummary | null {
  return isRecord(value) && hasStrings(value, ["id", "slug", "name"])
    ? (value as unknown as ApiAuthorSummary)
    : null;
}

function parseNarrator(value: unknown): ApiNarratorSummary | null {
  return isRecord(value) && hasStrings(value, ["id", "slug", "name"])
    ? (value as unknown as ApiNarratorSummary)
    : null;
}

function mapHomeAuthor(value: ApiAuthorSummary): Author {
  return {
    id: value.id,
    slug: value.slug,
    name: value.name,
    nameEnglish: value.nameEnglish || undefined,
    image: value.image || DEFAULT_AVATAR_PATH,
    biography: "",
    genres: [],
    popularTracks: [],
  };
}

function mapHomeNarrator(value: ApiNarratorSummary): Narrator {
  return {
    id: value.id,
    slug: value.slug,
    name: value.name,
    image: value.image || DEFAULT_AVATAR_PATH,
    biography: "",
    followerCount: value.followerCount ?? 0,
    narratedTracks: [],
  };
}

function parseContinueListening(
  value: unknown,
): ApiContinueListeningItem | null {
  if (!isRecord(value)) return null;
  const track = parseCompactTrack(value.track);
  const progress = parseProgress(value.progress);
  return track && progress ? { track, progress } : null;
}

function parseProgress(value: unknown): ApiListeningProgress | null {
  if (
    !isRecord(value) ||
    !hasStrings(value, ["trackId", "updatedAt"]) ||
    typeof value.progressSeconds !== "number" ||
    typeof value.durationSeconds !== "number" ||
    typeof value.isCompleted !== "boolean"
  ) {
    return null;
  }
  return {
    trackId: value.trackId as string,
    progressSeconds: value.progressSeconds,
    durationSeconds: value.durationSeconds,
    progressPercentage:
      typeof value.progressPercentage === "number"
        ? value.progressPercentage
        : 0,
    isCompleted: value.isCompleted,
    lastListenedAt: isString(value.lastListenedAt)
      ? value.lastListenedAt
      : (value.updatedAt as string),
    updatedAt: value.updatedAt as string,
  };
}

function mapHomeAlbum(value: unknown): HomeAlbum | null {
  if (
    !isRecord(value) ||
    !hasStrings(value, ["id", "slug", "title", "albumType"]) ||
    !isRecord(value.author) ||
    !isString(value.author.name)
  ) {
    return null;
  }
  return {
    id: value.id as string,
    slug: value.slug as string,
    title: value.title as string,
    titleEnglish: isString(value.titleEnglish)
      ? value.titleEnglish
      : undefined,
    coverImage: isString(value.coverImage)
      ? value.coverImage
      : DEFAULT_ARTWORK_PATH,
    authorName: value.author.name,
    albumType: value.albumType as string,
    releaseDate: isString(value.releaseDate) ? value.releaseDate : null,
  };
}

function mapHomeCollection(value: unknown): Mood | null {
  if (!isRecord(value) || !hasStrings(value, ["id", "slug", "title"])) {
    return null;
  }
  return {
    id: value.id as string,
    slug: value.slug as string,
    name: value.title as string,
    nameEnglish: isString(value.titleEnglish)
      ? value.titleEnglish
      : undefined,
    description: "",
  };
}

function malformedHomeResponse() {
  return new ApiError({
    code: "malformed_response",
    message: "गृहपृष्ठको उत्तर बुझ्न सकिएन।",
  });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isString(value: unknown): value is string {
  return typeof value === "string";
}

function hasStrings(value: Record<string, unknown>, keys: string[]) {
  return keys.every((key) => isString(value[key]));
}

function isVisibility(
  value: unknown,
): value is "private" | "unlisted" | "public" {
  return value === "private" || value === "unlisted" || value === "public";
}
