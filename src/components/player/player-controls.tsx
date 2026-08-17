"use client";

import {
  LoaderCircle,
  Megaphone,
  Pause,
  Play,
  Repeat,
  Repeat1,
  Shuffle,
  SkipBack,
  SkipForward,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  pauseAudioImmediately,
  playAudioFromUserGesture,
} from "@/features/player/audio-engine";
import { usePlayerStore } from "@/features/player/player-store";
import { cn } from "@/lib/utils";

interface PlayerControlsProps {
  compact?: boolean;
  className?: string;
}

export function PlayerControls({
  compact = false,
  className,
}: PlayerControlsProps) {
  const hasTrack = usePlayerStore((state) => Boolean(state.currentTrack));
  const isPlaying = usePlayerStore((state) => state.isPlaying);
  const isLoading = usePlayerStore((state) => state.isLoading);
  const isShuffleEnabled = usePlayerStore(
    (state) => state.isShuffleEnabled,
  );
  const repeatMode = usePlayerStore((state) => state.repeatMode);
  const playbackPhase = usePlayerStore((state) => state.playbackPhase);
  const togglePlay = usePlayerStore((state) => state.togglePlay);
  const next = usePlayerStore((state) => state.next);
  const previous = usePlayerStore((state) => state.previous);
  const toggleShuffle = usePlayerStore((state) => state.toggleShuffle);
  const setRepeatMode = usePlayerStore((state) => state.setRepeatMode);
  const finishIntroduction = usePlayerStore(
    (state) => state.finishIntroduction,
  );

  const cycleRepeatMode = () => {
    setRepeatMode(
      repeatMode === "off" ? "all" : repeatMode === "all" ? "one" : "off",
    );
  };
  const handleTogglePlay = () => {
    togglePlay();

    if (isPlaying) {
      pauseAudioImmediately();
    } else {
      void playAudioFromUserGesture().catch(() => undefined);
    }
  };

  if (compact) {
    return (
      <div className={cn("flex shrink-0 items-center gap-1", className)}>
        {playbackPhase === "advertisement" ? (
          <span className="flex items-center gap-1 px-1 text-xs text-primary" aria-label="Advertisement playing">
            <Megaphone aria-hidden="true" className="size-3.5" />
            Ad
          </span>
        ) : null}
        {playbackPhase === "introduction" ? (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={finishIntroduction}
            aria-label="Skip spoken introduction"
            className="h-9 rounded-full px-2 text-xs"
          >
            Skip intro
          </Button>
        ) : null}
        <Button
          type="button"
          variant="ghost"
          size="icon"
          disabled={!hasTrack}
          onClick={handleTogglePlay}
          aria-label={isPlaying ? "Pause" : "Play"}
          aria-keyshortcuts="Space"
          className="size-11 rounded-full"
        >
          {isLoading ? (
            <LoaderCircle aria-hidden="true" className="size-5 animate-spin" />
          ) : isPlaying ? (
            <Pause aria-hidden="true" className="size-5 fill-current" />
          ) : (
            <Play aria-hidden="true" className="size-5 fill-current" />
          )}
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          disabled={!hasTrack}
          onClick={next}
          aria-label="Next track"
          aria-keyshortcuts="N"
          className="size-11 rounded-full"
        >
          <SkipForward aria-hidden="true" className="size-5 fill-current" />
        </Button>
      </div>
    );
  }

  return (
    <div className={cn("flex items-center justify-center gap-1", className)}>
      {playbackPhase === "advertisement" ? (
        <span className="mr-1 flex items-center gap-1 text-xs font-medium text-primary" aria-label="Advertisement playing">
          <Megaphone aria-hidden="true" className="size-3.5" />
          Advertisement
        </span>
      ) : null}
      {playbackPhase === "introduction" ? (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={finishIntroduction}
          aria-label="Skip spoken introduction"
          className="mr-1 h-8 rounded-full px-2 text-xs text-primary"
        >
          Skip intro
        </Button>
      ) : null}
      <Button
        type="button"
        variant="ghost"
        size="icon"
        disabled={!hasTrack}
        onClick={toggleShuffle}
        aria-label={
          isShuffleEnabled ? "Disable shuffle" : "Enable shuffle"
        }
        aria-pressed={isShuffleEnabled}
        className={cn(
          "size-8 rounded-full",
          isShuffleEnabled && "text-primary",
        )}
      >
        <Shuffle aria-hidden="true" className="size-4" />
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        disabled={!hasTrack}
        onClick={previous}
        aria-label="Previous track"
        aria-keyshortcuts="P"
        className="size-8 rounded-full"
      >
        <SkipBack aria-hidden="true" className="size-4 fill-current" />
      </Button>
      <Button
        type="button"
        size="icon"
        disabled={!hasTrack}
        onClick={handleTogglePlay}
        aria-label={isPlaying ? "Pause" : "Play"}
        aria-keyshortcuts="Space"
        className="mx-1 size-10 rounded-full text-background shadow-lg shadow-primary/15"
      >
        {isLoading ? (
          <LoaderCircle aria-hidden="true" className="size-5 animate-spin" />
        ) : isPlaying ? (
          <Pause aria-hidden="true" className="size-5 fill-current" />
        ) : (
          <Play aria-hidden="true" className="size-5 fill-current" />
        )}
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        disabled={!hasTrack}
        onClick={next}
        aria-label="Next track"
        aria-keyshortcuts="N"
        className="size-8 rounded-full"
      >
        <SkipForward aria-hidden="true" className="size-4 fill-current" />
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        disabled={!hasTrack}
        onClick={cycleRepeatMode}
        aria-label={`Repeat mode: ${repeatMode}`}
        aria-pressed={repeatMode !== "off"}
        className={cn("size-8 rounded-full", repeatMode !== "off" && "text-primary")}
      >
        {repeatMode === "one" ? (
          <Repeat1 aria-hidden="true" className="size-4" />
        ) : (
          <Repeat aria-hidden="true" className="size-4" />
        )}
      </Button>
    </div>
  );
}
