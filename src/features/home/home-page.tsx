"use client";

import { useQuery } from "@tanstack/react-query";
import { motion, useReducedMotion } from "framer-motion";
import Image from "next/image";
import Link from "next/link";
import { useCallback } from "react";

import {
  AlbumCard,
  AuthorCard,
  ContinueListeningCard,
  FeaturedHeroCard,
  FeaturedHeroCardSkeleton,
  NarratorCard,
  PlaylistCard,
  TrackCard,
} from "@/components/cards";
import { ExploreCollectionCard } from "@/components/cards/explore-collection-card";
import { CardPlayButton } from "@/components/cards/card-primitives";
import { EmptyState } from "@/components/common/empty-state";
import { SearchInput } from "@/components/common/search-input";
import { SectionError } from "@/components/common/section-error";
import { CardRailSkeleton } from "@/components/sections/card-rail-skeleton";
import { HorizontalSection } from "@/components/sections/horizontal-section";
import { usePlayerStore } from "@/features/player/player-store";
import { useCatalogPlayback } from "@/features/player/use-catalog-playback";
import {
  getHomePage,
  getTrackStream,
  mapPlayableTrack,
  queryKeys,
} from "@/services";
import type {
  CatalogPlaylist,
  CatalogTrack,
  HomeHero,
  HomeSection,
  Track,
} from "@/types";

const cardWidth = "w-[10.5rem] shrink-0 snap-start sm:w-[13rem] lg:w-[14rem]";
const personCardWidth =
  "w-[10.5rem] shrink-0 snap-start sm:w-[12rem] lg:w-[13rem]";
const continueCardWidth =
  "w-[19rem] shrink-0 snap-start sm:w-[23rem] lg:w-[25rem]";

