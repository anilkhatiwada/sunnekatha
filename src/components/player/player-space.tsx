"use client";

import {
  Heart,
  Headphones,
  ListMusic,
  Maximize2,
} from "lucide-react";
import Image from "next/image";
import { useState } from "react";

import { ErrorState } from "@/components/common/error-state";
import { FullPlayerPanel } from "@/components/player/full-player-panel";
import { PlayerControls } from "@/components/player/player-controls";
import { PlayerProgress } from "@/components/player/player-progress";
import { QueuePanel } from "@/components/player/queue-panel";
import { VolumeControl } from "@/components/player/volume-control";
import { Button } from "@/components/ui/button";
import { useLibraryStore } from "@/features/library/library-store";
import {
  selectCurrentTrack,
  selectPlay,
  selectPlaybackError,
} from "@/features/player/player-selectors";
import { usePlayerStore } from "@/features/player/player-store";
import { cn } from "@/lib/utils";

export function PlayerSpace() {
  const currentTrack = usePlayerStore(selectCurrentTrack);
  const playbackError = usePlayerStore(selectPlaybackError);
  const play = usePlayerStore(selectPlay);
  const setPlaybackError = usePlayerStore(
    (state) => state.setPlaybackError,
  );
  const favoriteTrackIds = useLibraryStore(
    (state) => state.favoriteTrackIds,
  );
  const toggleFavoriteTrack = useLibraryStore(
    (state) => state.toggleFavoriteTrack,
  );
  const [isQueueOpen, setIsQueueOpen] = useState(false);
  const [isFullPlayerOpen, setIsFullPlayerOpen] = useState(false);

  const isFavorite = currentTrack
    ? favoriteTrackIds.includes(currentTrack.id)
    : false;

  const toggleFavorite = () => {
    if (!currentTrack) return;
    toggleFavoriteTrack(currentTrack.id);
  };

  return (
    <>
      <section
        aria-label="अडियो प्लेयर"
        aria-describedby="player-keyboard-shortcuts"
        className="fixed inset-x-0 bottom-[calc(4rem+env(safe-area-inset-bottom))] z-40 h-20 border-y border-border/90 bg-surface/98 shadow-[0_-12px_40px_rgb(0_0_0_/_0.28)] backdrop-blur-xl lg:bottom-0 lg:left-64 lg:h-[5.5rem] lg:border-b-0"
      >
        <p id="player-keyboard-shortcuts" className="sr-only">
          किबोर्ड सर्टकट: स्पेस प्ले वा पज, दायाँ र बायाँ एरो दस सेकेन्ड
          अगाडि वा पछाडि, M आवाज बन्द वा खोल्ने, N अर्को र P अघिल्लो ट्र्याक।
        </p>
        <div className="relative mx-auto h-full max-w-[100rem]">
          <div className="flex h-full items-center gap-2 px-3 lg:hidden">
            <button
              type="button"
              disabled={!currentTrack}
              onClick={() => setIsFullPlayerOpen(true)}
              className="flex min-w-0 flex-1 items-center gap-3 rounded-lg text-left transition-colors hover:bg-surface-soft/70 focus-visible:outline-2 focus-visible:outline-primary disabled:cursor-default"
              aria-label={
                currentTrack
                  ? `${currentTrack.title} को पूर्ण प्लेयर खोल्नुहोस्`
                  : "कुनै ट्र्याक छानिएको छैन"
              }
            >
              <TrackArtwork size="mobile" />
              <TrackText />
            </button>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => setIsQueueOpen(true)}
              aria-label="प्ले सूची खोल्नुहोस्"
              aria-expanded={isQueueOpen}
              className="size-11 shrink-0 rounded-full"
            >
              <ListMusic aria-hidden="true" className="size-4" />
            </Button>
            <PlayerControls compact />
          </div>

          <div className="hidden h-full grid-cols-[minmax(10rem,1fr)_minmax(16rem,1.35fr)_minmax(8rem,0.8fr)] items-center gap-2 px-3 lg:grid xl:grid-cols-[minmax(13rem,1fr)_minmax(20rem,1.35fr)_minmax(13rem,1fr)] xl:gap-5 xl:px-8">
            <div className="flex min-w-0 items-center gap-3">
              <TrackArtwork size="desktop" />
              <TrackText />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                disabled={!currentTrack}
                onClick={toggleFavorite}
                aria-label={
                  isFavorite ? "मनपर्नेबाट हटाउनुहोस्" : "मनपर्नेमा राख्नुहोस्"
                }
                aria-pressed={isFavorite}
                className={cn(
                  "size-8 shrink-0 rounded-full",
                  isFavorite && "text-primary",
                )}
              >
                <Heart
                  aria-hidden="true"
                  className={cn("size-4", isFavorite && "fill-current")}
                />
              </Button>
            </div>

            <div className="min-w-0">
              <PlayerControls />
              <PlayerProgress className="-mt-0.5" />
            </div>

            <div className="flex items-center justify-end gap-1">
              <VolumeControl />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => setIsQueueOpen((isOpen) => !isOpen)}
                aria-label="प्ले सूची खोल्नुहोस्"
                aria-expanded={isQueueOpen}
                className={cn(
                  "size-9 rounded-full",
                  isQueueOpen && "text-primary",
                )}
              >
                <ListMusic aria-hidden="true" className="size-4" />
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                disabled={!currentTrack}
                onClick={() => setIsFullPlayerOpen(true)}
                aria-label="पूर्ण प्लेयर खोल्नुहोस्"
                className="size-9 rounded-full"
              >
                <Maximize2 aria-hidden="true" className="size-4" />
              </Button>
            </div>
          </div>

          <PlayerProgress compact className="absolute inset-x-0 bottom-0 lg:hidden" />
        </div>
      </section>

      {playbackError ? (
        <div className="fixed right-3 bottom-[calc(9.5rem+env(safe-area-inset-bottom))] z-50 w-[calc(100%-1.5rem)] max-w-sm shadow-xl lg:right-6 lg:bottom-24">
          <ErrorState
            compact
            title="अडियो उपलब्ध छैन"
            message={playbackError.message}
            onRetry={
              currentTrack
                ? () => {
                    setPlaybackError(null);
                    play();
                  }
                : undefined
            }
            className="min-h-0 bg-surface py-4"
          />
        </div>
      ) : null}

      <QueuePanel
        isOpen={isQueueOpen}
        onClose={() => setIsQueueOpen(false)}
      />

      {isFullPlayerOpen && currentTrack ? (
        <FullPlayerPanel
          key={currentTrack.id}
          track={currentTrack}
          isFavorite={isFavorite}
          onClose={() => setIsFullPlayerOpen(false)}
          onToggleFavorite={toggleFavorite}
          onOpenQueue={() => {
            setIsFullPlayerOpen(false);
            setIsQueueOpen(true);
          }}
        />
      ) : null}
    </>
  );
}

