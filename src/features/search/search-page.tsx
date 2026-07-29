"use client";

import { useQuery } from "@tanstack/react-query";
import { Clock3, Search, TrendingUp, X } from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";

import {
  AuthorCard,
  NarratorCard,
  PlaylistCard,
  TrackCard,
} from "@/components/cards";
import { ExploreCollectionCard } from "@/components/cards/explore-collection-card";
import { EmptyState } from "@/components/common/empty-state";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { SectionError } from "@/components/common/section-error";
import { Button } from "@/components/ui/button";
import { SEARCH_FILTERS } from "@/features/search/search-config";
import { useSearchHistoryStore } from "@/features/search/search-history-store";
import { useDebouncedValue } from "@/features/search/use-debounced-value";
import { usePlayerStore } from "@/features/player/player-store";
import { getTrendingSearches, queryKeys, searchContent } from "@/services";
import type {
  Playlist,
  SearchResults,
  SearchResultType,
} from "@/types";

interface SearchPageContentProps {
  initialQuery: string;
}

const SEARCH_DEBOUNCE_MS = 350;

export function SearchPageContent({
  initialQuery,
}: SearchPageContentProps) {
  const [query, setQuery] = useState(initialQuery);
  const [activeFilter, setActiveFilter] =
    useState<SearchResultType>("all");
  const debouncedQuery = useDebouncedValue(query.trim(), SEARCH_DEBOUNCE_MS);
  const searches = useSearchHistoryStore((state) => state.searches);
  const addSearch = useSearchHistoryStore((state) => state.addSearch);
  const clearHistory = useSearchHistoryStore((state) => state.clearHistory);
  const playTrack = usePlayerStore((state) => state.play);
  const replaceQueue = usePlayerStore((state) => state.replaceQueue);

  const resultsQuery = useQuery({
    queryKey: queryKeys.search.results(debouncedQuery, activeFilter),
    queryFn: () =>
      searchContent({
        query: debouncedQuery,
        resultType: activeFilter,
      }),
    enabled: debouncedQuery.length > 0,
  });
  const trendingQuery = useQuery({
    queryKey: queryKeys.search.trending(),
    queryFn: getTrendingSearches,
  });

  useEffect(() => {
    const searchParams = new URLSearchParams(window.location.search);
    if (debouncedQuery) {
      searchParams.set("q", debouncedQuery);
    } else {
      searchParams.delete("q");
    }
    const queryString = searchParams.toString();
    window.history.replaceState(
      window.history.state,
      "",
      queryString ? `/search?${queryString}` : "/search",
    );
  }, [debouncedQuery]);

  useEffect(() => {
    if (debouncedQuery && resultsQuery.isSuccess) {
      addSearch(debouncedQuery);
    }
  }, [addSearch, debouncedQuery, resultsQuery.isSuccess]);

  const chooseSearch = (value: string) => {
    setQuery(value);
    addSearch(value);
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    addSearch(query);
  };

  const playPlaylist = (playlist: Playlist) =>
    replaceQueue(playlist.tracks);
  const hasQuery = debouncedQuery.length > 0;
  const resultCount = resultsQuery.data
    ? countSearchResults(resultsQuery.data)
    : 0;

  return (
    <div className="space-y-9 pb-8">
      <header className="max-w-3xl pt-2">
        <p className="font-nepali text-sm font-medium text-primary">खोज</p>
        <h1 className="mt-2 font-literary text-4xl font-semibold sm:text-5xl">
          मनपर्ने आवाज खोज्नुहोस्
        </h1>
        <p className="mt-3 font-nepali text-base leading-7 text-muted-foreground">
          नेपाली वा Romanized शब्दमा रचना, सर्जक, वाचक र सङ्ग्रह खोज्नुहोस्।
        </p>
      </header>

      <form
        role="search"
        onSubmit={handleSubmit}
        className="relative max-w-4xl"
      >
        <label htmlFor="catalog-search" className="sr-only">
          SunneKatha मा खोज्नुहोस्
        </label>
        <Search
          aria-hidden="true"
          className="pointer-events-none absolute top-1/2 left-4 size-5 -translate-y-1/2 text-muted-foreground"
        />
        <input
          id="catalog-search"
          type="search"
          value={query}
          autoComplete="off"
          onChange={(event) => setQuery(event.target.value)}
          placeholder="उदाहरण: वर्षाको साँझ वा barshako saanjh"
          className="h-14 w-full rounded-xl border border-border bg-surface/90 pr-12 pl-12 font-nepali text-base text-foreground shadow-lg shadow-black/10 transition-colors placeholder:text-muted-foreground/70 hover:border-primary/30 focus:border-primary/60 focus:outline-2 focus:outline-primary sm:h-16"
        />
        {query ? (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={() => setQuery("")}
            aria-label="खोज खाली गर्नुहोस्"
            className="absolute top-1/2 right-2 size-11 -translate-y-1/2 rounded-full"
          >
            <X aria-hidden="true" className="size-4" />
          </Button>
        ) : null}
      </form>

      {hasQuery ? (
        <>
          <nav aria-label="खोज परिणाम प्रकार">
            <ul className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-2 [scrollbar-width:none] sm:mx-0 sm:flex-wrap sm:px-0 [&::-webkit-scrollbar]:hidden">
              {SEARCH_FILTERS.map((filter) => (
                <li key={filter.value} className="shrink-0">
                  <button
                    type="button"
                    onClick={() => setActiveFilter(filter.value)}
                    aria-pressed={activeFilter === filter.value}
                    className={
                      activeFilter === filter.value
                        ? "h-9 rounded-full border border-primary bg-primary px-4 font-nepali text-sm font-medium text-background focus-visible:outline-2 focus-visible:outline-primary"
                        : "h-9 rounded-full border border-border bg-surface px-4 font-nepali text-sm text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground focus-visible:outline-2 focus-visible:outline-primary"
                    }
                  >
                    {filter.label}
                  </button>
                </li>
              ))}
            </ul>
          </nav>

          <section aria-live="polite" aria-busy={resultsQuery.isPending}>
            {resultsQuery.isPending ? (
              <SearchResultsSkeleton />
            ) : resultsQuery.isError ? (
              <SectionError
                message="खोज परिणाम ल्याउन सकिएन।"
                onRetry={() => void resultsQuery.refetch()}
                isRetrying={resultsQuery.isFetching}
              />
            ) : resultCount === 0 ? (
              <SearchEmptyState query={debouncedQuery} />
            ) : resultsQuery.data ? (
              <GroupedSearchResults
                results={resultsQuery.data}
                onTrackPlay={playTrack}
                onPlaylistPlay={playPlaylist}
              />
            ) : null}
          </section>
        </>
      ) : (
        <div className="grid gap-8 lg:grid-cols-2">
          <SearchSuggestions
            icon={Clock3}
            title="हालै खोजिएका"
            items={searches}
            emptyText="तपाईंले खोजेका शब्दहरू यहाँ सुरक्षित हुन्छन्।"
            onSelect={chooseSearch}
            action={
              searches.length > 0 ? (
                <button
                  type="button"
                  onClick={clearHistory}
                  className="font-nepali text-xs text-muted-foreground hover:text-destructive focus-visible:outline-2 focus-visible:outline-primary"
                >
                  इतिहास हटाउनुहोस्
                </button>
              ) : null
            }
          />
          {trendingQuery.isPending ? (
            <LoadingSkeleton className="h-48 rounded-xl" />
          ) : trendingQuery.isError ? (
            <SectionError
              onRetry={() => void trendingQuery.refetch()}
              isRetrying={trendingQuery.isFetching}
            />
          ) : (
            <SearchSuggestions
              icon={TrendingUp}
              title="अहिले लोकप्रिय खोज"
              items={trendingQuery.data}
              emptyText="लोकप्रिय खोज उपलब्ध छैन।"
              onSelect={chooseSearch}
            />
          )}
        </div>
      )}
    </div>
  );
}

