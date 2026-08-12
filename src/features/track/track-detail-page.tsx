"use client";

import { useQuery } from "@tanstack/react-query";
import {
  BookOpen,
  Heart,
  Play,
  Share2,
  UserRound,
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";

import { TrackCard, TrackCardSkeleton } from "@/components/cards/track-card";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { SectionError } from "@/components/common/section-error";
import { HorizontalSection } from "@/components/sections/horizontal-section";
import { Button } from "@/components/ui/button";
import { useLibraryRelationship } from "@/features/library/use-library-relationship";
import { useCatalogPlayback } from "@/features/player/use-catalog-playback";
import { AddToPlaylistControl } from "@/features/playlist/add-to-playlist-control";
import { formatDuration } from "@/lib/formatters";
import { sharePage } from "@/lib/share";
import { cn } from "@/lib/utils";
import {
  getAuthorBySlug,
  getNarratorBySlug,
  getSimilarTracks,
  getTrackBySlug,
  queryKeys,
} from "@/services";
import type { ContentType } from "@/types";

const CONTENT_TYPE_LABELS: Record<ContentType, string> = {
  poem: "Poetry",
  story: "Story",
  essay: "Essay",
  novel_chapter: "Novel Chapter",
  folk_tale: "Folk Tale",
  drama: "Drama",
};

interface TrackDetailPageContentProps {
  slug: string;
}

export function TrackDetailPageContent({
  slug,
}: TrackDetailPageContentProps) {
  const trackQuery = useQuery({
    queryKey: queryKeys.tracks.detail(slug),
    queryFn: () => getTrackBySlug(slug),
  });
  const track = trackQuery.data;
  const authorQuery = useQuery({
    queryKey: queryKeys.authors.detail(track?.author.slug ?? ""),
    queryFn: () => getAuthorBySlug(track!.author.slug),
    enabled: Boolean(track),
  });
  const narratorQuery = useQuery({
    queryKey: queryKeys.narrators.detail(track?.narrator.slug ?? ""),
    queryFn: () => getNarratorBySlug(track!.narrator.slug),
    enabled: Boolean(track),
  });
  const similarQuery = useQuery({
    queryKey: queryKeys.tracks.similar(track?.slug),
    queryFn: () => getSimilarTracks(track!.slug),
    enabled: Boolean(track),
  });
  const { playTrack } = useCatalogPlayback();
  const favorite = useLibraryRelationship("favoriteTrack", track?.id);
  const [statusMessage, setStatusMessage] = useState("");

  if (trackQuery.isPending) {
    return <TrackDetailSkeleton />;
  }

  if (trackQuery.isError) {
    return (
      <SectionError
        message="The track could not be loaded. Please try again."
        onRetry={() => void trackQuery.refetch()}
        isRetrying={trackQuery.isFetching}
      />
    );
  }

  if (!track) {
    return <TrackNotFound />;
  }

  const isFavorite = favorite.isActive;
  const author = authorQuery.data;
  const narrator = narratorQuery.data;

  return (
    <div className="space-y-14 pb-8">
      <section className="relative overflow-hidden rounded-2xl border border-border bg-surface/75 p-5 sm:p-7 lg:p-10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgb(229_138_82_/_0.2),transparent_36rem)]" />
        <div className="relative grid gap-8 md:grid-cols-[16rem_minmax(0,1fr)] lg:grid-cols-[21rem_minmax(0,1fr)] lg:gap-12">
          <Image
            src={track.coverImage}
            alt={`${track.title} cover`}
            width={720}
            height={720}
            preload
            className="aspect-square w-full max-w-sm rounded-xl object-cover shadow-[0_30px_80px_rgb(0_0_0_/_0.5)] ring-1 ring-white/10"
          />

          <div className="flex min-w-0 flex-col justify-end">
            <p className="font-nepali text-xs font-semibold tracking-wide text-primary">
              {CONTENT_TYPE_LABELS[track.contentType]}
            </p>
            <h1 className="mt-2 font-literary text-4xl leading-tight font-semibold sm:text-5xl lg:text-6xl">
              {track.title}
            </h1>
            {track.subtitle && (
              <p className="mt-2 font-nepali text-base text-muted-foreground">
                {track.subtitle}
              </p>
            )}
            <div className="mt-5 flex flex-wrap gap-x-2 gap-y-1 font-nepali text-sm">
              <Link
                href={`/author/${track.author.slug}`}
                className="font-semibold text-foreground hover:text-primary focus-visible:outline-2 focus-visible:outline-primary"
              >
                {track.author.name}
              </Link>
              <span aria-hidden="true" className="text-muted-foreground">
                •
              </span>
              <Link
                href={`/narrator/${track.narrator.slug}`}
                className="text-muted-foreground hover:text-primary focus-visible:outline-2 focus-visible:outline-primary"
              >
                Narrated by: {track.narrator.name}
              </Link>
              <span aria-hidden="true" className="text-muted-foreground">
                •
              </span>
              <span className="text-muted-foreground">
                {formatDuration(track.duration)}
              </span>
            </div>
            <p className="mt-5 max-w-2xl font-nepali text-sm leading-7 text-muted-foreground sm:text-base">
              {track.description ?? "A description will be available soon."}
            </p>

            {track.literaryWork && (
              <div className="mt-5 flex max-w-xl items-center gap-3 rounded-xl border border-gold/20 bg-gold/5 px-4 py-3">
                <BookOpen
                  aria-hidden="true"
                  className="size-5 shrink-0 text-gold"
                />
                <p className="font-nepali text-sm text-muted-foreground">
                  <span className="text-foreground">
                    {track.literaryWork.title}
                  </span>
                  {track.literaryWork.chapterNumber
                    ? ` · Chapter ${track.literaryWork.chapterNumber}`
                    : " collection"}
                </p>
              </div>
            )}

            <div className="mt-7 flex flex-wrap items-center gap-2">
              <Button
                type="button"
                size="lg"
                onClick={() => void playTrack(track)}
                className="rounded-full px-6 font-nepali"
              >
                <Play aria-hidden="true" className="size-5 fill-current" />
                — play
              </Button>
              <Button
                type="button"
                variant="secondary"
                aria-pressed={isFavorite}
                disabled={favorite.isPending}
                onClick={() => {
                  if (!favorite.toggle()) {
                    setStatusMessage(
                      "Sign in to add this track to your favorites.",
                    );
                  }
                }}
                className={cn(
                  "rounded-full font-nepali",
                  isFavorite && "text-primary",
                )}
              >
                <Heart
                  aria-hidden="true"
                  className={cn("size-4", isFavorite && "fill-current")}
                />
                {isFavorite ? "Favorite" : "Add to favorites"}
              </Button>
              <AddToPlaylistControl
                trackId={track.id}
                onMessage={setStatusMessage}
              />
              <Button
                type="button"
                variant="ghost"
                className="rounded-full font-nepali"
                onClick={() => {
                  void sharePage({
                    title: track.title,
                    text: `${track.title} · SunneKatha`,
                  })
                    .then((result) =>
                      setStatusMessage(
                        result === "copied"
                          ? "Track link copied."
                          : "Track shared.",
                      ),
                    )
                    .catch(() => undefined);
                }}
              >
                <Share2 aria-hidden="true" className="size-4" />
                Share
              </Button>
            </div>
            <p
              role="status"
              aria-live="polite"
              className="mt-2 min-h-5 font-nepali text-xs text-muted-foreground"
            >
              {statusMessage}
              {favorite.error
                ? "Your favorite could not be saved. Please try again."
                : null}
            </p>
          </div>
        </div>
      </section>

      <section
        aria-labelledby="transcript-heading"
        className="rounded-2xl border border-border bg-surface/55 p-5 sm:p-8"
      >
        <p className="text-xs font-semibold tracking-[0.16em] text-primary uppercase">
          Read along
        </p>
        <h2
          id="transcript-heading"
          className="mt-2 font-literary text-3xl font-semibold"
        >
          Transcript
        </h2>
        {track.transcript ? (
          <p className="mt-5 max-w-4xl whitespace-pre-line font-nepali text-base leading-9 text-muted-foreground">
            {track.transcript}
          </p>
        ) : (
          <div className="mt-5 rounded-xl border border-dashed border-border px-5 py-8 font-nepali text-sm text-muted-foreground">
            A transcript is being prepared for this track.
          </div>
        )}
      </section>

      <section
        aria-label="Author and narrator information"
        className="grid gap-4 md:grid-cols-2"
      >
        <PersonInformation
          eyebrow="Author"
          name={author?.name ?? track.author.name}
          image={author?.image ?? track.author.image}
          href={`/author/${track.author.slug}`}
          biography={
            authorQuery.isPending
              ? undefined
              : author?.biography ?? "The author biography will be available soon."
          }
        />
        <PersonInformation
          eyebrow="Narrator"
          name={narrator?.name ?? track.narrator.name}
          image={narrator?.image ?? track.narrator.image}
          href={`/narrator/${track.narrator.slug}`}
          biography={
            narratorQuery.isPending
              ? undefined
              : narrator?.biography ?? "The narrator biography will be available soon."
          }
        />
      </section>

      <HorizontalSection title="Related tracks" eyebrow="What should you listen to next?">
        {similarQuery.isPending
          ? Array.from({ length: 5 }, (_, index) => (
              <div
                key={index}
                className="w-[70vw] max-w-56 shrink-0 snap-start sm:w-52"
              >
                <TrackCardSkeleton />
              </div>
            ))
          : similarQuery.data?.map((similarTrack) => (
              <div
                key={similarTrack.id}
                className="w-[70vw] max-w-56 shrink-0 snap-start sm:w-52"
              >
                <TrackCard
                  track={similarTrack}
                  onPlay={(selectedTrack) => void playTrack(selectedTrack)}
                />
              </div>
            ))}
      </HorizontalSection>
    </div>
  );
}

function PersonInformation({
  eyebrow,
  name,
  image,
  href,
  biography,
}: {
  eyebrow: string;
  name: string;
  image: string;
  href: string;
  biography?: string;
}) {
  return (
    <article className="flex gap-4 rounded-2xl border border-border bg-surface/55 p-5 sm:p-6">
      <Image
        src={image}
        alt={`${name} photo`}
        width={96}
        height={96}
        className="size-20 shrink-0 rounded-full object-cover ring-1 ring-white/10 sm:size-24"
      />
      <div className="min-w-0">
        <p className="font-nepali text-xs font-semibold text-primary">
          {eyebrow}
        </p>
        <h2 className="mt-1 font-literary text-xl font-semibold">{name}</h2>
        {biography ? (
          <p className="mt-2 line-clamp-3 font-nepali text-sm leading-6 text-muted-foreground">
            {biography}
          </p>
        ) : (
          <LoadingSkeleton className="mt-3 h-12 w-full" />
        )}
        <Link
          href={href}
          className="mt-3 inline-flex items-center gap-1 rounded-sm font-nepali text-xs font-semibold text-primary hover:text-primary/80 focus-visible:outline-2 focus-visible:outline-primary"
        >
          <UserRound aria-hidden="true" className="size-3.5" />
          Full biography
        </Link>
      </div>
    </article>
  );
}

function TrackNotFound() {
  return (
    <div className="rounded-2xl border border-dashed border-border bg-surface/45 px-6 py-16 text-center">
      <BookOpen aria-hidden="true" className="mx-auto size-8 text-primary" />
      <h1 className="mt-4 font-literary text-2xl font-semibold">
        Track not found
      </h1>
      <Link
        href="/explore"
        className="mt-4 inline-flex rounded-full bg-primary px-4 py-2 font-nepali text-sm font-semibold text-background focus-visible:outline-2 focus-visible:outline-primary"
      >
        Back to Explore
      </Link>
    </div>
  );
}

function TrackDetailSkeleton() {
  return (
    <div aria-label="Loading track" role="status" className="space-y-12">
      <div className="grid gap-8 rounded-2xl border border-border bg-surface/55 p-5 md:grid-cols-[16rem_minmax(0,1fr)] lg:p-10">
        <LoadingSkeleton className="aspect-square w-full rounded-xl" />
        <div className="flex flex-col justify-end">
          <LoadingSkeleton className="h-4 w-20" />
          <LoadingSkeleton className="mt-4 h-14 w-4/5" />
          <LoadingSkeleton className="mt-5 h-5 w-2/5" />
          <LoadingSkeleton className="mt-5 h-20 w-full max-w-2xl" />
          <LoadingSkeleton className="mt-7 h-12 w-72 rounded-full" />
        </div>
      </div>
      <LoadingSkeleton className="h-56 rounded-2xl" />
    </div>
  );
}
