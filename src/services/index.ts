export {
  getAuthorFeaturedCollections,
  getAuthorBySlug,
  getAuthorTracks,
  getPopularAuthors,
  getRelatedAuthors,
} from "@/services/author-service";
export {
  getExploreTracks,
  getGenres,
  getMoods,
} from "@/services/catalog-service";
export {
  getInitialUserLibrary,
  getLibraryCatalog,
} from "@/services/library-service";
export { getHomePage, mapHomeResponse } from "@/services/home-service";
export { getTrackStream } from "@/services/media-service";
export {
  getNarratorBySlug,
  getNarratorFeaturedPlaylists,
  getNarratorTracks,
  getPopularNarrators,
} from "@/services/narrator-service";
export {
  getFeaturedPlaylists,
  getMoodPlaylists,
  getPlaylistBySlug,
} from "@/services/playlist-service";
export { getListeningStatistics } from "@/services/profile-service";
export {
  getResumePosition,
  getSavedProgress,
  PROGRESS_UPDATE_INTERVAL_SECONDS,
  recordRecentlyPlayed,
  saveListeningProgress,
} from "@/services/progress-service";
export {
  getSearchSuggestions,
  getTrendingSearches,
  searchContent,
  searchTracks,
} from "@/services/search-service";
export {
  getContinueListening,
  getRecentlyAddedTracks,
  getSimilarTracks,
  getTrackBySlug,
  getTrendingTracks,
} from "@/services/track-service";
export { apiClient } from "@/services/api-client";
export { ApiError, normalizeApiError } from "@/services/api-error";
export {
  DEFAULT_ARTWORK_PATH,
  DEFAULT_AVATAR_PATH,
  mapAuthenticatedUser,
  mapAuthor,
  mapAuthorSummary,
  mapCompactPlaylist,
  mapCompactTrack,
  mapDetailedTrack,
  mapListeningProgress,
  mapNarratorSummary,
  mapNarrator,
  mapPlayableTrack,
  mapPlaylistDetail,
  mapTaxonomy,
} from "@/services/api-mappers";
export type {
  AuthenticatedUserDomain,
} from "@/services/api-mappers";
export {
  clearAuthSession,
  configureAuthSession,
  createBrowserAuthSession,
  setAuthTokens,
} from "@/services/auth-session";
export { queryKeys } from "@/services/query-keys";
