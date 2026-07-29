"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Bookmark,
  ListMusic,
  Play,
  Share2,
  Shuffle,
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";

import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { ListSkeleton } from "@/components/common/list-skeleton";
import { PlaylistTrackRow } from "@/components/player/playlist-track-row";
import { Button } from "@/components/ui/button";
import { useLibraryStore } from "@/features/library/library-store";
import { usePlayerStore } from "@/features/player/player-store";
import { formatDuration } from "@/lib/formatters";
import { cn } from "@/lib/utils";
import { getPlaylistBySlug, queryKeys } from "@/services";
import type { Track } from "@/types";

interface PlaylistDetailPageContentProps {
  slug: string;
}

export function PlaylistDetailPageContent({
  slug,
}: PlaylistDetailPageContentProps) {
  const playlistQuery = useQuery({
    queryKey: queryKeys.playlists.detail(slug),
    queryFn: () => getPlaylistBySlug(slug),
  });
  const currentTrack = usePlayerStore((state) => state.currentTrack);
  const replaceQueue = usePlayerStore((state) => state.replaceQueue);
  const savedPlaylistIds = useLibraryStore(
    (state) => state.savedPlaylistIds,
  );
  const toggleSavedPlaylist = useLibraryStore(
    (state) => state.toggleSavedPlaylist,
  );
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  if (playlistQuery.isPending) {
    return <PlaylistDetailSkeleton />;
  }

  if (playlistQuery.isError) {
    return (
      <ErrorState
        message="प्लेलिस्ट लोड गर्न सकिएन। कृपया फेरि प्रयास गर्नुहोस्।"
        onRetry={() => void playlistQuery.refetch()}
        isRetrying={playlistQuery.isFetching}
      />
    );
  }

  const playlist = playlistQuery.data;
  if (!playlist) {
    return (
      <EmptyState
        icon={ListMusic}
        title="प्लेलिस्ट भेटिएन"
        description="यो प्लेलिस्ट हटाइएको वा उपलब्ध नभएको हुन सक्छ।"
        action={
          <Link
            href="/explore"
            className="inline-flex min-h-11 items-center rounded-full bg-primary px-4 py-2 font-nepali text-sm font-semibold text-background"
          >
            अन्वेषणमा फर्कनुहोस्
          </Link>
        }
      />
    );
  }

  const isSaved = savedPlaylistIds.includes(playlist.id);
  const hasTracks = playlist.tracks.length > 0;

  const playAll = () => replaceQueue(playlist.tracks);
  const playShuffled = () => replaceQueue(shuffleTracks(playlist.tracks));
  const playFromTrack = (index: number) =>
    replaceQueue(playlist.tracks.slice(index));

  return (
    <div className="space-y-10 pb-8">
      <section className="relative overflow-hidden rounded-2xl border border-border bg-surface/75 p-5 sm:p-7 lg:p-9">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgb(229_138_82_/_0.18),transparent_34rem)]" />
        <div className="relative grid gap-7 md:grid-cols-[15rem_minmax(0,1fr)] lg:grid-cols-[19rem_minmax(0,1fr)] lg:gap-10">
          <Image
            src={playlist.coverImage}
            alt={`${playlist.title} प्लेलिस्टको आवरण`}
            width={640}
            height={640}
            preload
            className="aspect-square w-full max-w-sm rounded-xl object-cover shadow-[0_28px_70px_rgb(0_0_0_/_0.45)] ring-1 ring-white/10"
          />
          <div className="flex min-w-0 flex-col justify-end">
            <p className="font-nepali text-xs font-medium tracking-wide text-primary">
              विशेष प्लेलिस्ट
            </p>
            <h1 className="mt-2 font-literary text-4xl leading-tight font-semibold sm:text-5xl lg:text-6xl">
              {playlist.title}
            </h1>
            <p className="mt-4 max-w-2xl font-nepali text-sm leading-7 text-muted-foreground sm:text-base">
              {playlist.description}
            </p>
            <div className="mt-5 flex flex-wrap items-center gap-x-2 gap-y-1 font-nepali text-sm text-muted-foreground">
              <span className="font-medium text-foreground">
                {playlist.curatorName}
              </span>
              <span aria-hidden="true">•</span>
              <span>{playlist.trackCount} रचना</span>
              <span aria-hidden="true">•</span>
              <span>{formatDuration(playlist.totalDuration)}</span>
            </div>

            <div className="mt-7 flex flex-wrap items-center gap-2">
              <Button
                type="button"
                disabled={!hasTracks}
                onClick={playAll}
                className="rounded-full px-5 font-nepali"
              >
                <Play aria-hidden="true" className="size-4 fill-current" />
                सबै बजाउनुहोस्
              </Button>
              <Button
                type="button"
                variant="secondary"
                disabled={!hasTracks}
                onClick={playShuffled}
                className="rounded-full font-nepali"
              >
                <Shuffle aria-hidden="true" className="size-4" />
                शफल
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={() => toggleSavedPlaylist(playlist.id)}
                aria-pressed={isSaved}
                className={cn(
                  "rounded-full font-nepali",
                  isSaved && "text-primary",
                )}
              >
                <Bookmark
                  aria-hidden="true"
                  className={cn("size-4", isSaved && "fill-current")}
                />
                {isSaved ? "सुरक्षित" : "सुरक्षित गर्नुहोस्"}
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={() =>
                  setStatusMessage("साझा गर्ने सुविधा चाँडै उपलब्ध हुनेछ।")
                }
                className="rounded-full font-nepali"
              >
                <Share2 aria-hidden="true" className="size-4" />
                साझा
              </Button>
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

      <section aria-labelledby="playlist-tracks-heading">
        <div className="mb-4 flex items-end justify-between gap-4 px-2">
          <h2
            id="playlist-tracks-heading"
            className="font-literary text-2xl font-semibold sm:text-3xl"
          >
            रचनाहरू
          </h2>
          <span className="font-nepali text-xs text-muted-foreground">
            {playlist.tracks.length} रचना
          </span>
        </div>
        <div className="hidden grid-cols-[2.5rem_minmax(0,1.4fr)_minmax(8rem,0.8fr)_minmax(8rem,0.8fr)_6rem_4rem_auto] gap-3 border-b border-border px-3 py-2 font-nepali text-[0.7rem] text-muted-foreground sm:grid">
          <span className="text-center">#</span>
          <span>शीर्षक</span>
          <span>लेखक</span>
          <span>वाचक</span>
          <span>प्रकार</span>
          <span className="text-right">समय</span>
          <span className="sr-only">विकल्प</span>
        </div>
        {hasTracks ? (
          <ol className="mt-1 space-y-1">
            {playlist.tracks.map((track, index) => (
              <PlaylistTrackRow
                key={track.id}
                track={track}
                index={index}
                isActive={currentTrack?.id === track.id}
                onPlay={() => playFromTrack(index)}
                onMoreActions={() =>
                  setStatusMessage(
                    `${track.title} का थप विकल्प चाँडै उपलब्ध हुनेछन्।`,
                  )
                }
              />
            ))}
          </ol>
        ) : (
          <div className="rounded-xl border border-dashed border-border px-6 py-12 text-center font-nepali text-sm text-muted-foreground">
            यस प्लेलिस्टमा कुनै रचना छैन।
          </div>
        )}
      </section>
    </div>
  );
}

function shuffleTracks(tracks: Track[]) {
  const shuffled = [...tracks];

  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const randomIndex = Math.floor(Math.random() * (index + 1));
    [shuffled[index], shuffled[randomIndex]] = [
      shuffled[randomIndex],
      shuffled[index],
    ];
  }

  return shuffled;
}

function PlaylistDetailSkeleton() {
  return (
    <div className="space-y-10" aria-label="प्लेलिस्ट लोड हुँदैछ" role="status">
      <div className="grid gap-7 rounded-2xl border border-border bg-surface/60 p-5 md:grid-cols-[15rem_minmax(0,1fr)]">
        <LoadingSkeleton className="aspect-square w-full rounded-xl" />
        <div className="flex flex-col justify-end gap-4">
          <LoadingSkeleton className="h-4 w-28" />
          <LoadingSkeleton className="h-12 w-3/4" />
          <LoadingSkeleton className="h-4 w-full max-w-xl" />
          <LoadingSkeleton className="h-10 w-64 rounded-full" />
        </div>
      </div>
      <ListSkeleton />
    </div>
  );
}
