import type { PaginatedResponse } from "@/types/api";
import type { ContentType, Language } from "@/types/common";

export interface ApiAuthorSummary {
  id: string;
  slug: string;
  name: string;
  nameEnglish: string;
  image: string | null;
  isFeatured?: boolean;
  isVerified?: boolean;
}

export interface ApiAuthor extends ApiAuthorSummary {
  biography: string;
  biographyEnglish: string;
  birthDate: string | null;
  deathDate: string | null;
  birthYear: number | null;
  deathYear: number | null;
  country: string;
  createdAt: string;
  updatedAt: string;
}

export interface ApiNarratorSummary {
  id: string;
  slug: string;
  name: string;
  nameEnglish?: string;
  image: string | null;
  followerCount?: number;
  isFeatured?: boolean;
  isVerified?: boolean;
}

export interface ApiNarrator extends ApiNarratorSummary {
  biography: string;
  biographyEnglish: string;
  createdAt: string;
  updatedAt: string;
}

export interface ApiCompactTrack {
  id: string;
  slug: string;
  title: string;
  titleEnglish: string;
  subtitle: string;
  contentType: ContentType;
  category?: ApiTaxonomy;
  author: ApiAuthorSummary;
  narrator: ApiNarratorSummary;
  coverImage: string | null;
  duration: number;
  language: Language;
  genres: string[];
  moods: string[];
  playCount: number;
  isPremium: boolean;
  isExplicit: boolean;
  isFeatured: boolean;
  publishedAt: string;
}

export interface ApiDetailedTrack extends ApiCompactTrack {
  description: string;
  descriptionEnglish: string;
  chapterNumber: number | null;
  trackNumber: number | null;
  waveform: number[] | null;
  transcript: string;
  processingStatus: string;
  literaryWork: {
    id: string;
    slug: string;
    title: string;
    titleEnglish: string;
    type: "novel" | "collection";
    contentType: ContentType;
    category?: Pick<ApiTaxonomy, "id" | "slug" | "name" | "nameEnglish">;
    chapterNumber: number | null;
  };
  album: {
    id: string;
    slug: string;
    title: string;
    titleEnglish: string;
  } | null;
  createdAt: string;
  updatedAt: string;
}

export interface ApiCompactPlaylist {
  id: string;
  slug: string;
  title: string;
  titleEnglish: string;
  coverImage: string | null;
  curatorName: string;
  trackCount: number;
  totalDuration: number;
  category: string;
  playlistType: string;
  visibility: "private" | "unlisted" | "public";
  isFeatured: boolean;
  isPublished: boolean;
  createdAt: string;
  updatedAt: string;
  isOwnedByCurrentUser?: boolean;
}

export interface ApiPlaylistDetail extends ApiCompactPlaylist {
  description: string;
  descriptionEnglish: string;
  tracks: ApiCompactTrack[];
}

export interface ApiTaxonomy {
  id: string;
  slug: string;
  name: string;
  nameEnglish: string;
  description: string;
  image: string | null;
  sortOrder: number;
  isActive: boolean;
}

export interface ApiCompactLiteraryWork {
  id: string;
  slug: string;
  title: string;
  titleEnglish: string;
  subtitle: string;
  subtitleEnglish: string;
  contentType: ContentType;
  category?: ApiTaxonomy;
  author: ApiAuthorSummary;
  language: string;
  genres: string[];
  moods: string[];
  publicationYear: number | null;
  coverImage: string | null;
  isFeatured: boolean;
  publishedAt: string;
}

