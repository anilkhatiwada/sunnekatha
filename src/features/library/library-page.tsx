"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, LibraryBig } from "lucide-react";
import type { ReactNode } from "react";

import { AuthorCard } from "@/components/cards/author-card";
import { CompactTrackRow } from "@/components/cards/compact-track-row";
import { ContinueListeningCard } from "@/components/cards/continue-listening-card";
import { NarratorCard } from "@/components/cards/narrator-card";
import { PlaylistCard } from "@/components/cards/playlist-card";
import { TrackCard, TrackCardSkeleton } from "@/components/cards/track-card";
import { EmptyState } from "@/components/common/empty-state";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { SectionError } from "@/components/common/section-error";
import { HorizontalSection } from "@/components/sections/horizontal-section";
import { Button } from "@/components/ui/button";
import { useCatalogPlayback } from "@/features/player/use-catalog-playback";
import { usePlayerStore } from "@/features/player/player-store";
import {
  getRemoteUserLibrary,
  queryKeys,
  removeFromContinueListening,
} from "@/services";
import type {
  Author,
  ContinueListeningItem,
  Narrator,
} from "@/types";

export function LibraryPageContent() {
  const queryClient = useQueryClient();
  const libraryQuery = useQuery({
    queryKey: queryKeys.library.remote(),
    queryFn: getRemoteUserLibrary,
    staleTime: 30_000,
  });
  const { playTrack, playCollection, playPlaylist } = useCatalogPlayback();
  const seek = usePlayerStore((state) => state.seek);
  const removeProgress = useMutation({
    mutationFn: removeFromContinueListening,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.library.remote() }),
  });

  if (libraryQuery.isError) {
    return (
      <SectionError
        message="लाइब्रेरी लोड गर्न सकिएन। कृपया फेरि प्रयास गर्नुहोस्।"
        onRetry={() => void libraryQuery.refetch()}
        isRetrying={libraryQuery.isFetching}
      />
    );
  }

  if (libraryQuery.isPending) {
    return <LibraryPageSkeleton />;
  }

  const {
    favoriteTracks,
    savedPlaylists,
    followedAuthors,
    followedNarrators,
    recentlyPlayed,
    continueListening,
  } = libraryQuery.data;
  const recentTracks = recentlyPlayed.slice(0, 8).map((item) => item.track);
  const playAuthor = (author: Author) => playCollection(author.popularTracks);
  const playNarrator = (narrator: Narrator) =>
    playCollection(narrator.narratedTracks);
  const continueTrack = async (item: ContinueListeningItem) => {
    await playTrack(item.track);
    seek(item.progress.progressSeconds);
  };

  return (
    <div className="space-y-14 pb-8">
      <header className="relative overflow-hidden rounded-2xl border border-border bg-surface/75 px-5 py-9 sm:px-8 sm:py-12">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgb(229_138_82_/_0.18),transparent_34rem)]" />
        <div className="relative">
          <p className="font-nepali text-xs font-semibold tracking-wide text-primary">
            तपाईंको सङ्ग्रह
          </p>
          <h1 className="mt-2 font-literary text-4xl font-semibold sm:text-5xl">
            लाइब्रेरी
          </h1>
          <p className="mt-3 max-w-2xl font-nepali text-sm leading-7 text-muted-foreground sm:text-base">
            मन परेका रचना, सुरक्षित प्लेलिस्ट र अधुरा श्रवणहरू एउटै ठाउँमा।
          </p>
        </div>
      </header>

      <LibraryRail
        title="मनपर्ने"
        eyebrow="तपाईंले रोजेका"
        isEmpty={favoriteTracks.length === 0}
      >
        {favoriteTracks.map((track) => (
          <CardWidth key={track.id}>
            <TrackCard
              track={track}
              onPlay={(selected) => void playTrack(selected)}
            />
          </CardWidth>
        ))}
      </LibraryRail>

      <section aria-labelledby="recently-listened-heading">
        <SectionHeading
          id="recently-listened-heading"
          title="हालै सुनेका"
          eyebrow="पछिल्लो गतिविधि"
        />
        {recentTracks.length > 0 ? (
          <div className="grid gap-1 sm:grid-cols-2">
            {recentTracks.map((track, index) => (
              <CompactTrackRow
                key={track.id}
                track={track}
                index={index}
                onPlay={(selected) => void playTrack(selected)}
              />
            ))}
          </div>
        ) : (
          <LibraryEmptyState message="तपाईंले सुन्न थालेपछि हालैका रचना यहाँ देखिनेछन्।" />
        )}
      </section>

      <LibraryRail
        title="सुरक्षित प्लेलिस्ट"
        eyebrow="फेरि सुन्नका लागि"
        isEmpty={savedPlaylists.length === 0}
      >
        {savedPlaylists.map((playlist) => (
          <CardWidth key={playlist.id}>
            <PlaylistCard
              playlist={playlist}
              onPlay={(selected) => void playPlaylist(selected)}
            />
          </CardWidth>
        ))}
      </LibraryRail>

      <LibraryRail
        title="फलो गरेका लेखकहरू"
        eyebrow="मनपर्ने सर्जक"
        isEmpty={followedAuthors.length === 0}
      >
        {followedAuthors.map((author) => (
          <CardWidth key={author.id}>
            <AuthorCard
              author={author}
              onPlay={() => playAuthor(author)}
            />
          </CardWidth>
        ))}
      </LibraryRail>

      <LibraryRail
        title="फलो गरेका वाचकहरू"
        eyebrow="मनपर्ने स्वर"
        isEmpty={followedNarrators.length === 0}
      >
        {followedNarrators.map((narrator) => (
          <CardWidth key={narrator.id}>
            <NarratorCard
              narrator={narrator}
              onPlay={() => playNarrator(narrator)}
            />
          </CardWidth>
        ))}
      </LibraryRail>

      <section aria-labelledby="continue-library-heading">
        <SectionHeading
          id="continue-library-heading"
          title="अधुरो सुनेका सामग्री"
          eyebrow="जहाँ रोक्नुभएको थियो"
        />
        {continueListening.length > 0 ? (
          <div className="grid gap-3 lg:grid-cols-2">
            {continueListening.map((item) => (
              <ContinueListeningCard
                key={item.track.id}
                item={item}
                onPlay={() => void continueTrack(item)}
                onRemove={() => removeProgress.mutate(item.track.id)}
              />
            ))}
          </div>
        ) : (
          <LibraryEmptyState message="अधुरा श्रवणहरू यहाँ सुरक्षित हुनेछन्।" />
        )}
      </section>

      <section
        aria-labelledby="downloads-heading"
        className="rounded-2xl border border-dashed border-border bg-surface/40 p-6 sm:p-8"
      >
        <Download aria-hidden="true" className="size-7 text-primary" />
        <h2
          id="downloads-heading"
          className="mt-4 font-literary text-2xl font-semibold"
        >
          डाउनलोड
        </h2>
        <p className="mt-2 max-w-xl font-nepali text-sm leading-6 text-muted-foreground">
          अफलाइन सुन्न मिल्ने डाउनलोड सुविधा भविष्यको संस्करणमा उपलब्ध हुनेछ।
        </p>
        <Button
          type="button"
          variant="secondary"
          disabled
          className="mt-5 rounded-full font-nepali"
        >
          चाँडै उपलब्ध
        </Button>
      </section>
    </div>
  );
}

