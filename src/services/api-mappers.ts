import type {
  ApiAuthenticatedUser,
  ApiAuthor,
  ApiAuthorSummary,
  ApiCompactPlaylist,
  ApiCompactTrack,
  ApiDetailedTrack,
  ApiListeningProgress,
  ApiNarratorSummary,
  ApiNarrator,
  ApiPlaylistDetail,
  ApiStreamResponse,
  ApiTaxonomy,
} from "@/types/backend-api";
import type {
  AuthenticatedUser,
  Author,
  AuthorSummary,
  CatalogTrack,
  CatalogPlaylist,
  Genre,
  ListeningProgress,
  Mood,
  NarratorSummary,
  Narrator,
  Track,
} from "@/types";

export const DEFAULT_ARTWORK_PATH = "/icons/pwa-512.png";
export const DEFAULT_AVATAR_PATH = "/icons/pwa-192.png";

export interface AuthenticatedUserDomain extends AuthenticatedUser {
  username: string;
  avatar: string;
  preferredLanguage: "ne" | "en";
  defaultPlaybackSpeed: number;
  autoplayEnabled: boolean;
  explicitContentEnabled: boolean;
  isCreator: boolean;
}

export function mapAuthorSummary(value: ApiAuthorSummary): AuthorSummary {
  return {
    id: value.id,
    slug: value.slug,
    name: value.nameEnglish || value.name,
    nameEnglish: value.nameEnglish || undefined,
    image: value.image || DEFAULT_AVATAR_PATH,
  };
}

export function mapNarratorSummary(
  value: ApiNarratorSummary,
): NarratorSummary {
  return {
    id: value.id,
    slug: value.slug,
    name: value.name,
    image: value.image || DEFAULT_AVATAR_PATH,
  };
}

export function mapAuthor(value: ApiAuthor): Author {
  return {
    ...mapAuthorSummary(value),
    biography: value.biography || value.biographyEnglish,
    birthYear: value.birthYear ?? undefined,
    deathYear: value.deathYear ?? undefined,
    genres: [],
    popularTracks: [],
  };
}

export function mapNarrator(value: ApiNarrator): Narrator {
  return {
    ...mapNarratorSummary(value),
    biography: value.biography || value.biographyEnglish,
    followerCount: value.followerCount ?? 0,
    narratedTracks: [],
  };
}

export function mapCompactTrack(value: ApiCompactTrack): CatalogTrack {
  return {
    id: value.id,
    slug: value.slug,
    title: value.title,
    subtitle: value.subtitle || value.titleEnglish || undefined,
    contentType: value.contentType,
    category: value.category ? mapTaxonomy(value.category) : undefined,
    author: mapAuthorSummary(value.author),
    narrator: mapNarratorSummary(value.narrator),
    coverImage: value.coverImage || DEFAULT_ARTWORK_PATH,
    duration: value.duration,
    publishedAt: value.publishedAt,
    language: value.language,
    genres: value.genres,
    moods: value.moods,
    playCount: value.playCount,
    isPremium: value.isPremium,
    isExplicit: value.isExplicit,
  };
}

export function mapDetailedTrack(value: ApiDetailedTrack): CatalogTrack {
  return {
    ...mapCompactTrack(value),
    description: value.description || value.descriptionEnglish || undefined,
    waveform: value.waveform ?? undefined,
    transcript: value.transcript || undefined,
    literaryWork: {
      title: value.literaryWork.title,
      type: value.literaryWork.type,
      chapterNumber: value.literaryWork.chapterNumber ?? undefined,
    },
  };
}

export function mapPlayableTrack(value: ApiStreamResponse): Track {
  return {
    ...mapCompactTrack(value.track),
    audioUrl: value.url,
    introduction: value.introduction ?? undefined,
  };
}

export function mapCompactPlaylist(
  value: ApiCompactPlaylist,
): CatalogPlaylist {
  return {
    id: value.id,
    slug: value.slug,
    title: value.title,
    description: "",
    coverImage: value.coverImage || DEFAULT_ARTWORK_PATH,
    curatorName: value.curatorName,
    trackCount: value.trackCount,
    totalDuration: value.totalDuration,
    tracks: [],
    category: value.playlistType || value.category,
    isFeatured: value.isFeatured,
    playlistType: value.playlistType,
    visibility: value.visibility,
    isPublished: value.isPublished,
    isOwnedByCurrentUser: value.isOwnedByCurrentUser,
  };
}

export function mapPlaylistDetail(
  value: ApiPlaylistDetail,
): CatalogPlaylist {
  return {
    ...mapCompactPlaylist(value),
    description: value.description || value.descriptionEnglish,
    tracks: value.tracks.map(mapCompactTrack),
  };
}

export function mapTaxonomy(value: ApiTaxonomy): Genre | Mood {
  return {
    id: value.id,
    slug: value.slug,
    name: value.name,
    nameEnglish: value.nameEnglish || undefined,
    description: value.description,
    image: value.image || undefined,
  };
}

export function mapAuthenticatedUser(
  value: ApiAuthenticatedUser,
): AuthenticatedUserDomain {
  return {
    id: value.id,
    email: value.email,
    displayName: value.displayName,
    username: value.username,
    avatar: value.avatar || DEFAULT_AVATAR_PATH,
    preferredLanguage: value.preferredLanguage,
    defaultPlaybackSpeed: value.defaultPlaybackSpeed,
    autoplayEnabled: value.autoplayEnabled,
    explicitContentEnabled: value.explicitContentEnabled,
    isCreator: value.isCreator,
  };
}

export function mapListeningProgress(
  value: ApiListeningProgress,
): ListeningProgress {
  return {
    trackId: value.trackId,
    progressSeconds: value.progressSeconds,
    durationSeconds: value.durationSeconds,
    isCompleted: value.isCompleted,
    updatedAt: value.updatedAt,
  };
}
