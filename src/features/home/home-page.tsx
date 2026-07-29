"use client";

import { useQuery } from "@tanstack/react-query";
import { motion, useReducedMotion } from "framer-motion";

import {
  AuthorCard,
  ContinueListeningCard,
  FeaturedHeroCard,
  FeaturedHeroCardSkeleton,
  NarratorCard,
  PlaylistCard,
  TrackCard,
} from "@/components/cards";
import { EmptyState } from "@/components/common/empty-state";
import { SearchInput } from "@/components/common/search-input";
import { SectionError } from "@/components/common/section-error";
import { CardRailSkeleton } from "@/components/sections/card-rail-skeleton";
import { HorizontalSection } from "@/components/sections/horizontal-section";
import { usePlayerStore } from "@/features/player/player-store";
import {
  getContinueListening,
  getFeaturedPlaylists,
  getMoodPlaylists,
  getPopularAuthors,
  getPopularNarrators,
  queryKeys,
  getRecentlyAddedTracks,
  getTrendingTracks,
} from "@/services";
import type { Playlist } from "@/types";

const cardWidth = "w-[10.5rem] shrink-0 snap-start sm:w-[13rem] lg:w-[14rem]";
const personCardWidth =
  "w-[10.5rem] shrink-0 snap-start sm:w-[12rem] lg:w-[13rem]";
const continueCardWidth =
  "w-[19rem] shrink-0 snap-start sm:w-[23rem] lg:w-[25rem]";