interface GroupedSearchResultsProps {
  results: SearchResults;
  onTrackPlay: ReturnType<typeof usePlayerStore.getState>["play"];
  onPlaylistPlay: (playlist: Playlist) => void;
}

function GroupedSearchResults({
  results,
  onTrackPlay,
  onPlaylistPlay,
}: GroupedSearchResultsProps) {
  return (
    <div className="space-y-12">
      {results.tracks.length > 0 && (
        <ResultGroup title="रचनाहरू" count={results.tracks.length}>
          <div className="grid grid-cols-2 gap-x-3 gap-y-7 sm:grid-cols-3 sm:gap-5 lg:grid-cols-4 xl:grid-cols-5">
            {results.tracks.map((track) => (
              <TrackCard
                key={track.id}
                track={track}
                onPlay={onTrackPlay}
              />
            ))}
          </div>
        </ResultGroup>
      )}
      {results.playlists.length > 0 && (
        <ResultGroup title="प्लेलिस्टहरू" count={results.playlists.length}>
          <div className="grid grid-cols-2 gap-x-3 gap-y-7 sm:grid-cols-3 sm:gap-5 lg:grid-cols-4 xl:grid-cols-5">
            {results.playlists.map((playlist) => (
              <PlaylistCard
                key={playlist.id}
                playlist={playlist}
                onPlay={onPlaylistPlay}
              />
            ))}
          </div>
        </ResultGroup>
      )}
      {results.authors.length > 0 && (
        <ResultGroup title="लेखकहरू" count={results.authors.length}>
          <div className="grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
            {results.authors.map((author) => (
              <AuthorCard
                key={author.id}
                author={author}
                onPlay={onTrackPlay}
              />
            ))}
          </div>
        </ResultGroup>
      )}
      {results.narrators.length > 0 && (
        <ResultGroup title="वाचकहरू" count={results.narrators.length}>
          <div className="grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
            {results.narrators.map((narrator) => (
              <NarratorCard
                key={narrator.id}
                narrator={narrator}
                onPlay={onTrackPlay}
              />
            ))}
          </div>
        </ResultGroup>
      )}
      {results.genres.length > 0 && (
        <ResultGroup title="विधाहरू" count={results.genres.length}>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
            {results.genres.map((genre) => (
              <ExploreCollectionCard
                key={genre.id}
                collection={genre}
                kind="genre"
              />
            ))}
          </div>
        </ResultGroup>
      )}
      {results.moods.length > 0 && (
        <ResultGroup title="मूडहरू" count={results.moods.length}>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
            {results.moods.map((mood) => (
              <ExploreCollectionCard
                key={mood.id}
                collection={mood}
                kind="mood"
              />
            ))}
          </div>
        </ResultGroup>
      )}
    </div>
  );
}

