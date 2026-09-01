"use client";

import { BookOpenText } from "lucide-react";

import { CardTitleLink, MediaArtwork } from "@/components/cards/card-primitives";
import { formatDuration } from "@/lib/formatters";
import type { LiteraryWork } from "@/types";

export function LiteraryWorkCard({ work }: { work: LiteraryWork }) {
  return (
    <article className="group min-w-0 rounded-xl border border-transparent p-3 transition-[background-color,border-color,transform] hover:-translate-y-0.5 hover:border-border/80 hover:bg-surface focus-within:border-border/80 focus-within:bg-surface">
      <MediaArtwork
        src={work.coverImage}
        alt={`${work.title} cover`}
        sizes="(max-width: 640px) 44vw, (max-width: 1024px) 28vw, 240px"
        className="aspect-square rounded-lg shadow-[0_16px_42px_rgb(0_0_0_/_0.3)]"
      >
        <span className="absolute top-2.5 left-2.5 inline-flex items-center gap-1 rounded-full border border-gold/25 bg-background/85 px-2 py-1 text-[0.65rem] font-semibold text-gold backdrop-blur">
          <BookOpenText aria-hidden="true" className="size-3" />
          {work.chapterCount} chapters
        </span>
      </MediaArtwork>
      <div className="mt-4 min-w-0">
        <h3 className="line-clamp-2 min-h-12">
          <CardTitleLink
            href={`/work/${work.slug}`}
            title={work.title}
            className="inline text-base leading-6"
          />
        </h3>
        <p className="mt-1 truncate text-sm text-muted-foreground">
          {work.author.name} · {formatDuration(work.totalDuration)}
        </p>
      </div>
    </article>
  );
}
