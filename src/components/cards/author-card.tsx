"use client";

import { PersonCardLayout } from "@/components/cards/card-primitives";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import type { Author, Track } from "@/types";

interface AuthorCardProps {
  author: Author;
  onPlay: (track: Track) => void;
}

export function AuthorCard({ author, onPlay }: AuthorCardProps) {
  const firstTrack = author.popularTracks[0];

  return (
    <PersonCardLayout
      href={`/author/${author.slug}`}
      image={author.image}
      name={author.name}
      description="Author"
      playLabel={`${author.name}  — play popular tracks`}
      isPlayDisabled={!firstTrack}
      onPlay={() => {
        if (firstTrack) {
          onPlay(firstTrack);
        }
      }}
    />
  );
}

export function AuthorCardSkeleton() {
  return (
    <div
      aria-label="Loading author"
      role="status"
      className="p-3 text-center"
    >
      <LoadingSkeleton className="aspect-square rounded-full" />
      <LoadingSkeleton className="mx-auto mt-4 h-5 w-3/4" />
      <LoadingSkeleton className="mx-auto mt-2 h-4 w-1/3" />
    </div>
  );
}
