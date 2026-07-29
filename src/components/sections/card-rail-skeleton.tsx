import {
  AuthorCardSkeleton,
  ContinueListeningCardSkeleton,
  NarratorCardSkeleton,
  PlaylistCardSkeleton,
  TrackCardSkeleton,
} from "@/components/cards";

type SkeletonVariant =
  | "track"
  | "playlist"
  | "author"
  | "narrator"
  | "continue";

interface CardRailSkeletonProps {
  variant: SkeletonVariant;
  count?: number;
}

function SkeletonCard({ variant }: { variant: SkeletonVariant }) {
  if (variant === "playlist") return <PlaylistCardSkeleton />;
  if (variant === "author") return <AuthorCardSkeleton />;
  if (variant === "narrator") return <NarratorCardSkeleton />;
  if (variant === "continue") return <ContinueListeningCardSkeleton />;
  return <TrackCardSkeleton />;
}

export function CardRailSkeleton({
  variant,
  count = 4,
}: CardRailSkeletonProps) {
  const width =
    variant === "continue"
      ? "w-[19rem] sm:w-[23rem]"
      : "w-[10.5rem] sm:w-[13rem] lg:w-[14rem]";

  return Array.from({ length: count }, (_, index) => (
    <div key={index} className={`shrink-0 snap-start ${width}`}>
      <SkeletonCard variant={variant} />
    </div>
  ));
}
