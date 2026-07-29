import { beforeEach, describe, expect, it } from "vitest";

import { useLibraryStore } from "@/features/library/library-store";
import {
  getResumePosition,
  saveListeningProgress,
} from "@/services/progress-service";

function resetLibraryStore() {
  useLibraryStore.setState({
    hasHydrated: true,
    hasInitialized: true,
    savedPlaylistIds: [],
    favoriteTrackIds: [],
    followedAuthorIds: [],
    followedNarratorIds: [],
    recentlyPlayedTrackIds: [],
    listeningProgress: [],
  });
}

describe("library state", () => {
  beforeEach(resetLibraryStore);

  it("favorites and unfavorites a track", () => {
    useLibraryStore.getState().toggleFavoriteTrack("track-005");
    expect(useLibraryStore.getState().favoriteTrackIds).toContain("track-005");

    useLibraryStore.getState().toggleFavoriteTrack("track-005");
    expect(useLibraryStore.getState().favoriteTrackIds).not.toContain(
      "track-005",
    );
  });

  it("saves resumable progress and marks playback complete at 90 percent", () => {
    const inProgress = saveListeningProgress({
      trackId: "track-005",
      progressSeconds: 50,
      durationSeconds: 100,
    });

    expect(inProgress).toMatchObject({
      progressSeconds: 50,
      isCompleted: false,
    });
    expect(getResumePosition("track-005")).toBe(50);

    const completed = saveListeningProgress({
      trackId: "track-005",
      progressSeconds: 90,
      durationSeconds: 100,
    });

    expect(completed?.isCompleted).toBe(true);
    expect(getResumePosition("track-005")).toBe(0);
  });

  it("clamps invalid progress and ignores empty playback", () => {
    expect(
      saveListeningProgress({
        trackId: "track-005",
        progressSeconds: 0,
        durationSeconds: 100,
      }),
    ).toBeNull();

    const progress = saveListeningProgress({
      trackId: "track-005",
      progressSeconds: 150,
      durationSeconds: 100,
    });
    expect(progress?.progressSeconds).toBe(100);
  });
});
