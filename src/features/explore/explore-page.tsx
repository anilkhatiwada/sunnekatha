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
import {
  EXPLORE_FILTERS,
  type ExploreFilter,
} from "@/features/explore/explore-config";
import { useCatalogPlayback } from "@/features/player/use-catalog-playback";
import {
  getExploreTracks,
  getFeaturedPlaylists,
  getGenres,
  getMoods,
  getPopularAuthors,
  getPopularNarrators,
  queryKeys,
} from "@/services";
import type { CatalogPlaylist, ContentType } from "@/types";

interface ExplorePageContentProps {
  activeFilter: ExploreFilter["value"];
  genre?: string;
  mood?: string;
}

const railCardWidth =
  "w-[10.5rem] shrink-0 snap-start sm:w-[13rem] lg:w-[14rem]";
const personCardWidth =
  "w-[10.5rem] shrink-0 snap-start sm:w-[12rem] lg:w-[13rem]";

export function ExplorePageContent({
  activeFilter,
  genre,
  mood,
}: ExplorePageContentProps) {
  const { playTrack, playCollection } = useCatalogPlayback();
  const contentType =
    activeFilter === "all" ? undefined : (activeFilter as ContentType);

  const releasesQuery = useQuery({
    queryKey: queryKeys.explore.releases({ contentType, genre, mood }),
    queryFn: () => getExploreTracks({ contentType, genre, mood }),
  });
  const moodsQuery = useQuery({
    queryKey: queryKeys.explore.moods(),
    queryFn: getMoods,
  });
  const genresQuery = useQuery({
    queryKey: queryKeys.explore.genres(),
    queryFn: getGenres,
  });
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

  const playPlaylist = (playlist: CatalogPlaylist) =>
    void playCollection(playlist.tracks);
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
          नयाँ आवाज पत्ता लगाउनुहोस्
        </p>
        <h1 className="mt-2 font-literary text-4xl font-semibold sm:text-5xl">
          नेपाली साहित्य अन्वेषण
        </h1>
        <p className="mt-3 font-nepali text-base leading-7 text-muted-foreground">
          मनको लय, प्रिय विधा र नयाँ सर्जकअनुसार सुन्ने अर्को रचना छान्नुहोस्।
        </p>
      </header>

      <FilterChips
        filters={EXPLORE_FILTERS}
        activeFilter={activeFilter}
      />
      {(genre || mood) && (
        <div className="-mt-8 flex min-h-8 items-center gap-2 sm:-mt-12">
          <span className="font-nepali text-xs text-muted-foreground">
            सक्रिय सङ्ग्रह:
          </span>
          {activeCollection ? (
            <Link
              href={clearCollectionHref}
              replace
              scroll={false}
              className="inline-flex items-center gap-1.5 rounded-full border border-primary/40 bg-primary-muted/25 px-3 py-1.5 font-nepali text-xs text-foreground transition-colors hover:bg-primary-muted/40 focus-visible:outline-2 focus-visible:outline-primary"
              aria-label={`${activeCollection.name} फिल्टर हटाउनुहोस्`}
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
          title="नयाँ रचना"
          description={
            genre || mood
              ? "छानिएको सङ्ग्रहसँग मिल्ने नयाँ श्रव्य रचना"
              : "भर्खरै SunneKatha मा थपिएका श्रव्य रचना"
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
            title="यो छनोटमा रचना भेटिएन"
            description="अर्को विधा वा मूड छानेर फेरि अन्वेषण गर्नुहोस्।"
          />
        )}
      </section>

      <section aria-labelledby="moods-heading">
        <SectionHeading
          id="moods-heading"
          title="मूडअनुसार सुन्नुहोस्"
          description="आजको मनस्थितिसँग मिल्ने साहित्य"
        />
        {moodsQuery.isPending ? (
          <CollectionGridSkeleton />
        ) : moodsQuery.isError ? (
          <SectionError
            onRetry={() => void moodsQuery.refetch()}
            isRetrying={moodsQuery.isFetching}
          />
        ) : moodsQuery.data.length === 0 ? (
          <EmptyState compact title="मूड सङ्ग्रह उपलब्ध छैन" description="नयाँ सङ्ग्रह चाँडै थपिनेछन्।" />
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
          title="विधाहरू"
          description="कथा, विचार र कल्पनाका विविध संसार"
        />
        {genresQuery.isPending ? (
          <CollectionGridSkeleton />
        ) : genresQuery.isError ? (
          <SectionError
            onRetry={() => void genresQuery.refetch()}
            isRetrying={genresQuery.isFetching}
          />
        ) : genresQuery.data.length === 0 ? (
          <EmptyState compact title="विधाहरू उपलब्ध छैनन्" description="विधागत सङ्ग्रह चाँडै थपिनेछन्।" />
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

      <HorizontalSection title="विशेष प्लेलिस्टहरू" viewAllHref="/playlists">
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
          <RailEmpty title="प्लेलिस्ट उपलब्ध छैन" />
        )}
        {playlistsQuery.data?.map((playlist) => (
          <div key={playlist.id} className={railCardWidth}>
            <PlaylistCard playlist={playlist} onPlay={playPlaylist} />
          </div>
        ))}
      </HorizontalSection>

      <HorizontalSection title="लोकप्रिय लेखकहरू">
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
          <RailEmpty title="लेखकहरू उपलब्ध छैनन्" />
        )}
        {authorsQuery.data?.map((author) => (
          <div key={author.id} className={personCardWidth}>
            <AuthorCard author={author} onPlay={playTrack} />
          </div>
        ))}
      </HorizontalSection>

      <HorizontalSection title="लोकप्रिय वाचकहरू">
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
          <RailEmpty title="वाचकहरू उपलब्ध छैनन्" />
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

function RailEmpty({ title }: { title: string }) {
  return (
    <div className="w-full min-w-72 shrink-0">
      <EmptyState
        compact
        title={title}
        description="नयाँ सामग्री थपिएपछि यहाँ देखिनेछ।"
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
