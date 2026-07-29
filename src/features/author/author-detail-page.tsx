"use client";

import { useQuery } from "@tanstack/react-query";
import { BookOpen, CalendarDays, Play, UserPlus } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import {
  AuthorCard,
  AuthorCardSkeleton,
} from "@/components/cards/author-card";
import {
  PlaylistCard,
  PlaylistCardSkeleton,
} from "@/components/cards/playlist-card";
import { TrackCard, TrackCardSkeleton } from "@/components/cards/track-card";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { SectionError } from "@/components/common/section-error";
import { HorizontalSection } from "@/components/sections/horizontal-section";
import { Button } from "@/components/ui/button";
import { useLibraryStore } from "@/features/library/library-store";
import { useCatalogPlayback } from "@/features/player/use-catalog-playback";
import { cn } from "@/lib/utils";
import {
  getAuthorBySlug,
  getAuthorFeaturedCollections,
  getAuthorTracks,
  getRelatedAuthors,
  queryKeys,
} from "@/services";
import type { CatalogPlaylist } from "@/types";

interface AuthorDetailPageContentProps {
  slug: string;
}

export function AuthorDetailPageContent({
  slug,
}: AuthorDetailPageContentProps) {
  const authorQuery = useQuery({
    queryKey: queryKeys.authors.detail(slug),
    queryFn: () => getAuthorBySlug(slug),
  });
  const author = authorQuery.data;
  const tracksQuery = useQuery({
    queryKey: queryKeys.authors.tracks(author?.id),
    queryFn: () => getAuthorTracks(author!.slug),
    enabled: Boolean(author),
  });
  const collectionsQuery = useQuery({
    queryKey: queryKeys.authors.collections(author?.id),
    queryFn: () => getAuthorFeaturedCollections(author!.slug),
    enabled: Boolean(author),
  });
  const relatedAuthorsQuery = useQuery({
    queryKey: queryKeys.authors.related(author?.id),
    queryFn: () => getRelatedAuthors(author!.id),
    enabled: Boolean(author),
  });
  const { playTrack, playCollection } = useCatalogPlayback();
  const followedAuthorIds = useLibraryStore(
    (state) => state.followedAuthorIds,
  );
  const toggleFollowedAuthor = useLibraryStore(
    (state) => state.toggleFollowedAuthor,
  );

  if (authorQuery.isPending) {
    return <AuthorDetailSkeleton />;
  }

  if (authorQuery.isError) {
    return (
      <SectionError
        message="लेखकको परिचय लोड गर्न सकिएन। कृपया फेरि प्रयास गर्नुहोस्।"
        onRetry={() => void authorQuery.refetch()}
        isRetrying={authorQuery.isFetching}
      />
    );
  }

  if (!author) {
    return <AuthorNotFound />;
  }

  const isFollowing = followedAuthorIds.includes(author.id);
  const allTracks = tracksQuery.data ?? [];
  const popularTracks =
    author.popularTracks.length > 0 ? author.popularTracks : allTracks.slice(0, 5);
  const playPlaylist = (playlist: CatalogPlaylist) =>
    void playCollection(playlist.tracks);

  return (
    <div className="space-y-14 pb-8">
      <section className="relative overflow-hidden rounded-2xl border border-border bg-surface/75 p-5 sm:p-8 lg:p-10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgb(229_138_82_/_0.2),transparent_38rem)]" />
        <div className="relative grid items-end gap-8 md:grid-cols-[16rem_minmax(0,1fr)] lg:grid-cols-[20rem_minmax(0,1fr)] lg:gap-12">
          <Image
            src={author.image}
            alt={`${author.name} को तस्बिर`}
            width={720}
            height={720}
            preload
            className="aspect-square w-full max-w-sm rounded-2xl object-cover shadow-[0_30px_80px_rgb(0_0_0_/_0.5)] ring-1 ring-white/10"
          />

          <div className="min-w-0">
            <p className="font-nepali text-xs font-semibold tracking-wide text-primary">
              लेखक परिचय
            </p>
            <h1 className="mt-2 font-literary text-4xl leading-tight font-semibold sm:text-5xl lg:text-6xl">
              {author.name}
            </h1>
            {author.nameEnglish && (
              <p className="mt-2 text-base text-muted-foreground sm:text-lg">
                {author.nameEnglish}
              </p>
            )}
            <p className="mt-5 max-w-3xl font-nepali text-sm leading-7 text-muted-foreground sm:text-base">
              {author.biography}
            </p>

            <div className="mt-5 flex flex-wrap items-center gap-x-4 gap-y-3 font-nepali text-sm text-muted-foreground">
              {(author.birthYear || author.deathYear) && (
                <span className="inline-flex items-center gap-2">
                  <CalendarDays
                    aria-hidden="true"
                    className="size-4 text-primary"
                  />
                  {formatLifeYears(author.birthYear, author.deathYear)}
                </span>
              )}
              <span>
                {allTracks.length || author.popularTracks.length} श्रव्य रचना
              </span>
            </div>

            <div className="mt-5 flex flex-wrap gap-2">
              {author.genres.map((genre) => (
                <span
                  key={genre}
                  className="rounded-full border border-border bg-background/35 px-3 py-1.5 text-xs text-muted-foreground"
                >
                  {genre}
                </span>
              ))}
            </div>

            <div className="mt-7 flex flex-wrap gap-2">
              <Button
                type="button"
                size="lg"
                disabled={popularTracks.length === 0}
                onClick={() => void playCollection(popularTracks)}
                className="rounded-full px-6 font-nepali"
              >
                <Play aria-hidden="true" className="size-5 fill-current" />
                लोकप्रिय रचना बजाउनुहोस्
              </Button>
              <Button
                type="button"
                variant="secondary"
                aria-pressed={isFollowing}
                onClick={() => toggleFollowedAuthor(author.id)}
                className={cn(
                  "rounded-full font-nepali",
                  isFollowing && "border-primary/40 text-primary",
                )}
              >
                <UserPlus
                  aria-hidden="true"
                  className={cn("size-4", isFollowing && "fill-current")}
                />
                {isFollowing ? "फलो गर्दै" : "फलो गर्नुहोस्"}
              </Button>
            </div>
          </div>
        </div>
      </section>

      <HorizontalSection title="लोकप्रिय रचना" eyebrow="धेरै सुनिएका">
        {popularTracks.map((track) => (
          <CardWidth key={track.id}>
            <TrackCard track={track} onPlay={(item) => void playTrack(item)} />
          </CardWidth>
        ))}
      </HorizontalSection>

      <section aria-labelledby="all-author-tracks">
        <div className="mb-5 flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold tracking-[0.16em] text-primary uppercase">
              पूर्ण सूची
            </p>
            <h2
              id="all-author-tracks"
              className="mt-1 font-literary text-2xl font-semibold sm:text-3xl"
            >
              सबै श्रव्य रचना
            </h2>
          </div>
          {!tracksQuery.isPending && (
            <span className="font-nepali text-xs text-muted-foreground">
              {allTracks.length} रचना
            </span>
          )}
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
          {tracksQuery.isPending
            ? Array.from({ length: 5 }, (_, index) => (
                <TrackCardSkeleton key={index} />
              ))
            : allTracks.map((track) => (
                <TrackCard
                  key={track.id}
                  track={track}
                  onPlay={(item) => void playTrack(item)}
                />
              ))}
        </div>
      </section>

      {(collectionsQuery.isPending ||
        Boolean(collectionsQuery.data?.length)) && (
        <HorizontalSection
          title="विशेष सङ्ग्रह"
          eyebrow="यी रचना समेटिएका"
        >
          {collectionsQuery.isPending
            ? Array.from({ length: 4 }, (_, index) => (
                <CardWidth key={index}>
                  <PlaylistCardSkeleton />
                </CardWidth>
              ))
            : collectionsQuery.data?.map((playlist) => (
                <CardWidth key={playlist.id}>
                  <PlaylistCard
                    playlist={playlist}
                    onPlay={playPlaylist}
                  />
                </CardWidth>
              ))}
        </HorizontalSection>
      )}

      {(relatedAuthorsQuery.isPending ||
        Boolean(relatedAuthorsQuery.data?.length)) && (
        <HorizontalSection title="सम्बन्धित लेखक" eyebrow="अर्को परिचय">
          {relatedAuthorsQuery.isPending
            ? Array.from({ length: 4 }, (_, index) => (
                <CardWidth key={index}>
                  <AuthorCardSkeleton />
                </CardWidth>
              ))
            : relatedAuthorsQuery.data?.map((relatedAuthor) => (
                <CardWidth key={relatedAuthor.id}>
                  <AuthorCard
                    author={relatedAuthor}
                    onPlay={playTrack}
                  />
                </CardWidth>
              ))}
        </HorizontalSection>
      )}
    </div>
  );
}

