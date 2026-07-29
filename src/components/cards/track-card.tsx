"use client";

import { Crown } from "lucide-react";

import {
  CardPlayButton,
  CardTitleLink,
  MediaArtwork,
} from "@/components/cards/card-primitives";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { formatDuration } from "@/lib/formatters";
import type { CatalogTrack } from "@/types";

interface TrackCardProps<TTrack extends CatalogTrack> {
  track: TTrack;
  onPlay: (track: TTrack) => void;
  priority?: boolean;
}

export function TrackCard<TTrack extends CatalogTrack>({
  track,
  onPlay,
  priority = false,
}: TrackCardProps<TTrack>) {
  return (
    <article className="group min-w-0 rounded-xl border border-transparent p-3 transition-[background-color,border-color,transform] hover:-translate-y-0.5 hover:border-border/80 hover:bg-surface focus-within:border-border/80 focus-within:bg-surface">
      <MediaArtwork
        src={track.coverImage}
        alt={`${track.title} को आवरण`}
        sizes="(max-width: 640px) 44vw, (max-width: 1024px) 28vw, 240px"
        priority={priority}
        className="aspect-square rounded-lg shadow-[0_16px_42px_rgb(0_0_0_/_0.3)]"
      >
        <div className="absolute inset-0 bg-gradient-to-t from-background/60 via-transparent to-transparent" />
        {track.isPremium && (
          <span className="absolute top-2.5 left-2.5 inline-flex items-center gap-1 rounded-full border border-gold/25 bg-background/80 px-2 py-1 text-[0.65rem] font-semibold text-gold backdrop-blur">
            <Crown aria-hidden="true" className="size-3" />
            प्रिमियम
          </span>
        )}
        <CardPlayButton
          label={`${track.title} बजाउनुहोस्`}
          onPlay={() => onPlay(track)}
          className="absolute right-3 bottom-3 translate-y-0 opacity-100 lg:translate-y-2 lg:opacity-0 lg:group-hover:translate-y-0 lg:group-hover:opacity-100 lg:group-focus-within:translate-y-0 lg:group-focus-within:opacity-100"
        />
      </MediaArtwork>

      <div className="mt-4 min-w-0">
        <h3 className="line-clamp-2 min-h-12">
          <CardTitleLink
            href={`/track/${track.slug}`}
            title={track.title}
            className="inline text-base leading-6"
          />
        </h3>
        <p className="mt-1 truncate font-nepali text-sm text-muted-foreground">
          {track.author.name} · {formatDuration(track.duration)}
        </p>
      </div>
    </article>
  );
}

export function TrackCardSkeleton() {
  return (
    <div aria-label="रचना लोड हुँदैछ" role="status" className="p-3">
      <LoadingSkeleton className="aspect-square rounded-lg" />
      <LoadingSkeleton className="mt-4 h-5 w-4/5" />
      <LoadingSkeleton className="mt-2 h-4 w-3/5" />
    </div>
  );
}
