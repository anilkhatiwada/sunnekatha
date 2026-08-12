"use client";

import { useQuery } from "@tanstack/react-query";
import { BookOpenText, Disc3, Play } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import { TrackCard, TrackCardSkeleton } from "@/components/cards";
import { EmptyState } from "@/components/common/empty-state";
import { SectionError } from "@/components/common/section-error";
import { Button } from "@/components/ui/button";
import { useCatalogPlayback } from "@/features/player/use-catalog-playback";
import {
  getAlbumBySlug,
  getLiteraryWorkBySlug,
  queryKeys,
} from "@/services";
import type { Album, LiteraryWork } from "@/types";

export function CatalogDetailPage({
  kind,
  slug,
}: {
  kind: "work" | "album";
  slug: string;
}) {
  const detailQuery = useQuery<LiteraryWork | Album | null>({
    queryKey:
      kind === "work"
        ? queryKeys.works.detail(slug)
        : queryKeys.albums.detail(slug),
    queryFn: async () =>
      kind === "work"
        ? await getLiteraryWorkBySlug(slug)
        : await getAlbumBySlug(slug),
  });
  const { playTrack, playCollection } = useCatalogPlayback();

  if (detailQuery.isPending) {
    return <CatalogDetailSkeleton />;
  }
  if (detailQuery.isError) {
    return (
      <SectionError
        message="The collection could not be loaded. Please try again."
        onRetry={() => void detailQuery.refetch()}
        isRetrying={detailQuery.isFetching}
      />
    );
  }
  if (!detailQuery.data) {
    return (
      <EmptyState
        icon={kind === "work" ? BookOpenText : Disc3}
        title="Collection not found"
        description="This content may have been removed or is unavailable."
      />
    );
  }

  const item = detailQuery.data;
  const eyebrow = kind === "work" ? "Literary Work" : "Audio Album";
  const metadata =
    kind === "work"
      ? getWorkMetadata(item as LiteraryWork)
      : getAlbumMetadata(item as Album);

  return (
    <div className="space-y-12 pb-8">
      <section className="relative overflow-hidden rounded-2xl border border-border bg-surface/75 p-5 sm:p-8 lg:p-10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgb(215_173_99_/_0.17),transparent_38rem)]" />
        <div className="relative grid items-end gap-8 md:grid-cols-[16rem_minmax(0,1fr)] lg:grid-cols-[20rem_minmax(0,1fr)]">
          <Image
            src={item.coverImage}
            alt={`${item.title} cover`}
            width={720}
            height={720}
            className="aspect-square w-full max-w-sm rounded-xl object-cover shadow-[0_30px_80px_rgb(0_0_0_/_0.5)]"
          />
          <div>
            <p className="font-nepali text-xs font-semibold text-primary">
              {eyebrow}
            </p>
            <h1 className="mt-2 font-literary text-4xl font-semibold sm:text-5xl lg:text-6xl">
              {item.title}
            </h1>
            {item.titleEnglish ? (
              <p className="mt-2 text-base text-muted-foreground">
                {item.titleEnglish}
              </p>
            ) : null}
            <Link
              href={`/author/${item.author.slug}`}
              className="mt-4 inline-flex font-nepali text-sm font-semibold text-foreground hover:text-primary"
            >
              {item.author.name}
            </Link>
            <p className="mt-4 max-w-3xl font-nepali text-sm leading-7 text-muted-foreground">
              {item.description || "A description will be added soon."}
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              {metadata.map((value) => (
                <span
                  key={value}
                  className="rounded-full border border-border bg-background/40 px-3 py-1.5 font-nepali text-xs text-muted-foreground"
                >
                  {value}
                </span>
              ))}
            </div>
            <Button
              type="button"
              disabled={item.tracks.length === 0}
              onClick={() => void playCollection(item.tracks)}
              className="mt-7 rounded-full px-6 font-nepali"
            >
              <Play aria-hidden="true" className="size-4 fill-current" />
              All — play
            </Button>
          </div>
        </div>
      </section>

      <section>
        <p className="text-xs font-semibold tracking-[0.16em] text-primary uppercase">
          Ordered audio content
        </p>
        <h2 className="mt-1 font-literary text-3xl font-semibold">
          {item.tracks.length} Track
        </h2>
        {item.tracks.length ? (
          <div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-5">
            {item.tracks.map((track) => (
              <TrackCard
                key={track.id}
                track={track}
                onPlay={(selected) => void playTrack(selected)}
              />
            ))}
          </div>
        ) : (
          <EmptyState
            compact
            title="No audio tracks available"
            description="Processed tracks will appear here."
            className="mt-5"
          />
        )}
      </section>
    </div>
  );
}

function getWorkMetadata(work: LiteraryWork) {
  return [
    work.contentType,
    work.language,
    work.publicationYear ? String(work.publicationYear) : "",
    ...work.genres,
    ...work.moods,
  ].filter(Boolean);
}

function getAlbumMetadata(album: Album) {
  return [
    album.albumType,
    album.releaseDate ?? "",
    ...album.genres,
    ...album.moods,
  ].filter(Boolean);
}

function CatalogDetailSkeleton() {
  return (
    <div className="space-y-10" role="status" aria-label="Loading collection">
      <div className="grid gap-8 rounded-2xl border border-border bg-surface/60 p-6 md:grid-cols-[16rem_minmax(0,1fr)]">
        <TrackCardSkeleton />
        <div className="min-h-72 animate-pulse rounded-xl bg-surface-soft" />
      </div>
    </div>
  );
}