export function HomePageContent() {
  const shouldReduceMotion = useReducedMotion();
  const playTrack = usePlayerStore((state) => state.play);
  const { playPlaylist } = useCatalogPlayback();
  const seek = usePlayerStore((state) => state.seek);
  const setLoading = usePlayerStore((state) => state.setLoading);
  const setPlaybackError = usePlayerStore(
    (state) => state.setPlaybackError,
  );
  const homeQuery = useQuery({
    queryKey: queryKeys.home.detail(),
    queryFn: getHomePage,
    staleTime: 60_000,
  });

  const playCatalogTrack = useCallback(
    async (track: CatalogTrack, resumeAt?: number) => {
      if ("audioUrl" in track && typeof track.audioUrl === "string") {
        playTrack(track as Track);
        if (resumeAt && resumeAt > 0) seek(resumeAt);
        return;
      }

      setLoading(true);
      setPlaybackError(null);
      try {
        const stream = await getTrackStream(track.slug);
        playTrack(mapPlayableTrack(stream));
        if (resumeAt && resumeAt > 0) seek(resumeAt);
      } catch {
        setLoading(false);
        setPlaybackError({
          code: "stream-unavailable",
          message: "This track cannot be played right now. Please try again.",
        });
      }
    },
    [playTrack, seek, setLoading, setPlaybackError],
  );

  const handlePlaylistPlay = (playlist: CatalogPlaylist) => {
    void playPlaylist(playlist);
  };

  const hero = homeQuery.data?.hero;

  return (
    <div className="space-y-10 pb-6 sm:space-y-14 lg:space-y-16">
      <motion.header
        initial={shouldReduceMotion ? false : { opacity: 0, y: 10 }}
        animate={shouldReduceMotion ? undefined : { opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="pt-1 sm:pt-2"
      >
        <p className="font-nepali text-sm font-medium text-primary">Good evening</p>
        <h1 className="mt-2 max-w-3xl font-literary text-4xl leading-tight font-semibold text-foreground sm:text-5xl">
          Nepali literature, now in audio
        </h1>
        <p className="mt-4 max-w-2xl font-nepali text-base leading-8 text-muted-foreground sm:text-lg">
          Listen to beloved Nepali stories, poetry, and ideas in one place.
        </p>
        <SearchInput className="mt-6 max-w-2xl" />
      </motion.header>

      <section aria-label="Featured">
        {homeQuery.isPending && <FeaturedHeroCardSkeleton />}
        {homeQuery.isError && (
          <SectionError
            onRetry={() => void homeQuery.refetch()}
            isRetrying={homeQuery.isFetching}
          />
        )}
        {homeQuery.isSuccess && !hero && (
          <EmptyState
            compact
            title="Featured content is coming"
            description="New literary collections will appear here."
          />
        )}
        {hero?.kind === "playlist" && (
          <FeaturedHeroCard
            playlist={hero.content}
            onPlay={handlePlaylistPlay}
          />
        )}
        {hero && hero.kind !== "playlist" && (
          <ContentHeroCard
            hero={hero}
            onPlayTrack={playCatalogTrack}
          />
        )}
      </section>

      {homeQuery.isPending && <HomepageSectionsSkeleton />}
      {homeQuery.data?.sections
        .filter((section) => section.items.length > 0)
        .map((section) => (
          <HomeSectionRail
            key={section.id}
            section={section}
            onPlayTrack={playCatalogTrack}
            onPlayPlaylist={handlePlaylistPlay}
          />
        ))}
    </div>
  );
}

function ContentHeroCard({
  hero,
  onPlayTrack,
}: {
  hero: Exclude<HomeHero, { kind: "playlist" }>;
  onPlayTrack: (track: CatalogTrack) => Promise<void>;
}) {
  const subtitle =
    hero.kind === "track"
      ? hero.content.author.name
      : hero.content.authorName;
  const href =
    hero.kind === "track" ? `/track/${hero.content.slug}` : null;

  return (
    <article className="group relative isolate min-h-[24rem] overflow-hidden rounded-2xl border border-border/80 bg-surface shadow-[0_30px_80px_rgb(0_0_0_/_0.35)] sm:min-h-[28rem] lg:min-h-[30rem]">
      <Image
        src={hero.content.coverImage}
        alt=""
        fill
        preload
        sizes="(max-width: 1024px) 100vw, 1200px"
        className="object-cover transition duration-700 group-hover:scale-[1.02]"
      />
      <div className="absolute inset-0 bg-[linear-gradient(90deg,rgb(11_10_9_/_0.98)_0%,rgb(11_10_9_/_0.82)_44%,rgb(11_10_9_/_0.2)_100%)]" />
      <div className="relative flex min-h-[24rem] max-w-2xl flex-col justify-end p-6 sm:min-h-[28rem] sm:p-9 lg:min-h-[30rem] lg:p-12">
        <p className="text-xs font-semibold tracking-[0.2em] text-primary uppercase">
          Featured
        </p>
        <h2 className="mt-4 font-literary text-4xl leading-tight font-semibold text-foreground sm:text-5xl lg:text-6xl">
          {href ? (
            <Link
              href={href}
              className="rounded-sm focus-visible:outline-2 focus-visible:outline-primary"
            >
              {hero.content.title}
            </Link>
          ) : (
            hero.content.title
          )}
        </h2>
        <p className="mt-5 font-nepali text-base text-muted-foreground sm:text-lg">
          {subtitle}
        </p>
        {hero.kind === "track" && (
          <div className="mt-8">
            <CardPlayButton
              label={`${hero.content.title} — play`}
              onPlay={() => void onPlayTrack(hero.content)}
              size="lg"
            />
          </div>
        )}
      </div>
    </article>
  );
}

function HomeSectionRail({
  section,
  onPlayTrack,
  onPlayPlaylist,
}: {
  section: HomeSection;
  onPlayTrack: (track: CatalogTrack, resumeAt?: number) => Promise<void>;
  onPlayPlaylist: (playlist: CatalogPlaylist) => void;
}) {
  const content = renderSectionItems(section, onPlayTrack, onPlayPlaylist);
  if (!content) return null;

  if (section.layout === "grid") {
    return (
      <section aria-labelledby={`${section.id}-title`}>
        <div className="mb-5 flex items-end justify-between gap-4 sm:mb-7">
          <div className="min-w-0">
            <h2
              id={`${section.id}-title`}
              className="font-literary text-2xl font-semibold text-foreground sm:text-3xl"
            >
              {section.title}
            </h2>
            {section.subtitle && (
              <p className="mt-2 max-w-2xl font-nepali leading-7 text-muted-foreground">
                {section.subtitle}
              </p>
            )}
          </div>
          {section.viewAllHref && (
            <Link
              href={section.viewAllHref}
              className="inline-flex min-h-11 shrink-0 items-center rounded-sm font-nepali text-sm font-semibold text-primary transition-colors hover:text-primary/80 focus-visible:outline-2 focus-visible:outline-primary"
            >
              View all
            </Link>
          )}
        </div>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
          {content}
        </div>
      </section>
    );
  }

  return (
    <HorizontalSection
      title={section.title}
      description={section.subtitle}
      viewAllHref={section.viewAllHref}
    >
      {content}
    </HorizontalSection>
  );
}

function renderSectionItems(
  section: HomeSection,
  onPlayTrack: (track: CatalogTrack, resumeAt?: number) => Promise<void>,
  onPlayPlaylist: (playlist: CatalogPlaylist) => void,
) {
  const standardItemClass = section.layout === "grid" ? "min-w-0" : cardWidth;
  const personItemClass =
    section.layout === "grid" ? "min-w-0" : personCardWidth;
  const continueItemClass =
    section.layout === "grid"
      ? "col-span-2 min-w-0 sm:col-span-3 lg:col-span-2"
      : continueCardWidth;

  if (section.kind === "continue-listening") {
    return section.items.map((item) => (
      <div key={item.track.id} className={continueItemClass}>
        <ContinueListeningCard
          item={item}
          onPlay={(track) =>
            void onPlayTrack(track, item.progress.progressSeconds)
          }
        />
      </div>
    ));
  }
  if (section.kind === "tracks") {
    return section.items.map((track) => (
      <div key={track.id} className={standardItemClass}>
        <TrackCard
          track={track}
          onPlay={(selected) => void onPlayTrack(selected)}
        />
      </div>
    ));
  }
  if (section.kind === "playlists") {
    return section.items.map((playlist) => (
      <div key={playlist.id} className={standardItemClass}>
        <PlaylistCard playlist={playlist} onPlay={onPlayPlaylist} />
      </div>
    ));
  }
  if (section.kind === "authors") {
    return section.items.map((author) => (
      <div key={author.id} className={personItemClass}>
        <AuthorCard author={author} onPlay={() => undefined} />
      </div>
    ));
  }
  if (section.kind === "narrators") {
    return section.items.map((narrator) => (
      <div key={narrator.id} className={personItemClass}>
        <NarratorCard narrator={narrator} onPlay={() => undefined} />
      </div>
    ));
  }
  if (section.kind === "moods" || section.kind === "genres") {
    return section.items.map((collection) => (
      <div key={collection.id} className={standardItemClass}>
        <ExploreCollectionCard
          collection={collection}
          kind={section.kind === "moods" ? "mood" : "genre"}
        />
      </div>
    ));
  }
  if (section.kind === "categories") {
    return section.items.slice(0, 6).map((collection, index) => (
      <div
        key={collection.id}
        className={`${standardItemClass} ${index >= 4 ? "hidden sm:block" : ""}`}
      >
        <ExploreCollectionCard collection={collection} kind="category" />
      </div>
    ));
  }
  if (section.kind === "albums") {
    return section.items.map((album) => (
      <div key={album.id} className={standardItemClass}>
        <AlbumCard album={album} />
      </div>
    ));
  }
  return null;
}

function HomepageSectionsSkeleton() {
  return (
    <>
      <HorizontalSection title="Loading content">
        <CardRailSkeleton variant="track" count={6} />
      </HorizontalSection>
      <HorizontalSection title="Loading collection">
        <CardRailSkeleton variant="playlist" count={5} />
      </HorizontalSection>
    </>
  );
}
