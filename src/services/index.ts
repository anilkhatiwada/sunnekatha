export {
  getAuthors,
  getAuthorFeaturedCollections,
  getAuthorBySlug,
  getAuthorTracks,
  getPopularAuthors,
  getRelatedAuthors,
} from "@/services/author-service";
export {
  getAlbumBySlug,
  getCatalogTracks,
  getCatalogItems,
  getContentCategories,
  getExploreTracks,
  getGenreBySlug,
  getGenres,
  getLiteraryWorkBySlug,
  getMoodBySlug,
  getMoods,
} from "@/services/catalog-service";
export {
  getCreatorDrafts,
  getCreatorProfile,
  getCreatorUploads,
  submitCreatorTrack,
  updateCreatorDraft,
  updateCreatorProfile,
} from "@/services/creator-service";
export {
  getInitialUserLibrary,
  getLibraryCatalog,
  getListeningHistory,
  getRemoteUserLibrary,
  updateLibraryRelationship,
} from "@/services/library-service";
export type {
  LibraryRelationship,
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
  getNotifications,
  getUnreadNotificationCount,
  markAllNotificationsRead,
  markNotificationRead,
} from "@/services/notification-service";
export {
  addTrackToPlaylist,
  changePlaylistVisibility,
  createPlaylist,
  deletePlaylist,
  duplicatePlaylist,
  getFeaturedPlaylists,
  getMyPlaylists,
  getMoodPlaylists,
  getPlaylistBySlug,
  getPublicPlaylists,
  removeTrackFromPlaylist,
  reorderPlaylistTracks,
  updatePlaylist,
} from "@/services/playlist-service";
export type { PlaylistWriteInput } from "@/services/playlist-service";
export {
  getServerListeningProgress,
  getResumePosition,
  getSavedProgress,
  markTrackCompleted,
  PROGRESS_UPDATE_INTERVAL_SECONDS,
  recordRecentlyPlayed,
  removeFromContinueListening,
  saveListeningProgress,
} from "@/services/progress-service";
export {
  endPlaybackSession,
  startPlaybackSession,
  updatePlaybackSession,
} from "@/services/playback-service";
export {
  clearSynchronizedQueue,
  getCurrentQueue,
  replaceSynchronizedQueue,
  updateSynchronizedQueuePosition,
  updateSynchronizedQueueRepeat,
  updateSynchronizedQueueShuffle,
} from "@/services/queue-service";
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
export {
  cancelDirectUpload,
  confirmDirectUpload,
  getUploadStatus,
  requestDirectUpload,
  uploadCreatorFile,
  uploadFileDirectly,
} from "@/services/upload-service";
export type {
  UploadRequest,
  UploadType,
} from "@/services/upload-service";
export { apiClient } from "@/services/api-client";
export {
  changePassword,
  getCurrentUser,
  hasStoredSession,
  loginWithGoogle,
  loginWithPassword,
  logoutCurrentUser,
  registerAccount,
  updateAccountPreferences,
  updateProfile,
} from "@/services/auth-service";
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
