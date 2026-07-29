"use client";

import { Ellipsis, Play } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { formatPlayerTime } from "@/lib/formatters";
import { cn } from "@/lib/utils";
import type { CatalogTrack, ContentType } from "@/types";

interface PlaylistTrackRowProps {
  track: CatalogTrack;
  index: number;
  isActive: boolean;
  onPlay: () => void;
  onMoreActions: () => void;
}

const CONTENT_TYPE_LABELS: Record<ContentType, string> = {
  poem: "कविता",
  story: "कथा",
  essay: "निबन्ध",
  novel_chapter: "उपन्यास अध्याय",
  folk_tale: "लोककथा",
  drama: "नाटक",
};

export function PlaylistTrackRow({
  track,
  index,
  isActive,
  onPlay,
  onMoreActions,
}: PlaylistTrackRowProps) {
  return (
    <li
      aria-current={isActive ? "true" : undefined}
      className={cn(
        "group grid grid-cols-[2rem_minmax(0,1fr)_auto] items-center gap-2 rounded-lg border border-transparent px-2 py-3 transition-colors hover:border-border/70 hover:bg-surface focus-within:border-border/70 focus-within:bg-surface sm:grid-cols-[2.5rem_minmax(0,1.4fr)_minmax(8rem,0.8fr)_minmax(8rem,0.8fr)_6rem_4rem_auto] sm:gap-3 sm:px-3",
        isActive && "border-primary/25 bg-primary-muted/20",
      )}
    >
      <button
        type="button"
        onClick={onPlay}
        aria-label={`${track.title} बजाउनुहोस्`}
        className="grid size-11 place-items-center rounded-full text-xs tabular-nums text-muted-foreground transition-colors hover:bg-primary hover:text-background focus-visible:outline-2 focus-visible:outline-primary sm:size-8"
      >
        <span className="group-hover:hidden group-focus-within:hidden">
          {index + 1}
        </span>
        <Play
          aria-hidden="true"
          className="hidden size-3.5 fill-current group-hover:block group-focus-within:block"
        />
      </button>

      <div className="min-w-0">
        <button
          type="button"
          onClick={onPlay}
          className="block max-w-full truncate rounded-sm text-left font-nepali text-sm font-semibold text-foreground transition-colors hover:text-primary focus-visible:outline-2 focus-visible:outline-primary"
        >
          {track.title}
        </button>
        <p className="mt-0.5 truncate font-nepali text-xs text-muted-foreground sm:hidden">
          {track.author.name} · {track.narrator.name}
        </p>
        <span className="mt-1 inline-flex rounded-full bg-surface-soft px-2 py-0.5 font-nepali text-[0.65rem] text-muted-foreground sm:hidden">
          {CONTENT_TYPE_LABELS[track.contentType]}
        </span>
      </div>

      <Link
        href={`/author/${track.author.slug}`}
        className="hidden truncate rounded-sm font-nepali text-xs text-muted-foreground transition-colors hover:text-primary focus-visible:outline-2 focus-visible:outline-primary sm:block"
      >
        {track.author.name}
      </Link>
      <Link
        href={`/narrator/${track.narrator.slug}`}
        className="hidden truncate rounded-sm font-nepali text-xs text-muted-foreground transition-colors hover:text-primary focus-visible:outline-2 focus-visible:outline-primary sm:block"
      >
        {track.narrator.name}
      </Link>
      <span className="hidden truncate font-nepali text-xs text-muted-foreground sm:block">
        {CONTENT_TYPE_LABELS[track.contentType]}
      </span>
      <span className="hidden text-right text-xs tabular-nums text-muted-foreground sm:block">
        {formatPlayerTime(track.duration)}
      </span>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        onClick={onMoreActions}
        aria-label={`${track.title} का थप विकल्प`}
        className="size-11 rounded-full text-muted-foreground sm:size-9"
      >
        <Ellipsis aria-hidden="true" className="size-4" />
      </Button>
    </li>
  );
}
