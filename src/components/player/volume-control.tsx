"use client";

import { Volume2, VolumeX } from "lucide-react";

import { Button } from "@/components/ui/button";
import { usePlayerStore } from "@/features/player/player-store";

export function VolumeControl() {
  const volume = usePlayerStore((state) => state.volume);
  const isMuted = usePlayerStore((state) => state.isMuted);
  const setVolume = usePlayerStore((state) => state.setVolume);
  const toggleMuted = usePlayerStore((state) => state.toggleMuted);
  const audibleVolume = isMuted ? 0 : volume;

  return (
    <div className="flex items-center gap-1">
      <Button
        type="button"
        variant="ghost"
        size="icon"
        onClick={toggleMuted}
        aria-label={isMuted ? "आवाज खोल्नुहोस्" : "आवाज बन्द गर्नुहोस्"}
        aria-pressed={isMuted}
        aria-keyshortcuts="M"
        className="size-8 rounded-full"
      >
        {isMuted || volume === 0 ? (
          <VolumeX aria-hidden="true" className="size-4" />
        ) : (
          <Volume2 aria-hidden="true" className="size-4" />
        )}
      </Button>
      <input
        type="range"
        min={0}
        max={1}
        step={0.01}
        value={audibleVolume}
        onChange={(event) => setVolume(event.currentTarget.valueAsNumber)}
        aria-label="आवाजको स्तर"
        aria-valuetext={`${Math.round(audibleVolume * 100)} प्रतिशत`}
        className="player-range w-20"
        style={
          {
            "--range-progress": `${audibleVolume * 100}%`,
          } as React.CSSProperties
        }
      />
    </div>
  );
}
