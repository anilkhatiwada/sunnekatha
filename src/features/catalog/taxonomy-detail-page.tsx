"use client";

import { useQuery } from "@tanstack/react-query";
import { BookOpenText, Sparkles } from "lucide-react";

import { TrackCard, TrackCardSkeleton } from "@/components/cards";
import { EmptyState } from "@/components/common/empty-state";
import { SectionError } from "@/components/common/section-error";
import { useCatalogPlayback } from "@/features/player/use-catalog-playback";
import {
  getCatalogTracks,
  getGenreBySlug,
  getMoodBySlug,
  queryKeys,
} from "@/services";

export function TaxonomyDetailPage({
  kind,
  slug,
}: {
  kind: "genre" | "mood";
  slug: string;
}) {
  const collectionQuery = useQuery({
    queryKey:
      kind === "genre"
        ? queryKeys.taxonomy.genre(slug)
        : queryKeys.taxonomy.mood(slug),
    queryFn: () =>
      kind === "genre" ? getGenreBySlug(slug) : getMoodBySlug(slug),
  });
  const tracksQuery = useQuery({
    queryKey: queryKeys.explore.releases({
      [kind]: slug,
    }),
    queryFn: () => getCatalogTracks({ [kind]: slug }),
  });
  const { playTrack } = useCatalogPlayback();
  const Icon = kind === "genre" ? BookOpenText : Sparkles;

  if (collectionQuery.isError || tracksQuery.isError) {
    return (
      <SectionError
        onRetry={() => {
          void collectionQuery.refetch();
          void tracksQuery.refetch();
        }}
        isRetrying={
          collectionQuery.isFetching || tracksQuery.isFetching
        }
      />
    );
  }

  const collection = collectionQuery.data;
  return (
    <div className="space-y-10 pb-8">
      <header className="rounded-2xl border border-border bg-[radial-gradient(circle_at_top_left,rgb(229_138_82_/_0.18),transparent_34rem)] p-7 sm:p-10">
        <Icon aria-hidden="true" className="size-8 text-primary" />
        <p className="mt-5 font-nepali text-xs font-semibold text-primary">
          {kind === "genre" ? "साहित्यिक विधा" : "मनस्थितिअनुसार सङ्ग्रह"}
        </p>
        <h1 className="mt-2 font-literary text-4xl font-semibold sm:text-5xl">
          {collection?.name ?? "सङ्ग्रह"}
        </h1>
        <p className="mt-3 max-w-2xl font-nepali text-sm leading-7 text-muted-foreground">
          {collection?.description || "यस छनोटका श्रव्य रचना।"}
        </p>
      </header>

      {tracksQuery.isPending ? (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-5">
          {Array.from({ length: 10 }, (_, index) => (
            <TrackCardSkeleton key={index} />
          ))}
        </div>
      ) : tracksQuery.data.length ? (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-5">
          {tracksQuery.data.map((track) => (
            <TrackCard
              key={track.id}
              track={track}
              onPlay={(selected) => void playTrack(selected)}
            />
          ))}
        </div>
      ) : (
        <EmptyState
          title="रचना भेटिएन"
          description="यो सङ्ग्रहमा प्रकाशनयोग्य श्रव्य रचना थपिएपछि यहाँ देखिनेछन्।"
        />
      )}
    </div>
  );
}
