import type { PlayerStore } from "@/features/player/player-types";

export const selectCurrentTrack = (state: PlayerStore) => state.currentTrack;
export const selectQueue = (state: PlayerStore) => state.queue;
export const selectCurrentQueueIndex = (state: PlayerStore) =>
  state.currentQueueIndex;
export const selectIsPlaying = (state: PlayerStore) => state.isPlaying;
export const selectCurrentTime = (state: PlayerStore) => state.currentTime;
export const selectDuration = (state: PlayerStore) => state.duration;
export const selectVolume = (state: PlayerStore) => state.volume;
export const selectIsMuted = (state: PlayerStore) => state.isMuted;
export const selectPlaybackSpeed = (state: PlayerStore) => state.playbackSpeed;
export const selectIsShuffleEnabled = (state: PlayerStore) =>
  state.isShuffleEnabled;
export const selectRepeatMode = (state: PlayerStore) => state.repeatMode;
export const selectIsLoading = (state: PlayerStore) => state.isLoading;
export const selectPlaybackError = (state: PlayerStore) => state.playbackError;
export const selectPlay = (state: PlayerStore) => state.play;
export const selectPause = (state: PlayerStore) => state.pause;
export const selectTogglePlay = (state: PlayerStore) => state.togglePlay;
export const selectNext = (state: PlayerStore) => state.next;
export const selectPrevious = (state: PlayerStore) => state.previous;
export const selectSeek = (state: PlayerStore) => state.seek;
export const selectAddToQueue = (state: PlayerStore) => state.addToQueue;
export const selectPlayNext = (state: PlayerStore) => state.playNext;
export const selectPlayQueueItem = (state: PlayerStore) =>
  state.playQueueItem;
export const selectMoveQueueItem = (state: PlayerStore) =>
  state.moveQueueItem;
export const selectRemoveFromQueue = (state: PlayerStore) =>
  state.removeFromQueue;
export const selectClearQueue = (state: PlayerStore) => state.clearQueue;
export const selectReplaceQueue = (state: PlayerStore) => state.replaceQueue;
