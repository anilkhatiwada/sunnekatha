import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { cn } from "@/lib/utils";

interface ListSkeletonProps {
  count?: number;
  className?: string;
}

export function ListSkeleton({
  count = 5,
  className,
}: ListSkeletonProps) {
  return (
    <div
      role="status"
      aria-label="Loading list"
      className={cn("space-y-2", className)}
    >
      {Array.from({ length: count }, (_, index) => (
        <div
          key={index}
          className="flex items-center gap-3 rounded-lg border border-border/70 bg-surface/45 p-3"
        >
          <LoadingSkeleton className="size-12 shrink-0 rounded-md" />
          <div className="min-w-0 flex-1">
            <LoadingSkeleton className="h-4 w-3/5" />
            <LoadingSkeleton className="mt-2 h-3 w-2/5" />
          </div>
          <LoadingSkeleton className="size-10 shrink-0 rounded-full" />
        </div>
      ))}
    </div>
  );
}
