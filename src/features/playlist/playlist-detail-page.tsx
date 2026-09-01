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
import { LiteraryWorkCard } from "@/components/cards";
import { Button } from "@/components/ui/button";
import { useLibraryRelationship } from "@/features/library/use-library-relationship";
import { usePlayerStore } from "@/features/player/player-store";
import { useCatalogPlayback } from "@/features/player/use-catalog-playback";
import { PlaylistOwnerControls } from "@/features/playlist/playlist-owner-controls";
import { formatDuration } from "@/lib/formatters";
import { sharePage } from "@/lib/share";
import { cn } from "@/lib/utils";
import { getPlaylistBySlug, queryKeys } from "@/services";
import type { CatalogTrack } from "@/types";

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
  const { playCollection } = useCatalogPlayback();
  const saved = useLibraryRelationship("savedPlaylist", playlistQuery.data?.id);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  if (playlistQuery.isPending) {
    return <PlaylistDetailSkeleton />;
  }

  if (playlistQuery.isError) {
    return (
      <ErrorState
        message="The playlist could not be loaded. Please try again."
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
        title="Playlist not found"
        description="This playlist may have been removed or is unavailable."
        action={
          <Link
            href="/explore"
            className="inline-flex min-h-11 items-center rounded-full bg-primary px-4 py-2 font-nepali text-sm font-semibold text-background"
          >
            Back to Explore
          </Link>
        }
      />
    );
  }

  const isSaved = saved.isActive;
  const hasTracks = playlist.tracks.length > 0;

  const playAll = () => void playCollection(playlist.tracks);
  const playShuffled = () =>
    void playCollection(shuffleTracks(playlist.tracks));
  const playFromTrack = (index: number) =>
    void playCollection(playlist.tracks, index);

  return (
    <div className="space-y-10 pb-8">
      <section className="relative overflow-hidden rounded-2xl border border-border bg-surface/75 p-5 sm:p-7 lg:p-9">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgb(229_138_82_/_0.18),transparent_34rem)]" />
        <div className="relative grid gap-7 md:grid-cols-[15rem_minmax(0,1fr)] lg:grid-cols-[19rem_minmax(0,1fr)] lg:gap-10">
          <Image
            src={playlist.coverImage}
            alt={`${playlist.title} Playlistcover`}
            width={640}
            height={640}
            preload
            className="aspect-square w-full max-w-sm rounded-xl object-cover shadow-[0_28px_70px_rgb(0_0_0_/_0.45)] ring-1 ring-white/10"
          />
          <div className="flex min-w-0 flex-col justify-end">
            <p className="font-nepali text-xs font-medium tracking-wide text-primary">
              Featured playlist
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
              <span>{playlist.trackCount} Track</span>
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
                All — play
              </Button>
              <Button
                type="button"
                variant="secondary"
                disabled={!hasTracks}
                onClick={playShuffled}
                className="rounded-full font-nepali"
              >
                <Shuffle aria-hidden="true" className="size-4" />
                Shuffle
              </Button>
              <Button
                type="button"
                variant="ghost"
                disabled={saved.isPending}
                onClick={() => {
                  if (!saved.toggle()) {
                    setStatusMessage(
                      "Sign in to save this playlist.",
                    );
                  }
                }}
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
                {isSaved ? "Saved" : "Save"}
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={() => {
                  void sharePage({
                    title: playlist.title,
                    text: `${playlist.title} · SunneKatha`,
                  })
                    .then((result) =>
                      setStatusMessage(
                        result === "copied"
                          ? "Playlist link copied."
                          : "Playlist shared.",
                      ),
                    )
                    .catch(() => undefined);
                }}
                className="rounded-full font-nepali"
              >
                <Share2 aria-hidden="true" className="size-4" />
                Share
              </Button>
            </div>
            <p
              role="status"
              aria-live="polite"
              className="mt-2 min-h-5 font-nepali text-xs text-muted-foreground"
            >
              {saved.error
                ? "The playlist could not be saved. Please try again."
                : statusMessage}
            </p>
          </div>
        </div>
      </section>

      {playlist.isOwnedByCurrentUser ? (
        <PlaylistOwnerControls playlist={playlist} />
      ) : null}

      <section aria-labelledby="playlist-tracks-heading">
        <div className="mb-4 flex items-end justify-between gap-4 px-2">
          <h2
            id="playlist-tracks-heading"
            className="font-literary text-2xl font-semibold sm:text-3xl"
          >
            Tracks
          </h2>
          <span className="font-nepali text-xs text-muted-foreground">
            {playlist.tracks.length} Track
          </span>
        </div>
        <div className="hidden grid-cols-[2.5rem_minmax(0,1.4fr)_minmax(8rem,0.8fr)_minmax(8rem,0.8fr)_6rem_4rem_auto] gap-3 border-b border-border px-3 py-2 font-nepali text-[0.7rem] text-muted-foreground sm:grid">
          <span className="text-center">#</span>
          <span>Title</span>
          <span>Author</span>
          <span>Narrator</span>
          <span>Type</span>
          <span className="text-right">Duration</span>
          <span className="sr-only">Options</span>
        </div>
        {playlist.items?.some((item) => item.kind === "work") ? (
          <div className="mt-4 space-y-6">
            {playlist.items.map((item) =>
              item.kind === "work" ? (
                <div key={item.id} className="max-w-[15rem]">
                  <LiteraryWorkCard work={item.content} />
                </div>
              ) : (
                <ol key={item.id} className="space-y-1">
                  <PlaylistTrackRow
                    track={item.content}
                    index={item.position - 1}
                    isActive={currentTrack?.id === item.content.id}
                    onPlay={() => {
                      const index = playlist.tracks.findIndex((track) => track.id === item.content.id);
                      if (index >= 0) playFromTrack(index);
                    }}
                    onMoreActions={() => setStatusMessage(`${item.content.title} — more options will be available soon.`)}
                  />
                </ol>
              ),
            )}
          </div>
        ) : hasTracks ? (
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
                    `${track.title} — more options will be available soon.`,
                  )
                }
              />
            ))}
          </ol>
        ) : (
          <div className="rounded-xl border border-dashed border-border px-6 py-12 text-center font-nepali text-sm text-muted-foreground">
            This playlist has no tracks.
          </div>
        )}
      </section>
    </div>
  );
}

function shuffleTracks(tracks: CatalogTrack[]) {
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
    <div className="space-y-10" aria-label="Loading playlist" role="status">
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
