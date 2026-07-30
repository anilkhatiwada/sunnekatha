"use client";

import Image from "next/image";
import Link from "next/link";

import { CardPlayButton } from "@/components/cards/card-primitives";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { formatDuration } from "@/lib/formatters";
import { cn } from "@/lib/utils";
import type { CatalogTrack } from "@/types";

interface CompactTrackRowProps<TTrack extends CatalogTrack> {
  track: TTrack;
  onPlay: (track: TTrack) => void;
  index?: number;
  className?: string;
}

export function CompactTrackRow<TTrack extends CatalogTrack>({
  track,
  onPlay,
  index,
  className,
}: CompactTrackRowProps<TTrack>) {
  return (
    <article
      className={cn(
        "group grid min-w-0 grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 rounded-lg border border-transparent px-2 py-2 transition-colors hover:border-border/70 hover:bg-surface focus-within:border-border/70 focus-within:bg-surface sm:grid-cols-[2rem_auto_minmax(0,1fr)_auto]",
        className,
      )}
    >
      <span className="hidden text-center text-xs tabular-nums text-muted-foreground sm:block">
        {index === undefined ? "—" : index + 1}
      </span>
      <div className="relative size-12 overflow-hidden rounded-md bg-surface-soft">
        <Image
          src={track.coverImage}
          alt={`${track.title} को आवरण`}
          fill
          sizes="48px"
          className="object-cover"
        />
      </div>
      <div className="min-w-0">
        <Link
          href={`/track/${track.slug}`}
          className="block truncate rounded-sm font-nepali text-sm font-semibold text-foreground transition-colors hover:text-primary focus-visible:outline-2 focus-visible:outline-primary"
        >
          {track.title}
        </Link>
        <p className="mt-0.5 truncate font-nepali text-xs text-muted-foreground">
          {track.author.name} · {formatDuration(track.duration)}
        </p>
      </div>
      <CardPlayButton
        label={`${track.title} बजाउनुहोस्`}
        onPlay={() => onPlay(track)}
        size="sm"
        className="shadow-none"
      />
    </article>
  );
}

export function CompactTrackRowSkeleton() {
  return (
    <div
      aria-label="रचना लोड हुँदैछ"
      role="status"
      className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 px-2 py-2 sm:grid-cols-[2rem_auto_minmax(0,1fr)_auto]"
    >
      <LoadingSkeleton className="hidden h-4 w-5 sm:block" />
      <LoadingSkeleton className="size-12 rounded-md" />
      <div>
        <LoadingSkeleton className="h-4 w-1/2" />
        <LoadingSkeleton className="mt-2 h-3 w-1/3" />
      </div>
      <LoadingSkeleton className="size-9 rounded-full" />
    </div>
  );
}
