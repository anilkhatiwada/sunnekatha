"use client";

import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";
import Link from "next/link";

import {
  AuthorCard,
  NarratorCard,
  PlaylistCard,
  TrackCard,
} from "@/components/cards";
import { ExploreCollectionCard } from "@/components/cards/explore-collection-card";
import { FilterChips } from "@/components/common/filter-chips";
import { EmptyState } from "@/components/common/empty-state";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { SectionError } from "@/components/common/section-error";
import { CardRailSkeleton } from "@/components/sections/card-rail-skeleton";
import { HorizontalSection } from "@/components/sections/horizontal-section";
import { Button } from "@/components/ui/button";
import type { ExploreFilter } from "@/features/explore/explore-config";
import { useCatalogPlayback } from "@/features/player/use-catalog-playback";
import {
  getExploreTracks,
  getContentCategories,
  getFeaturedPlaylists,
  getGenres,
  getMoods,
  getPopularAuthors,
  getPopularNarrators,
  queryKeys,
} from "@/services";
import type { ContentType } from "@/types";

interface ExplorePageContentProps {
  activeFilter: ExploreFilter["value"];
  genre?: string;
  mood?: string;
  language?: string;
  premium?: boolean;
  explicit?: boolean;
  ordering?: string;
}

const railCardWidth =
  "w-[10.5rem] shrink-0 snap-start sm:w-[13rem] lg:w-[14rem]";
const personCardWidth =
  "w-[10.5rem] shrink-0 snap-start sm:w-[12rem] lg:w-[13rem]";

