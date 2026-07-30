import { ArrowUpRight, BookOpenText, Sparkles } from "lucide-react";
import Link from "next/link";

import { cn } from "@/lib/utils";
import type { Genre, Mood } from "@/types";

interface ExploreCollectionCardProps {
  collection: Genre | Mood;
  kind: "genre" | "mood";
}

export function ExploreCollectionCard({
  collection,
  kind,
}: ExploreCollectionCardProps) {
  const Icon = kind === "mood" ? Sparkles : BookOpenText;
  const href =
    kind === "genre"
      ? `/genre/${collection.slug}`
      : `/mood/${collection.slug}`;

  return (
    <Link
      href={href}
      className={cn(
        "group relative min-h-32 overflow-hidden rounded-xl border border-border bg-surface p-4 transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-lg hover:shadow-black/20 focus-visible:outline-2 focus-visible:outline-primary",
        kind === "mood" &&
          "bg-[radial-gradient(circle_at_top_right,rgb(229_138_82_/_0.18),transparent_70%)]",
      )}
    >
      <div className="flex items-start justify-between">
        <span className="grid size-9 place-items-center rounded-lg bg-primary-muted/35 text-primary">
          <Icon aria-hidden="true" className="size-4.5" />
        </span>
        <ArrowUpRight
          aria-hidden="true"
          className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-primary"
        />
      </div>
      <h3 className="mt-4 font-literary text-lg font-semibold text-foreground">
        {collection.name}
      </h3>
      <p className="mt-1 line-clamp-2 font-nepali text-xs leading-5 text-muted-foreground">
        {collection.description}
      </p>
    </Link>
  );
}
