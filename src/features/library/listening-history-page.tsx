"use client";

import { useQuery } from "@tanstack/react-query";
import { Clock3, Play } from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { Button } from "@/components/ui/button";
import { useCatalogPlayback } from "@/features/player/use-catalog-playback";
import { formatDuration } from "@/lib/formatters";
import { getListeningHistory, queryKeys } from "@/services";

export function ListeningHistoryPage() {
  const history = useQuery({
    queryKey: queryKeys.progress.history(),
    queryFn: getListeningHistory,
  });
  const { playTrack } = useCatalogPlayback();

  if (history.isPending) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 8 }, (_, index) => (
          <LoadingSkeleton key={index} className="h-20 rounded-xl" />
        ))}
      </div>
    );
  }
  if (history.isError) {
    return (
      <ErrorState
        message="सुन्ने इतिहास लोड गर्न सकिएन।"
        onRetry={() => void history.refetch()}
      />
    );
  }

  return (
    <div className="space-y-7 pb-8">
      <header>
        <p className="font-nepali text-sm font-semibold text-primary">
          तपाईंको गतिविधि
        </p>
        <h1 className="mt-2 font-literary text-4xl font-semibold">
          सुन्ने इतिहास
        </h1>
      </header>
      {history.data.length ? (
        <ol className="space-y-2">
          {history.data.map((item) => (
            <li
              key={item.track.id}
              className="flex items-center gap-3 rounded-xl border border-border bg-surface/60 p-3"
            >
              <Button
                type="button"
                size="icon"
                onClick={() => void playTrack(item.track)}
                aria-label={`${item.track.title} बजाउनुहोस्`}
                className="shrink-0 rounded-full"
              >
                <Play aria-hidden="true" className="size-4 fill-current" />
              </Button>
              <div className="min-w-0 flex-1">
                <Link
                  href={`/track/${item.track.slug}`}
                  className="line-clamp-1 font-nepali font-semibold hover:text-primary"
                >
                  {item.track.title}
                </Link>
                <p className="mt-1 font-nepali text-xs text-muted-foreground">
                  {item.playCount} पटक · जम्मा{" "}
                  {formatDuration(item.totalListenedSeconds)}
                </p>
              </div>
              <time
                dateTime={item.lastListenedAt}
                className="hidden font-nepali text-xs text-muted-foreground sm:block"
              >
                {new Intl.DateTimeFormat("ne-NP", {
                  month: "short",
                  day: "numeric",
                }).format(new Date(item.lastListenedAt))}
              </time>
            </li>
          ))}
        </ol>
      ) : (
        <EmptyState
          icon={Clock3}
          title="सुन्ने इतिहास खाली छ"
          description="रचना सुन्न थालेपछि गतिविधि यहाँ देखिनेछ।"
        />
      )}
    </div>
  );
}
