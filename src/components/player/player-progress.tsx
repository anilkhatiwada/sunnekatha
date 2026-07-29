"use client";

import { usePlayerStore } from "@/features/player/player-store";
import { formatPlayerTime, getProgressPercentage } from "@/lib/formatters";
import { cn } from "@/lib/utils";

interface PlayerProgressProps {
  compact?: boolean;
  className?: string;
}

export function PlayerProgress({
  compact = false,
  className,
}: PlayerProgressProps) {
  const currentTime = usePlayerStore((state) => state.currentTime);
  const duration = usePlayerStore((state) => state.duration);
  const seek = usePlayerStore((state) => state.seek);
  const hasTrack = usePlayerStore((state) => Boolean(state.currentTrack));
  const progress = getProgressPercentage(currentTime, duration);

  if (compact) {
    return (
      <div
        aria-hidden="true"
        className={cn("h-0.5 overflow-hidden bg-foreground/10", className)}
      >
        <div
          className="h-full bg-primary transition-[width] duration-200"
          style={{ width: `${progress}%` }}
        />
      </div>
    );
  }

  return (
    <div className={cn("flex min-w-0 items-center gap-2", className)}>
      <span className="w-10 text-right text-[0.65rem] tabular-nums text-muted-foreground">
        {formatPlayerTime(currentTime)}
      </span>
      <input
        type="range"
        min={0}
        max={Math.max(duration, 0)}
        step={0.1}
        value={Math.min(currentTime, duration || 0)}
        disabled={!hasTrack || duration <= 0}
        onChange={(event) => seek(event.currentTarget.valueAsNumber)}
        aria-label="अडियो समय"
        aria-valuetext={`${formatPlayerTime(currentTime)} / ${formatPlayerTime(duration)}`}
        aria-keyshortcuts="ArrowLeft ArrowRight"
        className="player-range min-w-0 flex-1"
        style={{ "--range-progress": `${progress}%` } as React.CSSProperties}
      />
      <span className="w-10 text-[0.65rem] tabular-nums text-muted-foreground">
        {formatPlayerTime(duration)}
      </span>
    </div>
  );
}
