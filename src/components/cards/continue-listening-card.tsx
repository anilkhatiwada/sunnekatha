"use client";

import {
  CardPlayButton,
  CardTitleLink,
  MediaArtwork,
} from "@/components/cards/card-primitives";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import {
  formatPlayerTime,
  getProgressPercentage,
} from "@/lib/formatters";
import type { ContinueListeningItem, Track } from "@/types";

interface ContinueListeningCardProps {
  item: ContinueListeningItem;
  onPlay: (track: Track) => void;
}

export function ContinueListeningCard({
  item,
  onPlay,
}: ContinueListeningCardProps) {
  const { track, progress } = item;
  const percentage = getProgressPercentage(
    progress.progressSeconds,
    progress.durationSeconds,
  );
  const remainingSeconds = Math.max(
    0,
    progress.durationSeconds - progress.progressSeconds,
  );

  return (
    <article className="group flex min-w-0 items-center gap-4 rounded-xl border border-border/70 bg-surface p-3 transition-[background-color,border-color,transform] hover:-translate-y-0.5 hover:border-primary/30 hover:bg-surface-soft focus-within:border-primary/30">
      <MediaArtwork
        src={track.coverImage}
        alt={`${track.title} को आवरण`}
        sizes="80px"
        className="size-20 shrink-0 rounded-lg sm:size-24"
      />

      <div className="min-w-0 flex-1">
        <h3 className="line-clamp-2">
          <CardTitleLink
            href={`/track/${track.slug}`}
            title={track.title}
            className="inline text-base leading-6"
          />
        </h3>
        <p className="mt-1 truncate font-nepali text-sm text-muted-foreground">
          {track.author.name}
        </p>
        <div className="mt-3">
          <div
            role="progressbar"
            aria-label={`${track.title} श्रवण प्रगति`}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(percentage)}
            aria-valuetext={`${Math.round(percentage)} प्रतिशत सुनिएको, ${formatPlayerTime(remainingSeconds)} बाँकी`}
            className="h-1.5 overflow-hidden rounded-full bg-background"
          >
            <span
              className="block h-full rounded-full bg-primary"
              style={{ width: `${percentage}%` }}
            />
          </div>
          <p className="mt-1.5 font-nepali text-xs text-muted-foreground">
            {Math.round(percentage)}% सुनिएको ·{" "}
            {formatPlayerTime(remainingSeconds)} बाँकी
          </p>
        </div>
      </div>

      <CardPlayButton
        label={`${track.title} सुन्न जारी राख्नुहोस्`}
        onPlay={() => onPlay(track)}
        size="sm"
      />
    </article>
  );
}

export function ContinueListeningCardSkeleton() {
  return (
    <div
      aria-label="श्रवण प्रगति लोड हुँदैछ"
      role="status"
      className="flex items-center gap-4 rounded-xl border border-border/70 bg-surface p-3"
    >
      <LoadingSkeleton className="size-20 shrink-0 rounded-lg sm:size-24" />
      <div className="min-w-0 flex-1">
        <LoadingSkeleton className="h-5 w-3/5" />
        <LoadingSkeleton className="mt-2 h-4 w-2/5" />
        <LoadingSkeleton className="mt-4 h-1.5 w-full rounded-full" />
      </div>
      <LoadingSkeleton className="size-11 shrink-0 rounded-full" />
    </div>
  );
}
