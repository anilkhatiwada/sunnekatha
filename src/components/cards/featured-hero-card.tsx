"use client";

import { Headphones, ListMusic } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import { CardPlayButton } from "@/components/cards/card-primitives";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { formatDuration } from "@/lib/formatters";
import type { Playlist } from "@/types";

interface FeaturedHeroCardProps {
  playlist: Playlist;
  onPlay: (playlist: Playlist) => void;
  priority?: boolean;
}

export function FeaturedHeroCard({
  playlist,
  onPlay,
  priority = true,
}: FeaturedHeroCardProps) {
  return (
    <article className="group relative isolate min-h-[24rem] overflow-hidden rounded-2xl border border-border/80 bg-surface shadow-[0_30px_80px_rgb(0_0_0_/_0.35)] sm:min-h-[28rem] lg:min-h-[30rem]">
      <Image
        src={playlist.coverImage}
        alt=""
        fill
          preload={priority}
        sizes="(max-width: 1024px) 100vw, 1200px"
        className="object-cover transition duration-700 group-hover:scale-[1.02]"
      />
      <div className="absolute inset-0 bg-[linear-gradient(90deg,rgb(11_10_9_/_0.98)_0%,rgb(11_10_9_/_0.82)_44%,rgb(11_10_9_/_0.2)_100%)]" />
      <div className="absolute inset-0 bg-gradient-to-t from-background/80 via-transparent to-transparent" />

      <div className="relative flex min-h-[24rem] max-w-2xl flex-col justify-end p-6 sm:min-h-[28rem] sm:p-9 lg:min-h-[30rem] lg:p-12">
        <p className="text-xs font-semibold tracking-[0.2em] text-primary uppercase">
          विशेष प्रस्तुति
        </p>
        <h2 className="mt-4 font-literary text-4xl leading-tight font-semibold text-foreground sm:text-5xl lg:text-6xl">
          <Link
            href={`/playlist/${playlist.slug}`}
            className="rounded-sm focus-visible:outline-2 focus-visible:outline-primary"
          >
            {playlist.title}
          </Link>
        </h2>
        <p className="mt-5 line-clamp-3 max-w-xl font-nepali text-base leading-8 text-muted-foreground sm:text-lg">
          {playlist.description}
        </p>

        <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2 font-nepali text-sm text-muted-foreground">
          <span className="inline-flex items-center gap-2">
            <ListMusic aria-hidden="true" className="size-4 text-gold" />
            {playlist.trackCount} रचना
          </span>
          <span className="inline-flex items-center gap-2">
            <Headphones aria-hidden="true" className="size-4 text-gold" />
            {formatDuration(playlist.totalDuration)}
          </span>
        </div>

        <div className="mt-8 flex items-center gap-4">
          <CardPlayButton
            label={`${playlist.title} प्लेलिस्ट बजाउनुहोस्`}
            onPlay={() => onPlay(playlist)}
            size="lg"
          />
          <Link
            href={`/playlist/${playlist.slug}`}
            className="inline-flex h-11 items-center rounded-full border border-border bg-background/60 px-5 font-nepali text-sm font-semibold text-foreground backdrop-blur transition-colors hover:border-primary/40 hover:bg-surface focus-visible:outline-2 focus-visible:outline-primary"
          >
            सबै हेर्नुहोस्
          </Link>
        </div>
      </div>
    </article>
  );
}

export function FeaturedHeroCardSkeleton() {
  return (
    <div
      aria-label="विशेष प्रस्तुति लोड हुँदैछ"
      role="status"
      className="flex min-h-[24rem] flex-col justify-end rounded-2xl border border-border/80 bg-surface p-6 sm:min-h-[28rem] sm:p-9 lg:min-h-[30rem] lg:p-12"
    >
      <LoadingSkeleton className="h-3 w-28" />
      <LoadingSkeleton className="mt-5 h-12 w-4/5 max-w-lg" />
      <LoadingSkeleton className="mt-5 h-5 w-full max-w-xl" />
      <LoadingSkeleton className="mt-2 h-5 w-3/4 max-w-md" />
      <div className="mt-8 flex gap-4">
        <LoadingSkeleton className="size-14 rounded-full" />
        <LoadingSkeleton className="h-11 w-28 rounded-full" />
      </div>
    </div>
  );
}