export interface ApiLiteraryWork extends ApiCompactLiteraryWork {
  description: string;
  descriptionEnglish: string;
  copyrightStatus: string;
  copyrightOwner: string;
  licenseNotes: string;
  isPublished: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface ApiCompactAlbum {
  id: string;
  slug: string;
  title: string;
  titleEnglish: string;
  coverImage: string | null;
  author: ApiAuthorSummary;
  albumType: string;
  genres: string[];
  moods: string[];
  releaseDate: string | null;
  isFeatured: boolean;
}

export interface ApiAlbum extends ApiCompactAlbum {
  description: string;
  descriptionEnglish: string;
  isPublished: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface ApiAuthenticatedUser {
  id: string;
  email: string;
  username: string;
  displayName: string;
  avatar: string | null;
  preferredLanguage: Language;
  defaultPlaybackSpeed: number;
  autoplayEnabled: boolean;
  explicitContentEnabled: boolean;
  isCreator: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface ApiStreamResponse {
  quality: "low" | "high";
  url: string;
  expiresAt: string | null;
  track: ApiCompactTrack;
  authorization: {
    status: string;
    accessType: string;
    isEntitled: boolean;
    isPrivileged: boolean;
  };
}

export interface ApiListeningProgress {
  trackId: string;
  progressSeconds: number;
  durationSeconds: number;
  progressPercentage: number;
  isCompleted: boolean;
  lastListenedAt: string;
  updatedAt: string;
}

export interface ApiContinueListeningItem {
  track: ApiCompactTrack;
  progress: ApiListeningProgress;
}

export interface ApiRecentlyPlayedItem {
  track: ApiCompactTrack;
  lastListenedAt: string;
}

export interface ApiListeningHistoryItem {
  track: ApiCompactTrack;
  firstListenedAt: string;
  lastListenedAt: string;
  totalListenedSeconds: number;
  playCount: number;
  completionCount: number;
}

export interface ApiRelationshipResponse {
  id: string;
  isFavorited?: boolean;
  isPlaylistSaved?: boolean;
  isAuthorFollowed?: boolean;
  isNarratorFollowed?: boolean;
}

export interface ApiPlaybackSession {
  id: string;
  trackId: string;
  deviceId: string;
  startedAt: string;
  lastActivityAt: string;
  endedAt: string | null;
  listenedSeconds: number;
  completed: boolean;
}

export interface ApiQueueItem {
  id: string;
  track: ApiCompactTrack;
  position: number;
  addedAt: string;
}

export interface ApiUserQueue {
  id: string;
  items: ApiQueueItem[];
  currentIndex: number;
  positionSeconds: number;
  isShuffleEnabled: boolean;
  repeatMode: "off" | "one" | "all";
  updatedAt: string;
}

export interface ApiUploadSession {
  id: string;
  uploadType:
    | "audio_master"
    | "cover_image"
    | "narrator_image"
    | "author_image";
  objectKey: string;
  originalFilename: string;
  contentType: string;
  expectedSize: number;
  status: string;
  expiresAt: string;
  createdAt: string;
  updatedAt: string;
}

export interface ApiUploadInstructions {
  url: string;
  fields: Record<string, string>;
}

export interface ApiUploadURLResponse extends ApiUploadSession {
  upload: ApiUploadInstructions;
}

export interface ApiCreatorProfile {
  id: string;
  displayName: string;
  biography: string;
  roles: Array<
    "narrator" | "editor" | "content_uploader" | "rights_holder"
  >;
  isApproved: boolean;
}

export interface ApiCreatorTrack extends ApiCompactTrack {
  reviewStatus: string;
  processingStatus: string;
  submittedAt: string | null;
  reviewedAt: string | null;
}

export type ApiCreatorTrackPage = PaginatedResponse<ApiCreatorTrack>;
export type ApiCreatorUploadPage = PaginatedResponse<ApiUploadSession>;

export interface ApiNotification {
  id: string;
  type: string;
  title: string;
  message: string;
  data: Record<string, unknown>;
  actionUrl: string;
  isRead: boolean;
  readAt: string | null;
  createdAt: string;
}

export interface ApiUnreadNotificationCount {
  unreadCount: number;
}

export interface ApiGroupedSearchResponse {
  query: string;
  tracks: ApiCompactTrack[];
  literaryWorks: ApiCompactLiteraryWork[];
  playlists: ApiCompactPlaylist[];
  albums: ApiCompactAlbum[];
  authors: ApiAuthorSummary[];
  narrators: ApiNarratorSummary[];
  genres: ApiTaxonomy[];
  moods: ApiTaxonomy[];
}

export interface ApiAutocompleteItem {
  type:
    | "track"
    | "work"
    | "playlist"
    | "album"
    | "author"
    | "narrator"
    | "genre"
    | "mood";
  id: string;
  slug: string;
  label: string;
  labelEnglish: string;
}

export interface ApiTrendingSearchResponse {
  searches: string[];
}

export interface ApiHomeSection {
  id: string;
  title: string;
  titleEnglish?: string;
  items: unknown[];
}

export interface ApiHomeResponse {
  hero: {
    id: string;
    title: string;
    titleEnglish?: string;
    contentType: string | null;
    content: unknown | null;
  } | null;
  sections: ApiHomeSection[];
}

export type ApiTrackPage = PaginatedResponse<ApiCompactTrack>;
export type ApiPlaylistPage = PaginatedResponse<ApiCompactPlaylist>;
export type ApiLiteraryWorkPage =
  PaginatedResponse<ApiCompactLiteraryWork>;
export type ApiAlbumPage = PaginatedResponse<ApiCompactAlbum>;
export type ApiAuthorPage = PaginatedResponse<ApiAuthorSummary>;
export type ApiNarratorPage = PaginatedResponse<ApiNarratorSummary>;
export type ApiContinueListeningPage =
  PaginatedResponse<ApiContinueListeningItem>;
export type ApiRecentlyPlayedPage = PaginatedResponse<ApiRecentlyPlayedItem>;
export type ApiListeningHistoryPage =
  PaginatedResponse<ApiListeningHistoryItem>;
export type ApiNotificationPage = PaginatedResponse<ApiNotification>;
