"use client";

import {
  LoaderCircle,
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
  const togglePlay = usePlayerStore((state) => state.togglePlay);
  const next = usePlayerStore((state) => state.next);
  const previous = usePlayerStore((state) => state.previous);
  const toggleShuffle = usePlayerStore((state) => state.toggleShuffle);
  const setRepeatMode = usePlayerStore((state) => state.setRepeatMode);

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
        <Button
          type="button"
          variant="ghost"
          size="icon"
          disabled={!hasTrack}
          onClick={handleTogglePlay}
          aria-label={isPlaying ? "पज गर्नुहोस्" : "प्ले गर्नुहोस्"}
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
          aria-label="अर्को ट्र्याक"
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
      <Button
        type="button"
        variant="ghost"
        size="icon"
        disabled={!hasTrack}
        onClick={toggleShuffle}
        aria-label={
          isShuffleEnabled ? "शफल बन्द गर्नुहोस्" : "शफल खोल्नुहोस्"
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
        aria-label="अघिल्लो ट्र्याक"
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
        aria-label={isPlaying ? "पज गर्नुहोस्" : "प्ले गर्नुहोस्"}
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
        aria-label="अर्को ट्र्याक"
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
        aria-label={`दोहोर्‍याउने मोड: ${repeatMode}`}
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
