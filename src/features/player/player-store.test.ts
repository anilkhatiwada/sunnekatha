import { beforeEach, describe, expect, it, vi } from "vitest";

import { tracks } from "@/data";
import { usePlayerStore } from "@/features/player/player-store";

function resetPlayerStore() {
  usePlayerStore.setState({
    currentTrack: null,
    queue: [],
    currentQueueIndex: -1,
    isPlaying: false,
    currentTime: 0,
    duration: 0,
    volume: 0.8,
    isMuted: false,
    playbackSpeed: 1,
    isShuffleEnabled: false,
    repeatMode: "off",
    isLoading: false,
    playbackError: null,
  });
}

describe("player store", () => {
  beforeEach(resetPlayerStore);

  it("moves to the next and previous queue items", () => {
    usePlayerStore.getState().replaceQueue(tracks.slice(0, 3));

    usePlayerStore.getState().next();
    expect(usePlayerStore.getState().currentTrack?.id).toBe(tracks[1].id);

    usePlayerStore.getState().previous();
    expect(usePlayerStore.getState().currentTrack?.id).toBe(tracks[0].id);
  });

  it("restarts the current track before moving to the previous item", () => {
    usePlayerStore.getState().replaceQueue(tracks.slice(0, 3), 1);
    usePlayerStore.getState().setCurrentTime(8);

    usePlayerStore.getState().previous();

    expect(usePlayerStore.getState().currentTrack?.id).toBe(tracks[1].id);
    expect(usePlayerStore.getState().currentTime).toBe(0);
  });

  it("wraps at the queue boundary in repeat-all mode", () => {
    usePlayerStore.getState().replaceQueue(tracks.slice(0, 3), 2);
    usePlayerStore.getState().setRepeatMode("all");

    usePlayerStore.getState().next();

    expect(usePlayerStore.getState().currentTrack?.id).toBe(tracks[0].id);
    expect(usePlayerStore.getState().repeatMode).toBe("all");
  });

  it("stores repeat-one mode for the audio engine", () => {
    usePlayerStore.getState().setRepeatMode("one");
    expect(usePlayerStore.getState().repeatMode).toBe("one");
  });

  it("selects a different queue item when shuffle is enabled", () => {
    vi.spyOn(Math, "random").mockReturnValue(0);
    usePlayerStore.getState().replaceQueue(tracks.slice(0, 3));
    usePlayerStore.getState().toggleShuffle();

    usePlayerStore.getState().next();

    expect(usePlayerStore.getState().currentQueueIndex).toBe(1);
    expect(usePlayerStore.getState().currentTrack?.id).not.toBe(tracks[0].id);
  });

  it("supports adding, prioritizing, moving, removing, and clearing queue items", () => {
    usePlayerStore.getState().replaceQueue(tracks.slice(0, 2));
    usePlayerStore.getState().addToQueue(tracks[2]);
    usePlayerStore.getState().playNext(tracks[3]);

    let state = usePlayerStore.getState();
    expect(state.queue.map((item) => item.track.id)).toEqual([
      tracks[0].id,
      tracks[3].id,
      tracks[1].id,
      tracks[2].id,
    ]);

    const lastItemId = state.queue[3].id;
    usePlayerStore.getState().moveQueueItem(lastItemId, 1);
    expect(
      usePlayerStore.getState().queue.map((item) => item.track.id),
    ).toEqual([tracks[0].id, tracks[2].id, tracks[3].id, tracks[1].id]);

    usePlayerStore.getState().removeFromQueue(lastItemId);
    expect(
      usePlayerStore.getState().queue.some((item) => item.id === lastItemId),
    ).toBe(false);

    usePlayerStore.getState().clearQueue();
    state = usePlayerStore.getState();
    expect(state.queue).toEqual([]);
    expect(state.currentTrack).toBeNull();
    expect(state.isPlaying).toBe(false);
  });
});
