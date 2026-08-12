"use client";

import { useQuery } from "@tanstack/react-query";
import { Mic2, Play, UserPlus, UsersRound } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";

import {
  PlaylistCard,
  PlaylistCardSkeleton,
} from "@/components/cards/playlist-card";
import { TrackCard, TrackCardSkeleton } from "@/components/cards/track-card";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { SectionError } from "@/components/common/section-error";
import { HorizontalSection } from "@/components/sections/horizontal-section";
import { Button } from "@/components/ui/button";
import { useLibraryRelationship } from "@/features/library/use-library-relationship";
import { useCatalogPlayback } from "@/features/player/use-catalog-playback";
import { formatCompactNumber } from "@/lib/formatters";
import { cn } from "@/lib/utils";
import {
  getNarratorBySlug,
  getNarratorFeaturedPlaylists,
  getNarratorTracks,
  queryKeys,
} from "@/services";
import type { CatalogPlaylist } from "@/types";

interface NarratorDetailPageContentProps {
  slug: string;
}

export function NarratorDetailPageContent({
  slug,
}: NarratorDetailPageContentProps) {
  const narratorQuery = useQuery({
    queryKey: queryKeys.narrators.detail(slug),
    queryFn: () => getNarratorBySlug(slug),
  });
  const narrator = narratorQuery.data;
  const tracksQuery = useQuery({
    queryKey: queryKeys.narrators.tracks(narrator?.id),
    queryFn: () => getNarratorTracks(narrator!.slug),
    enabled: Boolean(narrator),
  });
  const playlistsQuery = useQuery({
    queryKey: queryKeys.narrators.playlists(narrator?.id),
    queryFn: () => getNarratorFeaturedPlaylists(narrator!.slug),
    enabled: Boolean(narrator),
  });
  const { playTrack, playCollection, playPlaylist: playPlaylistDetail } =
    useCatalogPlayback();
  const follow = useLibraryRelationship("followedNarrator", narrator?.id);

  if (narratorQuery.isPending) {
    return <NarratorDetailSkeleton />;
  }

  if (narratorQuery.isError) {
    return (
      <SectionError
        message="The narrator profile could not be loaded. Please try again."
        onRetry={() => void narratorQuery.refetch()}
        isRetrying={narratorQuery.isFetching}
      />
    );
  }

  if (!narrator) {
    return <NarratorNotFound />;
  }

  const allTracks = tracksQuery.data ?? [];
  const popularTracks = allTracks.slice(0, 5);
  const fallbackTracks = narrator.narratedTracks;
  const playAllTracks = allTracks.length > 0 ? allTracks : fallbackTracks;
  const isFollowing = follow.isActive;
  const playPlaylist = (playlist: CatalogPlaylist) =>
    void playPlaylistDetail(playlist);

  return (
    <div className="space-y-14 pb-8">
      <section className="relative overflow-hidden rounded-2xl border border-border bg-surface/75 p-5 sm:p-8 lg:p-10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgb(229_138_82_/_0.2),transparent_38rem)]" />
        <div className="relative grid items-end gap-8 md:grid-cols-[16rem_minmax(0,1fr)] lg:grid-cols-[20rem_minmax(0,1fr)] lg:gap-12">
          <div className="relative">
            <Image
              src={narrator.image}
              alt={`${narrator.name} photo`}
              width={720}
              height={720}
              preload
              className="aspect-square w-full max-w-sm rounded-full object-cover shadow-[0_30px_80px_rgb(0_0_0_/_0.5)] ring-1 ring-white/10"
            />
            <span className="absolute right-3 bottom-3 inline-flex size-12 items-center justify-center rounded-full border border-primary/25 bg-background/85 text-primary shadow-xl backdrop-blur">
              <Mic2 aria-hidden="true" className="size-5" />
              <span className="sr-only">Narrator</span>
            </span>
          </div>

          <div className="min-w-0">
            <p className="font-nepali text-xs font-semibold tracking-wide text-primary">
              Narrator · Voice artist
            </p>
            <h1 className="mt-2 font-literary text-4xl leading-tight font-semibold sm:text-5xl lg:text-6xl">
              {narrator.name}
            </h1>
            <p className="mt-5 max-w-3xl font-nepali text-sm leading-7 text-muted-foreground sm:text-base">
              {narrator.biography}
            </p>

            <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-3 font-nepali text-sm text-muted-foreground">
              <span className="inline-flex items-center gap-2">
                <UsersRound
                  aria-hidden="true"
                  className="size-4 text-primary"
                />
                {formatCompactNumber(narrator.followerCount)} followers
              </span>
              <span>
                {allTracks.length || fallbackTracks.length} narrations
              </span>
            </div>

            <div className="mt-7 flex flex-wrap gap-2">
              <Button
                type="button"
                size="lg"
                disabled={playAllTracks.length === 0}
                onClick={() => void playCollection(playAllTracks)}
                className="rounded-full px-6 font-nepali"
              >
                <Play aria-hidden="true" className="size-5 fill-current" />
                All — play
              </Button>
              <Button
                type="button"
                variant="secondary"
                aria-pressed={isFollowing}
                disabled={follow.isPending}
                onClick={() => {
                  if (!follow.toggle()) {
                    window.location.assign("/login");
                  }
                }}
                className={cn(
                  "rounded-full font-nepali",
                  isFollowing && "border-primary/40 text-primary",
                )}
              >
                <UserPlus
                  aria-hidden="true"
                  className={cn("size-4", isFollowing && "fill-current")}
                />
                {isFollowing ? "Following" : "Follow"}
              </Button>
            </div>
          </div>
        </div>
      </section>

      <HorizontalSection title="Popular narrations" eyebrow="Most listened">
        {tracksQuery.isPending
          ? Array.from({ length: 5 }, (_, index) => (
              <CardWidth key={index}>
                <TrackCardSkeleton />
              </CardWidth>
            ))
          : popularTracks.map((track) => (
              <CardWidth key={track.id}>
                <TrackCard track={track} onPlay={(item) => void playTrack(item)} />
              </CardWidth>
            ))}
      </HorizontalSection>

      <section aria-labelledby="all-narrated-tracks">
        <div className="mb-5 flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold tracking-[0.16em] text-primary uppercase">
              Available in this voice
            </p>
            <h2
              id="all-narrated-tracks"
              className="mt-1 font-literary text-2xl font-semibold sm:text-3xl"
            >
              All narrations
            </h2>
          </div>
          {!tracksQuery.isPending && (
            <span className="font-nepali text-xs text-muted-foreground">
              {allTracks.length} Track
            </span>
          )}
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
          {tracksQuery.isPending
            ? Array.from({ length: 5 }, (_, index) => (
                <TrackCardSkeleton key={index} />
              ))
            : allTracks.map((track) => (
                <TrackCard
                  key={track.id}
                  track={track}
                  onPlay={(item) => void playTrack(item)}
                />
              ))}
        </div>
      </section>

      {(playlistsQuery.isPending || Boolean(playlistsQuery.data?.length)) && (
        <HorizontalSection
          title="Playlists featuring this narrator"
          eyebrow="Featured collections"
        >
          {playlistsQuery.isPending
            ? Array.from({ length: 4 }, (_, index) => (
                <CardWidth key={index}>
                  <PlaylistCardSkeleton />
                </CardWidth>
              ))
            : playlistsQuery.data?.map((playlist) => (
                <CardWidth key={playlist.id}>
                  <PlaylistCard
                    playlist={playlist}
                    onPlay={playPlaylist}
                  />
                </CardWidth>
              ))}
        </HorizontalSection>
      )}
    </div>
  );
}

