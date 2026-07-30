"use client";

import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { Clock3, Search, TrendingUp, X } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
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
import { useCatalogPlayback } from "@/features/player/use-catalog-playback";
import {
  getSearchSuggestions,
  getTrendingSearches,
  queryKeys,
  searchContent,
  searchTracks,
} from "@/services";
import type {
  CatalogPlaylist,
  CatalogTrack,
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
  const [isSearchFocused, setIsSearchFocused] = useState(false);
  const debouncedQuery = useDebouncedValue(query.trim(), SEARCH_DEBOUNCE_MS);
  const searches = useSearchHistoryStore((state) => state.searches);
  const addSearch = useSearchHistoryStore((state) => state.addSearch);
  const clearHistory = useSearchHistoryStore((state) => state.clearHistory);
  const { playTrack, playPlaylist } = useCatalogPlayback();

  const resultsQuery = useQuery({
    queryKey: queryKeys.search.results(debouncedQuery, activeFilter),
    queryFn: ({ signal }) =>
      searchContent({
        query: debouncedQuery,
        resultType: activeFilter,
      }, signal),
    enabled: debouncedQuery.length > 0 && activeFilter !== "tracks",
  });
  const trackResultsQuery = useInfiniteQuery({
    queryKey: queryKeys.search.results(debouncedQuery, "tracks"),
    queryFn: ({ pageParam, signal }) =>
      searchTracks(debouncedQuery, pageParam, signal),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => lastPage.nextPage ?? undefined,
    enabled: debouncedQuery.length > 0 && activeFilter === "tracks",
  });
  const autocompleteQuery = useQuery({
    queryKey: queryKeys.search.autocomplete(debouncedQuery),
    queryFn: ({ signal }) =>
      getSearchSuggestions(debouncedQuery, signal),
    enabled: isSearchFocused && debouncedQuery.length >= 2,
    staleTime: 30_000,
  });
  const trendingQuery = useQuery({
    queryKey: queryKeys.search.trending(),
    queryFn: ({ signal }) => getTrendingSearches(signal),
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
    if (
      debouncedQuery &&
      (resultsQuery.isSuccess || trackResultsQuery.isSuccess)
    ) {
      addSearch(debouncedQuery);
    }
  }, [
    addSearch,
    debouncedQuery,
    resultsQuery.isSuccess,
    trackResultsQuery.isSuccess,
  ]);

  const chooseSearch = (value: string) => {
    setQuery(value);
    setIsSearchFocused(false);
    addSearch(value);
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    addSearch(query);
  };

  const hasQuery = debouncedQuery.length > 0;
  const searchResults =
    activeFilter === "tracks"
      ? {
          tracks:
            trackResultsQuery.data?.pages.flatMap(
              (page) => page.results,
            ) ?? [],
          works: [],
          albums: [],
          playlists: [],
          authors: [],
          narrators: [],
          genres: [],
          moods: [],
        }
      : resultsQuery.data;
  const isResultsPending =
    activeFilter === "tracks"
      ? trackResultsQuery.isPending
      : resultsQuery.isPending;
  const isResultsError =
    activeFilter === "tracks"
      ? trackResultsQuery.isError
      : resultsQuery.isError;
  const resultCount = searchResults
    ? countSearchResults(searchResults)
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
          onFocus={() => setIsSearchFocused(true)}
          onBlur={() => setIsSearchFocused(false)}
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={
            isSearchFocused &&
            Boolean(autocompleteQuery.data?.length)
          }
          aria-controls="catalog-search-suggestions"
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
        {isSearchFocused && autocompleteQuery.data?.length ? (
          <ul
            id="catalog-search-suggestions"
            role="listbox"
            aria-label="खोज सुझावहरू"
            className="absolute top-full z-30 mt-2 max-h-80 w-full overflow-y-auto rounded-xl border border-border bg-surface p-2 shadow-2xl shadow-black/30"
          >
            {autocompleteQuery.data.map((suggestion) => (
              <li
                key={`${suggestion.type}-${suggestion.id}`}
                role="option"
                aria-selected="false"
              >
                <button
                  type="button"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => chooseSearch(suggestion.label)}
                  className="flex w-full items-center justify-between gap-4 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-surface-soft focus-visible:outline-2 focus-visible:outline-primary"
                >
                  <span className="font-nepali text-sm">
                    {suggestion.label}
                  </span>
                  {suggestion.labelEnglish ? (
                    <span className="truncate text-xs text-muted-foreground">
                      {suggestion.labelEnglish}
                    </span>
                  ) : null}
                </button>
              </li>
            ))}
          </ul>
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

          <section aria-live="polite" aria-busy={isResultsPending}>
            {isResultsPending ? (
              <SearchResultsSkeleton />
            ) : isResultsError ? (
              <SectionError
                message="खोज परिणाम ल्याउन सकिएन।"
                onRetry={() =>
                  void (activeFilter === "tracks"
                    ? trackResultsQuery.refetch()
                    : resultsQuery.refetch())
                }
                isRetrying={
                  activeFilter === "tracks"
                    ? trackResultsQuery.isFetching
                    : resultsQuery.isFetching
                }
              />
            ) : resultCount === 0 ? (
              <SearchEmptyState query={debouncedQuery} />
            ) : searchResults ? (
              <>
                <GroupedSearchResults
                  results={searchResults}
                  onTrackPlay={playTrack}
                  onPlaylistPlay={(playlist) => void playPlaylist(playlist)}
                />
                {activeFilter === "tracks" &&
                trackResultsQuery.hasNextPage ? (
                  <div className="mt-8 flex justify-center">
                    <Button
                      type="button"
                      variant="secondary"
                      disabled={trackResultsQuery.isFetchingNextPage}
                      onClick={() =>
                        void trackResultsQuery.fetchNextPage()
                      }
                    >
                      {trackResultsQuery.isFetchingNextPage
                        ? "थप परिणाम लोड हुँदैछ…"
                        : "थप परिणाम देखाउनुहोस्"}
                    </Button>
                  </div>
                ) : null}
              </>
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
  onTrackPlay: (track: CatalogTrack) => void;
  onPlaylistPlay: (playlist: CatalogPlaylist) => void;
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
      {results.works.length > 0 && (
        <ResultGroup title="साहित्यिक कृति" count={results.works.length}>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
            {results.works.map((work) => (
              <SearchCatalogCard key={work.id} item={work} kind="work" />
            ))}
          </div>
        </ResultGroup>
      )}
      {results.albums.length > 0 && (
        <ResultGroup title="एल्बमहरू" count={results.albums.length}>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
            {results.albums.map((album) => (
              <SearchCatalogCard key={album.id} item={album} kind="album" />
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

function SearchCatalogCard({
  item,
  kind,
}: {
  item: SearchResults["works"][number];
  kind: "work" | "album";
}) {
  return (
    <article className="min-w-0 rounded-xl border border-border/70 bg-surface p-3">
      <Link href={`/${kind}/${item.slug}`} className="group block">
        <div className="relative aspect-square overflow-hidden rounded-lg bg-surface-soft">
          <Image
            src={item.coverImage}
            alt={`${item.title} को आवरण`}
            fill
            sizes="(max-width: 640px) 45vw, 220px"
            className="object-cover transition-transform group-hover:scale-[1.025]"
          />
        </div>
        <h3 className="mt-3 line-clamp-2 font-nepali font-semibold group-hover:text-primary">
          {item.title}
        </h3>
      </Link>
      <p className="mt-1 truncate font-nepali text-xs text-muted-foreground">
        {item.authorName}
      </p>
    </article>
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
    results.works.length +
    results.albums.length +
    results.playlists.length +
    results.authors.length +
    results.narrators.length +
    results.genres.length +
    results.moods.length
  );
}
