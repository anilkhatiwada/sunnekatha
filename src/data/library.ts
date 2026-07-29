import type { UserLibrary } from "@/types";

export const userLibrary: UserLibrary = {
  favoriteTrackIds: ["track-001", "track-004", "track-009", "track-017"],
  savedPlaylistIds: ["playlist-001", "playlist-003", "playlist-006"],
  followedAuthorIds: ["author-anjali", "author-deepak", "author-elina"],
  followedNarratorIds: ["narrator-aasha", "narrator-bikram"],
  recentlyPlayedTrackIds: [
    "track-002",
    "track-008",
    "track-004",
    "track-015",
  ],
  listeningProgress: [
    {
      trackId: "track-002",
      progressSeconds: 486,
      durationSeconds: 1288,
      isCompleted: false,
      updatedAt: "2026-07-18T21:15:00.000Z",
    },
    {
      trackId: "track-008",
      progressSeconds: 1324,
      durationSeconds: 2215,
      isCompleted: false,
      updatedAt: "2026-07-17T14:30:00.000Z",
    },
    {
      trackId: "track-004",
      progressSeconds: 1462,
      durationSeconds: 1462,
      isCompleted: true,
      updatedAt: "2026-07-16T08:40:00.000Z",
    },
    {
      trackId: "track-015",
      progressSeconds: 207,
      durationSeconds: 598,
      isCompleted: false,
      updatedAt: "2026-07-15T18:10:00.000Z",
    },
  ],
};
