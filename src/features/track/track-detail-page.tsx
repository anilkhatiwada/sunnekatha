"use client";

import { useQuery } from "@tanstack/react-query";
import {
  BookOpen,
  Heart,
  ListPlus,
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
import { useLibraryStore } from "@/features/library/library-store";
import { useCatalogPlayback } from "@/features/player/use-catalog-playback";
import { formatDuration } from "@/lib/formatters";
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
  poem: "कविता",
  story: "कथा",
  essay: "निबन्ध",
  novel_chapter: "उपन्यास अध्याय",
  folk_tale: "लोककथा",
  drama: "नाटक",
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
  const favoriteTrackIds = useLibraryStore(
    (state) => state.favoriteTrackIds,
  );
  const toggleFavoriteTrack = useLibraryStore(
    (state) => state.toggleFavoriteTrack,
  );
  const [statusMessage, setStatusMessage] = useState("");

  if (trackQuery.isPending) {
    return <TrackDetailSkeleton />;
  }

  if (trackQuery.isError) {
    return (
      <SectionError
        message="रचना लोड गर्न सकिएन। कृपया फेरि प्रयास गर्नुहोस्।"
        onRetry={() => void trackQuery.refetch()}
        isRetrying={trackQuery.isFetching}
      />
    );
  }

  if (!track) {
    return <TrackNotFound />;
  }

  const isFavorite = favoriteTrackIds.includes(track.id);
  const author = authorQuery.data;
  const narrator = narratorQuery.data;

  return (
    <div className="space-y-14 pb-8">
      <section className="relative overflow-hidden rounded-2xl border border-border bg-surface/75 p-5 sm:p-7 lg:p-10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgb(229_138_82_/_0.2),transparent_36rem)]" />
        <div className="relative grid gap-8 md:grid-cols-[16rem_minmax(0,1fr)] lg:grid-cols-[21rem_minmax(0,1fr)] lg:gap-12">
          <Image
            src={track.coverImage}
            alt={`${track.title} को आवरण`}
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
                वाचन: {track.narrator.name}
              </Link>
              <span aria-hidden="true" className="text-muted-foreground">
                •
              </span>
              <span className="text-muted-foreground">
                {formatDuration(track.duration)}
              </span>
            </div>
            <p className="mt-5 max-w-2xl font-nepali text-sm leading-7 text-muted-foreground sm:text-base">
              {track.description ?? "यस रचनाको विवरण चाँडै उपलब्ध हुनेछ।"}
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
                    ? ` · अध्याय ${track.literaryWork.chapterNumber}`
                    : " सङ्ग्रहको अंश"}
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
                बजाउनुहोस्
              </Button>
              <Button
                type="button"
                variant="secondary"
                aria-pressed={isFavorite}
                onClick={() => toggleFavoriteTrack(track.id)}
                className={cn(
                  "rounded-full font-nepali",
                  isFavorite && "text-primary",
                )}
              >
                <Heart
                  aria-hidden="true"
                  className={cn("size-4", isFavorite && "fill-current")}
                />
                {isFavorite ? "मनपर्ने" : "मनपर्नेमा"}
              </Button>
              <PlaceholderButton
                icon={ListPlus}
                label="प्लेलिस्टमा थप्नुहोस्"
                message="प्लेलिस्टमा थप्ने सुविधा चाँडै उपलब्ध हुनेछ।"
                onMessage={setStatusMessage}
              />
              <PlaceholderButton
                icon={Share2}
                label="साझा"
                message="साझा गर्ने सुविधा चाँडै उपलब्ध हुनेछ।"
                onMessage={setStatusMessage}
              />
            </div>
            <p
              role="status"
              aria-live="polite"
              className="mt-2 min-h-5 font-nepali text-xs text-muted-foreground"
            >
              {statusMessage}
            </p>
          </div>
        </div>
      </section>

      <section
        aria-labelledby="transcript-heading"
        className="rounded-2xl border border-border bg-surface/55 p-5 sm:p-8"
      >
        <p className="text-xs font-semibold tracking-[0.16em] text-primary uppercase">
          सुन्दै पढ्नुहोस्
        </p>
        <h2
          id="transcript-heading"
          className="mt-2 font-literary text-3xl font-semibold"
        >
          लेखोट
        </h2>
        {track.transcript ? (
          <p className="mt-5 max-w-4xl whitespace-pre-line font-nepali text-base leading-9 text-muted-foreground">
            {track.transcript}
          </p>
        ) : (
          <div className="mt-5 rounded-xl border border-dashed border-border px-5 py-8 font-nepali text-sm text-muted-foreground">
            यस रचनाको लेखोट तयार हुँदैछ।
          </div>
        )}
      </section>

      <section
        aria-label="सर्जक र वाचकको जानकारी"
        className="grid gap-4 md:grid-cols-2"
      >
        <PersonInformation
          eyebrow="लेखक"
          name={author?.name ?? track.author.name}
          image={author?.image ?? track.author.image}
          href={`/author/${track.author.slug}`}
          biography={
            authorQuery.isPending
              ? undefined
              : author?.biography ?? "लेखकको परिचय चाँडै उपलब्ध हुनेछ।"
          }
        />
        <PersonInformation
          eyebrow="वाचक"
          name={narrator?.name ?? track.narrator.name}
          image={narrator?.image ?? track.narrator.image}
          href={`/narrator/${track.narrator.slug}`}
          biography={
            narratorQuery.isPending
              ? undefined
              : narrator?.biography ?? "वाचकको परिचय चाँडै उपलब्ध हुनेछ।"
          }
        />
      </section>

      <HorizontalSection title="मिल्दोजुल्दो रचना" eyebrow="अर्को के सुन्ने?">
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

function PlaceholderButton({
  icon: Icon,
  label,
  message,
  onMessage,
}: {
  icon: typeof Share2;
  label: string;
  message: string;
  onMessage: (message: string) => void;
}) {
  return (
    <Button
      type="button"
      variant="ghost"
      onClick={() => onMessage(message)}
      className="rounded-full font-nepali"
    >
      <Icon aria-hidden="true" className="size-4" />
      {label}
    </Button>
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
        alt={`${name} को तस्बिर`}
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
          पूरा परिचय
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
        रचना भेटिएन
      </h1>
      <Link
        href="/explore"
        className="mt-4 inline-flex rounded-full bg-primary px-4 py-2 font-nepali text-sm font-semibold text-background focus-visible:outline-2 focus-visible:outline-primary"
      >
        अन्वेषणमा फर्कनुहोस्
      </Link>
    </div>
  );
}

function TrackDetailSkeleton() {
  return (
    <div aria-label="रचना लोड हुँदैछ" role="status" className="space-y-12">
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
