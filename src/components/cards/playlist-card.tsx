"use client";

import {
  CardPlayButton,
  CardTitleLink,
  MediaArtwork,
} from "@/components/cards/card-primitives";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import type { CatalogPlaylist, Playlist } from "@/types";

interface PlaylistCardProps<TPlaylist extends CatalogPlaylist | Playlist> {
  playlist: TPlaylist;
  onPlay: (playlist: TPlaylist) => void;
  priority?: boolean;
}

export function PlaylistCard<TPlaylist extends CatalogPlaylist | Playlist>({
  playlist,
  onPlay,
  priority = false,
}: PlaylistCardProps<TPlaylist>) {
  return (
    <article className="group min-w-0 rounded-xl border border-transparent p-3 transition-[background-color,border-color,transform] hover:-translate-y-0.5 hover:border-border/80 hover:bg-surface focus-within:border-border/80 focus-within:bg-surface">
      <MediaArtwork
        src={playlist.coverImage}
        alt={`${playlist.title} प्लेलिस्टको आवरण`}
        sizes="(max-width: 640px) 44vw, (max-width: 1024px) 28vw, 240px"
        priority={priority}
        className="aspect-square rounded-lg shadow-[0_16px_42px_rgb(0_0_0_/_0.3)]"
      >
        <div className="absolute inset-0 bg-gradient-to-t from-background/65 via-transparent to-transparent" />
        <span className="absolute bottom-3 left-3 rounded-full border border-border/70 bg-background/75 px-2 py-1 font-nepali text-[0.68rem] text-foreground backdrop-blur">
          {playlist.trackCount} रचना
        </span>
        <CardPlayButton
          label={`${playlist.title} प्लेलिस्ट बजाउनुहोस्`}
          onPlay={() => onPlay(playlist)}
          disabled={playlist.tracks.length === 0}
          className="absolute right-3 bottom-3 translate-y-0 opacity-100 lg:translate-y-2 lg:opacity-0 lg:group-hover:translate-y-0 lg:group-hover:opacity-100 lg:group-focus-within:translate-y-0 lg:group-focus-within:opacity-100"
        />
      </MediaArtwork>

      <div className="mt-4 min-w-0">
        <h3 className="line-clamp-2 min-h-12">
          <CardTitleLink
            href={`/playlist/${playlist.slug}`}
            title={playlist.title}
            className="inline text-base leading-6"
          />
        </h3>
        <p className="mt-1 line-clamp-2 font-nepali text-sm leading-6 text-muted-foreground">
          {playlist.description}
        </p>
      </div>
    </article>
  );
}

export function PlaylistCardSkeleton() {
  return (
    <div aria-label="प्लेलिस्ट लोड हुँदैछ" role="status" className="p-3">
      <LoadingSkeleton className="aspect-square rounded-lg" />
      <LoadingSkeleton className="mt-4 h-5 w-4/5" />
      <LoadingSkeleton className="mt-2 h-4 w-full" />
      <LoadingSkeleton className="mt-1.5 h-4 w-2/3" />
    </div>
  );
}