export function ExplorePageContent({
  activeFilter,
  genre,
  mood,
  language,
  premium,
  explicit,
  ordering,
}: ExplorePageContentProps) {
  const { playTrack, playPlaylist } = useCatalogPlayback();
  const contentType =
    activeFilter === "all" ? undefined : (activeFilter as ContentType);

  const releasesQuery = useQuery({
    queryKey: queryKeys.explore.releases({
      contentType,
      genre,
      mood,
      language,
      premium,
      explicit,
      ordering,
    }),
    queryFn: () =>
      getExploreTracks({
        contentType,
        genre,
        mood,
        language,
        premium,
        explicit,
        ordering,
      }),
  });
  const moodsQuery = useQuery({
    queryKey: queryKeys.explore.moods(),
    queryFn: getMoods,
  });
  const genresQuery = useQuery({
    queryKey: queryKeys.explore.genres(),
    queryFn: getGenres,
  });
  const categoriesQuery = useQuery({
    queryKey: queryKeys.explore.categories(),
    queryFn: getContentCategories,
  });
  const categoryFilters: ExploreFilter[] = [
    { label: "All", value: "all" },
    ...(categoriesQuery.data ?? []).map((category) => ({
      label: category.name,
      value: category.slug,
    })),
  ];
  const playlistsQuery = useQuery({
    queryKey: queryKeys.explore.featuredPlaylists(),
    queryFn: getFeaturedPlaylists,
  });
  const authorsQuery = useQuery({
    queryKey: queryKeys.explore.popularAuthors(),
    queryFn: getPopularAuthors,
  });
  const narratorsQuery = useQuery({
    queryKey: queryKeys.explore.popularNarrators(),
    queryFn: getPopularNarrators,
  });

  const activeCollection =
    genresQuery.data?.find((item) => item.slug === genre) ??
    moodsQuery.data?.find((item) => item.slug === mood);
  const clearCollectionHref =
    activeFilter === "all"
      ? "/explore"
      : `/explore?type=${activeFilter}`;

  return (
    <div className="space-y-12 pb-8 sm:space-y-16">
      <header className="max-w-3xl pt-2">
        <p className="font-nepali text-sm font-medium text-primary">
          Discover new voices
        </p>
        <h1 className="mt-2 font-literary text-4xl font-semibold sm:text-5xl">
          Explore Nepali literature
        </h1>
        <p className="mt-3 font-nepali text-base leading-7 text-muted-foreground">
          Find your next listen by mood, category, and creator.
        </p>
      </header>

      <FilterChips
        filters={categoryFilters}
        activeFilter={activeFilter}
      />
      <form
        action="/explore"
        className="-mt-6 grid gap-3 rounded-xl border border-border bg-surface/50 p-4 sm:grid-cols-4 sm:items-end sm:gap-4 sm:p-5"
      >
        {activeFilter !== "all" ? (
          <input type="hidden" name="type" value={activeFilter} />
        ) : null}
        {genre ? <input type="hidden" name="genre" value={genre} /> : null}
        {mood ? <input type="hidden" name="mood" value={mood} /> : null}
        <ExploreSelect
          name="language"
          label="Language"
          defaultValue={language ?? ""}
          options={[
            ["", "All Language"],
            ["ne", "Nepali"],
            ["en", "English"],
          ]}
        />
        <ExploreSelect
          name="premium"
          label="Access"
          defaultValue={premium === undefined ? "" : String(premium)}
          options={[
            ["", "All"],
            ["false", "Free"],
            ["true", "Premium"],
          ]}
        />
        <ExploreSelect
          name="ordering"
          label="Sort"
          defaultValue={ordering ?? "-published_at"}
          options={[
            ["-published_at", "Newest first"],
            ["-play_count_cache", "Popular"],
            ["title_ne", "Title"],
            ["duration_seconds", "Shortest first"],
          ]}
        />
        <Button type="submit" variant="secondary" className="h-11 font-nepali">
          Apply filters
        </Button>
        <label className="flex items-center gap-2 font-nepali text-xs text-muted-foreground sm:col-span-4">
          <input
            type="checkbox"
            name="explicit"
            value="false"
            defaultChecked={explicit === false}
          />
          Hide explicit content
        </label>
      </form>
      {(genre || mood) && (
        <div className="-mt-8 flex min-h-8 items-center gap-2 sm:-mt-12">
          <span className="font-nepali text-xs text-muted-foreground">
            Active collection:
          </span>
          {activeCollection ? (
            <Link
              href={clearCollectionHref}
              replace
              scroll={false}
              className="inline-flex items-center gap-1.5 rounded-full border border-primary/40 bg-primary-muted/25 px-3 py-1.5 font-nepali text-xs text-foreground transition-colors hover:bg-primary-muted/40 focus-visible:outline-2 focus-visible:outline-primary"
              aria-label={`${activeCollection.name} — remove filter`}
            >
              {activeCollection.name}
              <X aria-hidden="true" className="size-3.5" />
            </Link>
          ) : (
            <LoadingSkeleton className="h-7 w-20 rounded-full" />
          )}
        </div>
      )}

      <section aria-labelledby="new-releases-heading">
        <SectionHeading
          id="new-releases-heading"
          title="New tracks"
          description={
            genre || mood
              ? "New audio matching this collection"
              : "Recently added audio on SunneKatha"
          }
        />
        {releasesQuery.isPending ? (
          <ResponsiveCardGridSkeleton count={8} />
        ) : releasesQuery.isError ? (
          <SectionError
            onRetry={() => void releasesQuery.refetch()}
            isRetrying={releasesQuery.isFetching}
          />
        ) : releasesQuery.data.length > 0 ? (
          <div className="grid grid-cols-2 gap-x-3 gap-y-7 sm:grid-cols-3 sm:gap-5 lg:grid-cols-4 xl:grid-cols-5">
            {releasesQuery.data.map((track) => (
              <TrackCard
                key={track.id}
                track={track}
                onPlay={(track) => void playTrack(track)}
              />
            ))}
          </div>
        ) : (
          <EmptyState
            compact
            title="No tracks match this selection"
            description="Try another category or mood."
          />
        )}
      </section>

      <section aria-labelledby="moods-heading">
        <SectionHeading
          id="moods-heading"
          title="Listen by mood"
          description="Literature for your current mood"
        />
        {moodsQuery.isPending ? (
          <CollectionGridSkeleton />
        ) : moodsQuery.isError ? (
          <SectionError
            onRetry={() => void moodsQuery.refetch()}
            isRetrying={moodsQuery.isFetching}
          />
        ) : moodsQuery.data.length === 0 ? (
          <EmptyState compact title="No mood collections available" description="New collections will be added soon." />
        ) : (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
            {moodsQuery.data.slice(0, 8).map((item) => (
              <ExploreCollectionCard
                key={item.id}
                collection={item}
                kind="mood"
              />
            ))}
          </div>
        )}
      </section>

      <section aria-labelledby="genres-heading">
        <SectionHeading
          id="genres-heading"
          title="Genres"
          description="Stories, ideas, and imagined worlds"
        />
        {genresQuery.isPending ? (
          <CollectionGridSkeleton />
        ) : genresQuery.isError ? (
          <SectionError
            onRetry={() => void genresQuery.refetch()}
            isRetrying={genresQuery.isFetching}
          />
        ) : genresQuery.data.length === 0 ? (
          <EmptyState compact title="No categories available" description="Category collections will be added soon." />
        ) : (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
            {genresQuery.data.slice(0, 12).map((item) => (
              <ExploreCollectionCard
                key={item.id}
                collection={item}
                kind="genre"
              />
            ))}
          </div>
        )}
      </section>

      <HorizontalSection title="Featured playlists" viewAllHref="/playlists">
        {playlistsQuery.isPending && (
          <CardRailSkeleton variant="playlist" count={5} />
        )}
        {playlistsQuery.isError && (
          <div className="w-full shrink-0">
            <SectionError
              onRetry={() => void playlistsQuery.refetch()}
              isRetrying={playlistsQuery.isFetching}
            />
          </div>
        )}
        {playlistsQuery.isSuccess && playlistsQuery.data.length === 0 && (
          <RailEmpty title="No playlists available" />
        )}
        {playlistsQuery.data?.map((playlist) => (
          <div key={playlist.id} className={railCardWidth}>
            <PlaylistCard
              playlist={playlist}
              onPlay={(selected) => void playPlaylist(selected)}
            />
          </div>
        ))}
      </HorizontalSection>

      <HorizontalSection title="Popular authors">
        {authorsQuery.isPending && (
          <CardRailSkeleton variant="author" count={6} />
        )}
        {authorsQuery.isError && (
          <div className="w-full shrink-0">
            <SectionError
              onRetry={() => void authorsQuery.refetch()}
              isRetrying={authorsQuery.isFetching}
            />
          </div>
        )}
        {authorsQuery.isSuccess && authorsQuery.data.length === 0 && (
          <RailEmpty title="No authors available" />
        )}
        {authorsQuery.data?.map((author) => (
          <div key={author.id} className={personCardWidth}>
            <AuthorCard author={author} onPlay={playTrack} />
          </div>
        ))}
      </HorizontalSection>

      <HorizontalSection title="Popular narrators">
        {narratorsQuery.isPending && (
          <CardRailSkeleton variant="narrator" count={6} />
        )}
        {narratorsQuery.isError && (
          <div className="w-full shrink-0">
            <SectionError
              onRetry={() => void narratorsQuery.refetch()}
              isRetrying={narratorsQuery.isFetching}
            />
          </div>
        )}
        {narratorsQuery.isSuccess && narratorsQuery.data.length === 0 && (
          <RailEmpty title="No narrators available" />
        )}
        {narratorsQuery.data?.map((narrator) => (
          <div key={narrator.id} className={personCardWidth}>
            <NarratorCard narrator={narrator} onPlay={playTrack} />
          </div>
        ))}
      </HorizontalSection>
    </div>
  );
}