export function HomePageContent() {
  const shouldReduceMotion = useReducedMotion();
  const playTrack = usePlayerStore((state) => state.play);
  const replaceQueue = usePlayerStore((state) => state.replaceQueue);
  const seek = usePlayerStore((state) => state.seek);
  const handlePlaylistPlay = (playlist: Playlist) =>
    replaceQueue(playlist.tracks);
  const featuredQuery = useQuery({
    queryKey: queryKeys.home.featuredPlaylists(),
    queryFn: getFeaturedPlaylists,
  });
  const continueQuery = useQuery({
    queryKey: queryKeys.home.continueListening(),
    queryFn: getContinueListening,
  });
  const trendingQuery = useQuery({
    queryKey: queryKeys.home.trendingTracks(),
    queryFn: getTrendingTracks,
  });
  const recentlyAddedQuery = useQuery({
    queryKey: queryKeys.home.recentlyAdded(),
    queryFn: getRecentlyAddedTracks,
  });
  const authorsQuery = useQuery({
    queryKey: queryKeys.home.popularAuthors(),
    queryFn: getPopularAuthors,
  });
  const narratorsQuery = useQuery({
    queryKey: queryKeys.home.popularNarrators(),
    queryFn: getPopularNarrators,
  });
  const moodsQuery = useQuery({
    queryKey: queryKeys.home.moodPlaylists(),
    queryFn: getMoodPlaylists,
  });

  const featuredHero = featuredQuery.data?.[0];

  return (
    <div className="space-y-12 pb-6 sm:space-y-16 lg:space-y-20">
      <motion.header
        initial={shouldReduceMotion ? false : { opacity: 0, y: 10 }}
        animate={shouldReduceMotion ? undefined : { opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="pt-2 sm:pt-4"
      >
        <p className="font-nepali text-sm font-medium text-primary">शुभ साँझ</p>
        <h1 className="mt-2 max-w-3xl font-literary text-4xl leading-tight font-semibold text-foreground sm:text-5xl lg:text-6xl">
          नेपाली साहित्य अब कानसम्म
        </h1>
        <p className="mt-4 max-w-2xl font-nepali text-base leading-8 text-muted-foreground sm:text-lg">
          कथा, कविता र विचारका प्रिय नेपाली आवाजहरू एकै ठाउँमा सुन्नुहोस्।
        </p>
        <SearchInput className="mt-7 max-w-2xl" />
      </motion.header>

      <section aria-label="विशेष प्रस्तुति">
        {featuredQuery.isPending && <FeaturedHeroCardSkeleton />}
        {featuredQuery.isError && (
          <SectionError
            onRetry={() => void featuredQuery.refetch()}
            isRetrying={featuredQuery.isFetching}
          />
        )}
        {featuredQuery.isSuccess && !featuredHero && (
          <EmptyState
            compact
            title="विशेष प्रस्तुति आउँदैछ"
            description="नयाँ साहित्यिक सङ्ग्रह तयार भएपछि यहाँ देखिनेछ।"
          />
        )}
        {featuredHero && (
          <FeaturedHeroCard
            playlist={featuredHero}
            onPlay={handlePlaylistPlay}
          />
        )}
      </section>

      <HorizontalSection title="अहिले सुन्दै हुनुहुन्छ">
        {continueQuery.isPending && (
          <CardRailSkeleton variant="continue" count={3} />
        )}
        {continueQuery.isError && (
          <div className="w-full shrink-0">
            <SectionError
              onRetry={() => void continueQuery.refetch()}
              isRetrying={continueQuery.isFetching}
            />
          </div>
        )}
        {continueQuery.data?.map((item) => (
          <div key={item.track.id} className={continueCardWidth}>
            <ContinueListeningCard
              item={item}
              onPlay={() => {
                replaceQueue([item.track]);
                seek(item.progress.progressSeconds);
              }}
            />
          </div>
        ))}
        {continueQuery.isSuccess && continueQuery.data.length === 0 && (
          <EmptyRail title="सुन्न बाँकी केही छैन" />
        )}
      </HorizontalSection>

      <HorizontalSection
        title="विशेष प्लेलिस्टहरू"
        viewAllHref="/playlists"
      >
        {featuredQuery.isPending && (
          <CardRailSkeleton variant="playlist" count={5} />
        )}
        {featuredQuery.isError && (
          <div className="w-full shrink-0">
            <SectionError
              onRetry={() => void featuredQuery.refetch()}
              isRetrying={featuredQuery.isFetching}
            />
          </div>
        )}
        {featuredQuery.data?.map((playlist) => (
          <div key={playlist.id} className={cardWidth}>
            <PlaylistCard
              playlist={playlist}
              onPlay={handlePlaylistPlay}
            />
          </div>
        ))}
        {featuredQuery.isSuccess && featuredQuery.data.length === 0 && (
          <EmptyRail title="प्लेलिस्ट उपलब्ध छैन" />
        )}
      </HorizontalSection>

      <HorizontalSection title="यो हप्ता लोकप्रिय">
        {trendingQuery.isPending && (
          <CardRailSkeleton variant="track" count={6} />
        )}
        {trendingQuery.isError && (
          <div className="w-full shrink-0">
            <SectionError
              onRetry={() => void trendingQuery.refetch()}
              isRetrying={trendingQuery.isFetching}
            />
          </div>
        )}
        {trendingQuery.data?.map((track) => (
          <div key={track.id} className={cardWidth}>
            <TrackCard track={track} onPlay={playTrack} />
          </div>
        ))}
        {trendingQuery.isSuccess && trendingQuery.data.length === 0 && (
          <EmptyRail title="लोकप्रिय रचना उपलब्ध छैन" />
        )}
      </HorizontalSection>

      <HorizontalSection title="भर्खरै थपिएका">
        {recentlyAddedQuery.isPending && (
          <CardRailSkeleton variant="track" count={6} />
        )}
        {recentlyAddedQuery.isError && (
          <div className="w-full shrink-0">
            <SectionError
              onRetry={() => void recentlyAddedQuery.refetch()}
              isRetrying={recentlyAddedQuery.isFetching}
            />
          </div>
        )}
        {recentlyAddedQuery.data?.map((track) => (
          <div key={track.id} className={cardWidth}>
            <TrackCard track={track} onPlay={playTrack} />
          </div>
        ))}
        {recentlyAddedQuery.isSuccess &&
          recentlyAddedQuery.data.length === 0 && (
            <EmptyRail title="नयाँ रचना चाँडै आउँदैछन्" />
          )}
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
        {authorsQuery.data?.map((author) => (
          <div key={author.id} className={personCardWidth}>
            <AuthorCard author={author} onPlay={playTrack} />
          </div>
        ))}
        {authorsQuery.isSuccess && authorsQuery.data.length === 0 && (
          <EmptyRail title="लेखकहरू उपलब्ध छैनन्" />
        )}
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
        {narratorsQuery.data?.map((narrator) => (
          <div key={narrator.id} className={personCardWidth}>
            <NarratorCard narrator={narrator} onPlay={playTrack} />
          </div>
        ))}
        {narratorsQuery.isSuccess && narratorsQuery.data.length === 0 && (
          <EmptyRail title="वाचकहरू उपलब्ध छैनन्" />
        )}
      </HorizontalSection>

      <HorizontalSection
        eyebrow="मनको लयअनुसार"
        title="मूडअनुसार सुन्नुहोस्"
        viewAllHref="/playlists"
      >
        {moodsQuery.isPending && (
          <CardRailSkeleton variant="playlist" count={3} />
        )}
        {moodsQuery.isError && (
          <div className="w-full shrink-0">
            <SectionError
              onRetry={() => void moodsQuery.refetch()}
              isRetrying={moodsQuery.isFetching}
            />
          </div>
        )}
        {moodsQuery.data?.map((playlist) => (
          <div key={playlist.id} className={cardWidth}>
            <PlaylistCard
              playlist={playlist}
              onPlay={handlePlaylistPlay}
            />
          </div>
        ))}
        {moodsQuery.isSuccess && moodsQuery.data.length === 0 && (
          <EmptyRail title="मूड सङ्ग्रह उपलब्ध छैन" />
        )}
      </HorizontalSection>
    </div>
  );
}

function EmptyRail({ title }: { title: string }) {
  return (
    <div className="w-full min-w-[19rem] shrink-0">
      <EmptyState
        compact
        title={title}
        description="नयाँ सामग्री थपिएपछि यहाँ देखिनेछ।"
      />
    </div>
  );
}