function LibraryRail({
  title,
  eyebrow,
  isEmpty,
  children,
}: {
  title: string;
  eyebrow: string;
  isEmpty: boolean;
  children: ReactNode;
}) {
  if (isEmpty) {
    return (
      <section>
        <SectionHeading title={title} eyebrow={eyebrow} />
        <LibraryEmptyState message="यस खण्डमा अहिलेसम्म कुनै सामग्री छैन।" />
      </section>
    );
  }

  return (
    <HorizontalSection title={title} eyebrow={eyebrow}>
      {children}
    </HorizontalSection>
  );
}

function SectionHeading({
  id,
  title,
  eyebrow,
}: {
  id?: string;
  title: string;
  eyebrow: string;
}) {
  return (
    <div className="mb-5">
      <p className="text-xs font-semibold tracking-[0.16em] text-primary uppercase">
        {eyebrow}
      </p>
      <h2
        id={id}
        className="mt-1 font-literary text-2xl font-semibold sm:text-3xl"
      >
        {title}
      </h2>
    </div>
  );
}

function LibraryEmptyState({ message }: { message: string }) {
  return (
    <EmptyState
      compact
      icon={LibraryBig}
      title="अहिलेसम्म खाली छ"
      description={message}
    />
  );
}

function CardWidth({ children }: { children: ReactNode }) {
  return (
    <div className="w-[70vw] max-w-56 shrink-0 snap-start sm:w-52">
      {children}
    </div>
  );
}

function LibraryPageSkeleton() {
  return (
    <div aria-label="लाइब्रेरी लोड हुँदैछ" role="status" className="space-y-12">
      <div className="rounded-2xl border border-border bg-surface/55 p-8">
        <LoadingSkeleton className="h-4 w-24" />
        <LoadingSkeleton className="mt-4 h-14 w-56" />
        <LoadingSkeleton className="mt-5 h-5 w-full max-w-xl" />
      </div>
      <div>
        <LoadingSkeleton className="h-8 w-40" />
        <div className="mt-5 flex gap-4 overflow-hidden">
          {Array.from({ length: 5 }, (_, index) => (
            <div key={index} className="w-52 shrink-0">
              <TrackCardSkeleton />
            </div>
          ))}
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {Array.from({ length: 4 }, (_, index) => (
          <LoadingSkeleton key={index} className="h-16 rounded-lg" />
        ))}
      </div>
    </div>
  );
}
