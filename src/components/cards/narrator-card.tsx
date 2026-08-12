"use client";

import { PersonCardLayout } from "@/components/cards/card-primitives";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { formatCompactNumber } from "@/lib/formatters";
import type { Narrator, Track } from "@/types";

interface NarratorCardProps {
  narrator: Narrator;
  onPlay: (track: Track) => void;
}

export function NarratorCard({ narrator, onPlay }: NarratorCardProps) {
  const firstTrack = narrator.narratedTracks[0];

  return (
    <PersonCardLayout
      href={`/narrator/${narrator.slug}`}
      image={narrator.image}
      name={narrator.name}
      description={`${formatCompactNumber(narrator.followerCount)} listeners`}
      playLabel={`${narrator.name}  — play narrated tracks`}
      isPlayDisabled={!firstTrack}
      onPlay={() => {
        if (firstTrack) {
          onPlay(firstTrack);
        }
      }}
    />
  );
}

export function NarratorCardSkeleton() {
  return (
    <div
      aria-label="Loading narrator"
      role="status"
      className="p-3 text-center"
    >
      <LoadingSkeleton className="aspect-square rounded-full" />
      <LoadingSkeleton className="mx-auto mt-4 h-5 w-3/4" />
      <LoadingSkeleton className="mx-auto mt-2 h-4 w-2/5" />
    </div>
  );
}