function TrackArtwork({ size }: { size: "mobile" | "desktop" }) {
  const currentTrack = usePlayerStore(selectCurrentTrack);
  const sizeClass = size === "mobile" ? "size-12" : "size-14";

  if (!currentTrack) {
    return (
      <div
        className={cn(
          "grid shrink-0 place-items-center rounded-lg border border-border bg-surface-soft text-primary",
          sizeClass,
        )}
      >
        <Headphones aria-hidden="true" className="size-5" strokeWidth={1.7} />
      </div>
    );
  }

  return (
    <Image
      src={currentTrack.coverImage}
      alt={`${currentTrack.title} को आवरण`}
      width={56}
      height={56}
      className={cn("shrink-0 rounded-lg object-cover", sizeClass)}
    />
  );
}

function TrackText() {
  const currentTrack = usePlayerStore(selectCurrentTrack);

  return (
    <div className="min-w-0 flex-1" aria-live="polite">
      <p className="truncate font-nepali text-sm font-medium text-foreground">
        {currentTrack?.title ?? "सुन्नका लागि कथा छान्नुहोस्"}
      </p>
      <p className="truncate font-nepali text-xs text-muted-foreground">
        {currentTrack
          ? `${currentTrack.author.name} · ${currentTrack.narrator.name}`
          : "तपाईंको मनपर्ने साहित्य यहाँ बज्नेछ"}
      </p>
    </div>
  );
}
