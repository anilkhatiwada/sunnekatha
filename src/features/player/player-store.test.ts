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
    sleepTimerMinutes: 0,
    isLoading: false,
    playbackError: null,
    playbackPhase: "content",
    playbackSource: "manual",
    playbackStartPosition: 0,
    currentAdvertisement: null,
    playbackSequence: 0,
  });
}

describe("player store", () => {
  beforeEach(resetPlayerStore);

  it("plays, pauses, and toggles the current track", () => {
    usePlayerStore.getState().play(tracks[0]);
    expect(usePlayerStore.getState().isPlaying).toBe(true);

    usePlayerStore.getState().pause();
    expect(usePlayerStore.getState().isPlaying).toBe(false);

    usePlayerStore.getState().togglePlay();
    expect(usePlayerStore.getState().isPlaying).toBe(true);
  });

  it("plays introductions for sequenced playback but skips them for direct playback", () => {
    const track = {
      ...tracks[0],
      introduction: {
        url: "https://media.example/introduction.mp3",
        duration: 12,
        expiresAt: null,
      },
    };

    usePlayerStore.getState().play(track, "manual");
    expect(usePlayerStore.getState().playbackPhase).toBe("preparing");
    usePlayerStore.getState().preparePlayback(null, 1);
    expect(usePlayerStore.getState().playbackPhase).toBe("content");
    expect(usePlayerStore.getState().playbackStartPosition).toBe(0);

    usePlayerStore.getState().replaceQueue([track], 0, "playlist");
    expect(usePlayerStore.getState().playbackPhase).toBe("preparing");
    usePlayerStore.getState().preparePlayback(null, 2);
    expect(usePlayerStore.getState().playbackPhase).toBe("introduction");

    usePlayerStore.getState().finishIntroduction();
    expect(usePlayerStore.getState().playbackPhase).toBe("content");
    expect(usePlayerStore.getState().currentTrack?.id).toBe(track.id);
  });

  it("resumes only continue playback after an optional introduction", () => {
    const track = {
      ...tracks[0],
      introduction: {
        url: "https://media.example/introduction.mp3",
        duration: 12,
        expiresAt: null,
      },
    };

    usePlayerStore.getState().play(track, "continue", 47);
    usePlayerStore.getState().preparePlayback(null, 1);
    expect(usePlayerStore.getState().playbackPhase).toBe("introduction");
    expect(usePlayerStore.getState().playbackStartPosition).toBe(47);

    usePlayerStore.getState().finishIntroduction();
    expect(usePlayerStore.getState().playbackPhase).toBe("content");
    expect(usePlayerStore.getState().playbackStartPosition).toBe(47);

    usePlayerStore.getState().play(track, "autoplay", 47);
    expect(usePlayerStore.getState().playbackStartPosition).toBe(0);
  });

  it("orders an eligible advertisement before introduction and content", () => {
    const track = {
      ...tracks[0],
      introduction: {
        url: "https://media.example/introduction.mp3",
        duration: 12,
        expiresAt: null,
      },
    };
    const advertisement = {
      id: "ad-1",
      title: "SunneKatha announcement",
      url: "https://media.example/ad.mp3",
      duration: 8,
      expiresAt: null,
    };

    usePlayerStore.getState().replaceQueue([track], 0, "playlist");
    usePlayerStore.getState().preparePlayback(advertisement, 3);
    expect(usePlayerStore.getState().playbackPhase).toBe("advertisement");

    usePlayerStore.getState().finishAdvertisement();
    expect(usePlayerStore.getState().playbackPhase).toBe("introduction");

    usePlayerStore.getState().finishIntroduction();
    expect(usePlayerStore.getState().playbackPhase).toBe("content");
    expect(usePlayerStore.getState().currentTime).toBe(0);
  });

  it("clamps seeking, volume, and playback speed to safe ranges", () => {
    usePlayerStore.getState().play(tracks[0]);
    usePlayerStore.getState().setDuration(100);
    usePlayerStore.getState().seek(150);
    usePlayerStore.getState().setVolume(2);
    usePlayerStore.getState().setPlaybackSpeed(10);

    expect(usePlayerStore.getState().currentTime).toBe(100);
    expect(usePlayerStore.getState().volume).toBe(1);
    expect(usePlayerStore.getState().playbackSpeed).toBe(3);

    usePlayerStore.getState().seek(-10);
    usePlayerStore.getState().setVolume(0);
    usePlayerStore.getState().setPlaybackSpeed(0.1);

    expect(usePlayerStore.getState().currentTime).toBe(0);
    expect(usePlayerStore.getState().volume).toBe(0);
    expect(usePlayerStore.getState().isMuted).toBe(true);
    expect(usePlayerStore.getState().playbackSpeed).toBe(0.5);
  });

  it("toggles mute without losing the selected volume", () => {
    usePlayerStore.getState().setVolume(0.65);
    usePlayerStore.getState().toggleMuted();

    expect(usePlayerStore.getState().isMuted).toBe(true);
    expect(usePlayerStore.getState().volume).toBe(0.65);

    usePlayerStore.getState().toggleMuted();
    expect(usePlayerStore.getState().isMuted).toBe(false);
  });

  it("moves to the next and previous queue items", () => {
    usePlayerStore.getState().replaceQueue(tracks.slice(0, 3));

    usePlayerStore.getState().next();
    expect(usePlayerStore.getState().currentTrack?.id).toBe(tracks[1].id);
    expect(usePlayerStore.getState().playbackStartPosition).toBe(0);

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

  it("does not loop a single queue item when shuffle is enabled", () => {
    usePlayerStore.getState().replaceQueue(tracks.slice(0, 1));
    usePlayerStore.getState().toggleShuffle();

    usePlayerStore.getState().next();

    expect(usePlayerStore.getState().currentTrack?.id).toBe(tracks[0].id);
    expect(usePlayerStore.getState().isPlaying).toBe(false);
  });

  it("keeps the sleep timer in global player state", () => {
    usePlayerStore.getState().setSleepTimer(30);
    expect(usePlayerStore.getState().sleepTimerMinutes).toBe(30);

    usePlayerStore.getState().setSleepTimer(0);
    expect(usePlayerStore.getState().sleepTimerMinutes).toBe(0);
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

  it("refreshes an expiring media source in both current track and queue", () => {
    const original = tracks[0];
    usePlayerStore.getState().play(original);
    const refreshed = {
      ...original,
      audioUrl: "https://media.example/refreshed.mp3",
    };

    usePlayerStore.getState().updateTrackSource(refreshed);

    expect(usePlayerStore.getState().currentTrack?.audioUrl).toBe(
      refreshed.audioUrl,
    );
    expect(usePlayerStore.getState().queue[0].track.audioUrl).toBe(
      refreshed.audioUrl,
    );
  });
});