function ResultGroup({
  title,
  count,
  children,
}: {
  title: string;
  count: number;
  children: React.ReactNode;
}) {
  return (
    <section>
      <div className="mb-5 flex items-end gap-2">
        <h2 className="font-literary text-2xl font-semibold sm:text-3xl">
          {title}
        </h2>
        <span className="mb-1 text-xs text-muted-foreground">{count}</span>
      </div>
      {children}
    </section>
  );
}

interface SearchSuggestionsProps {
  icon: React.ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
  title: string;
  items: string[];
  emptyText: string;
  onSelect: (value: string) => void;
  action?: React.ReactNode;
}

function SearchSuggestions({
  icon: Icon,
  title,
  items,
  emptyText,
  onSelect,
  action,
}: SearchSuggestionsProps) {
  return (
    <section className="rounded-xl border border-border bg-surface/65 p-5">
      <div className="flex items-center justify-between gap-4">
        <h2 className="flex items-center gap-2 font-literary text-xl font-semibold">
          <Icon aria-hidden={true} className="size-4.5 text-primary" />
          {title}
        </h2>
        {action}
      </div>
      {items.length > 0 ? (
        <ul className="mt-4 flex flex-wrap gap-2">
          {items.map((item) => (
            <li key={item}>
              <button
                type="button"
                onClick={() => onSelect(item)}
                className="rounded-full border border-border bg-surface-soft px-3 py-2 font-nepali text-sm text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground focus-visible:outline-2 focus-visible:outline-primary"
              >
                {item}
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-5 font-nepali text-sm leading-6 text-muted-foreground">
          {emptyText}
        </p>
      )}
    </section>
  );
}

function SearchResultsSkeleton() {
  return (
    <div className="space-y-5">
      <LoadingSkeleton className="h-8 w-36" />
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {Array.from({ length: 10 }, (_, index) => (
          <div key={index} className="space-y-3">
            <LoadingSkeleton className="aspect-square rounded-xl" />
            <LoadingSkeleton className="h-4 w-4/5" />
            <LoadingSkeleton className="h-3 w-3/5" />
          </div>
        ))}
      </div>
    </div>
  );
}

function SearchEmptyState({ query }: { query: string }) {
  return (
    <EmptyState
      icon={Search}
      title={`“${query}” का लागि परिणाम भेटिएन`}
      description="अर्को हिज्जे, Romanized शब्द वा छोटो खोज प्रयोग गर्नुहोस्।"
    />
  );
}

function countSearchResults(results: SearchResults) {
  return (
    results.tracks.length +
    results.playlists.length +
    results.authors.length +
    results.narrators.length +
    results.genres.length +
    results.moods.length
  );
}