function ExploreSelect({
  name,
  label,
  defaultValue,
  options,
}: {
  name: string;
  label: string;
  defaultValue: string;
  options: Array<[string, string]>;
}) {
  return (
    <label className="font-nepali text-xs text-muted-foreground">
      {label}
      <select
        name={name}
        defaultValue={defaultValue}
        className="mt-2 h-11 w-full rounded-lg border border-border bg-background/60 px-3 font-nepali text-sm text-foreground"
      >
        {options.map(([value, text]) => (
          <option key={value} value={value}>
            {text}
          </option>
        ))}
      </select>
    </label>
  );
}

function RailEmpty({ title }: { title: string }) {
  return (
    <div className="w-full min-w-72 shrink-0">
      <EmptyState
        compact
        title={title}
        description="New content will appear here."
      />
    </div>
  );
}

interface SectionHeadingProps {
  id: string;
  title: string;
  description: string;
}

function SectionHeading({ id, title, description }: SectionHeadingProps) {
  return (
    <div className="mb-5">
      <h2 id={id} className="font-literary text-2xl font-semibold sm:text-3xl">
        {title}
      </h2>
      <p className="mt-1 font-nepali text-sm text-muted-foreground">
        {description}
      </p>
    </div>
  );
}

function ResponsiveCardGridSkeleton({ count }: { count: number }) {
  return (
    <div className="grid grid-cols-2 gap-x-3 gap-y-7 sm:grid-cols-3 sm:gap-5 lg:grid-cols-4 xl:grid-cols-5">
      {Array.from({ length: count }, (_, index) => (
        <div key={index} className="space-y-3">
          <LoadingSkeleton className="aspect-square w-full rounded-xl" />
          <LoadingSkeleton className="h-4 w-4/5" />
          <LoadingSkeleton className="h-3 w-3/5" />
        </div>
      ))}
    </div>
  );
}

function CollectionGridSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
      {Array.from({ length: 8 }, (_, index) => (
        <LoadingSkeleton key={index} className="h-32 rounded-xl" />
      ))}
    </div>
  );
}
