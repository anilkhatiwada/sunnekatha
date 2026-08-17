import type { QueueItem, Track } from "@/types";

export type RepeatMode = "off" | "one" | "all";
export type PlaybackPhase = "introduction" | "content";
export type PlaybackSource =
  | "manual"
  | "playlist"
  | "queue"
  | "play_all"
  | "autoplay"
  | "continue";

export interface PlayerError {
  code: string;
  message: string;
}

export interface PlayerState {
  currentTrack: Track | null;
  queue: QueueItem[];
  currentQueueIndex: number;
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  volume: number;
  isMuted: boolean;
  playbackSpeed: number;
  isShuffleEnabled: boolean;
  repeatMode: RepeatMode;
  sleepTimerMinutes: number;
  isLoading: boolean;
  playbackError: PlayerError | null;
  playbackPhase: PlaybackPhase;
  playbackSource: PlaybackSource;
  playbackStartPosition: number;
}

export interface PlayerActions {
  play: (
    track?: Track,
    source?: PlaybackSource,
    startPosition?: number,
  ) => void;
  pause: () => void;
  togglePlay: () => void;
  next: () => void;
  previous: () => void;
  seek: (time: number) => void;
  setCurrentTime: (time: number) => void;
  setDuration: (duration: number) => void;
  setVolume: (volume: number) => void;
  setMuted: (isMuted: boolean) => void;
  toggleMuted: () => void;
  setPlaybackSpeed: (speed: number) => void;
  toggleShuffle: () => void;
  setRepeatMode: (mode: RepeatMode) => void;
  setSleepTimer: (minutes: number) => void;
  addToQueue: (track: Track) => void;
  playNext: (track: Track) => void;
  playQueueItem: (queueItemId: string) => void;
  moveQueueItem: (queueItemId: string, targetIndex: number) => void;
  removeFromQueue: (queueItemId: string) => void;
  clearQueue: () => void;
  replaceQueue: (
    tracks: Track[],
    startIndex?: number,
    source?: PlaybackSource,
  ) => void;
  updateTrackSource: (track: Track) => void;
  finishIntroduction: () => void;
  setLoading: (isLoading: boolean) => void;
  setPlaybackError: (error: PlayerError | null) => void;
}

export type PlayerStore = PlayerState & PlayerActions;

export interface PersistedPlayerState {
  queue: QueueItem[];
  currentQueueIndex: number;
  volume: number;
  playbackSpeed: number;
  repeatMode: RepeatMode;
}
