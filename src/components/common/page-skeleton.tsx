import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { CardRailSkeleton } from "@/components/sections/card-rail-skeleton";

export function PageSkeleton() {
  return (
    <div
      role="status"
      aria-label="Loading page"
      className="space-y-12 pb-8"
    >
      <header className="max-w-3xl pt-2">
        <LoadingSkeleton className="h-4 w-24" />
        <LoadingSkeleton className="mt-4 h-12 w-3/4 max-w-xl" />
        <LoadingSkeleton className="mt-4 h-5 w-full max-w-2xl" />
        <LoadingSkeleton className="mt-2 h-5 w-2/3 max-w-lg" />
      </header>
      <LoadingSkeleton className="h-64 rounded-2xl sm:h-80" />
      <section>
        <LoadingSkeleton className="mb-5 h-8 w-52" />
        <div className="flex gap-4 overflow-hidden">
          <CardRailSkeleton variant="track" count={5} />
        </div>
      </section>
    </div>
  );
}
