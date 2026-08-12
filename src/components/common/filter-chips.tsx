import Link from "next/link";

import type { ExploreFilter } from "@/features/explore/explore-config";
import { cn } from "@/lib/utils";

interface FilterChipsProps {
  filters: ExploreFilter[];
  activeFilter: ExploreFilter["value"];
}

export function FilterChips({
  filters,
  activeFilter,
}: FilterChipsProps) {
  return (
    <nav aria-label="Content type" className="-mx-4 sm:mx-0">
      <ul className="flex snap-x gap-2 overflow-x-auto px-4 pb-2 [scrollbar-width:none] sm:flex-wrap sm:px-0 [&::-webkit-scrollbar]:hidden">
        {filters.map((filter) => {
          const isActive = filter.value === activeFilter;
          const href =
            filter.value === "all"
              ? "/explore"
              : `/explore?type=${filter.value}`;

          return (
            <li key={filter.value} className="shrink-0 snap-start">
              <Link
                href={href}
                replace
                scroll={false}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "inline-flex h-10 items-center rounded-full border px-4 font-nepali text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-primary",
                  isActive
                    ? "border-primary bg-primary text-background"
                    : "border-border bg-surface/80 text-muted-foreground hover:border-primary/50 hover:text-foreground",
                )}
              >
                {filter.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