function CardWidth({ children }: { children: React.ReactNode }) {
  return (
    <div className="w-[70vw] max-w-56 shrink-0 snap-start sm:w-52">
      {children}
    </div>
  );
}

function formatLifeYears(birthYear?: number, deathYear?: number) {
  if (birthYear && deathYear) {
    return `${birthYear}–${deathYear}`;
  }

  if (birthYear) {
    return `जन्म ${birthYear}`;
  }

  return `निधन ${deathYear}`;
}

function AuthorNotFound() {
  return (
    <div className="rounded-2xl border border-dashed border-border bg-surface/45 px-6 py-16 text-center">
      <BookOpen aria-hidden="true" className="mx-auto size-8 text-primary" />
      <h1 className="mt-4 font-literary text-2xl font-semibold">
        लेखक भेटिएन
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

function AuthorDetailSkeleton() {
  return (
    <div aria-label="लेखक लोड हुँदैछ" role="status" className="space-y-12">
      <div className="grid gap-8 rounded-2xl border border-border bg-surface/55 p-5 md:grid-cols-[16rem_minmax(0,1fr)] lg:p-10">
        <LoadingSkeleton className="aspect-square w-full rounded-2xl" />
        <div className="flex flex-col justify-end">
          <LoadingSkeleton className="h-4 w-24" />
          <LoadingSkeleton className="mt-4 h-14 w-3/5" />
          <LoadingSkeleton className="mt-3 h-5 w-2/5" />
          <LoadingSkeleton className="mt-6 h-20 w-full max-w-3xl" />
          <LoadingSkeleton className="mt-7 h-12 w-72 rounded-full" />
        </div>
      </div>
      <LoadingSkeleton className="h-72 rounded-2xl" />
    </div>
  );
}