function CardWidth({ children }: { children: ReactNode }) {
  return (
    <div className="w-[70vw] max-w-56 shrink-0 snap-start sm:w-52">
      {children}
    </div>
  );
}

function NarratorNotFound() {
  return (
    <div className="rounded-2xl border border-dashed border-border bg-surface/45 px-6 py-16 text-center">
      <Mic2 aria-hidden="true" className="mx-auto size-8 text-primary" />
      <h1 className="mt-4 font-literary text-2xl font-semibold">
        Narrator not found
      </h1>
      <Link
        href="/explore"
        className="mt-4 inline-flex rounded-full bg-primary px-4 py-2 font-nepali text-sm font-semibold text-background focus-visible:outline-2 focus-visible:outline-primary"
      >
        Back to Explore
      </Link>
    </div>
  );
}

function NarratorDetailSkeleton() {
  return (
    <div aria-label="Loading narrator" role="status" className="space-y-12">
      <div className="grid gap-8 rounded-2xl border border-border bg-surface/55 p-5 md:grid-cols-[16rem_minmax(0,1fr)] lg:p-10">
        <LoadingSkeleton className="aspect-square w-full rounded-full" />
        <div className="flex flex-col justify-end">
          <LoadingSkeleton className="h-4 w-28" />
          <LoadingSkeleton className="mt-4 h-14 w-3/5" />
          <LoadingSkeleton className="mt-6 h-20 w-full max-w-3xl" />
          <LoadingSkeleton className="mt-5 h-5 w-48" />
          <LoadingSkeleton className="mt-7 h-12 w-72 rounded-full" />
        </div>
      </div>
      <LoadingSkeleton className="h-72 rounded-2xl" />
    </div>
  );
}
