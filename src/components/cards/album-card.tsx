import Image from "next/image";
import Link from "next/link";

import { DEFAULT_ARTWORK_PATH } from "@/services/api-mappers";
import type { HomeAlbum } from "@/types";

export function AlbumCard({ album }: { album: HomeAlbum }) {
  return (
    <article className="group min-w-0 rounded-xl border border-transparent p-3 transition-[background-color,border-color,transform] hover:-translate-y-0.5 hover:border-border/80 hover:bg-surface">
      <div className="relative aspect-square overflow-hidden rounded-lg bg-surface-soft shadow-[0_16px_42px_rgb(0_0_0_/_0.3)]">
        <Image
          src={album.coverImage || DEFAULT_ARTWORK_PATH}
          alt={`${album.title} Albumcover`}
          fill
          sizes="(max-width: 640px) 44vw, (max-width: 1024px) 28vw, 240px"
          className="object-cover transition duration-500 group-hover:scale-[1.025]"
        />
      </div>
      <h3 className="mt-4 line-clamp-2 min-h-12 font-nepali text-base leading-6 font-semibold text-foreground">
        <Link
          href={`/album/${album.slug}`}
          className="rounded-sm transition-colors hover:text-primary focus-visible:outline-2 focus-visible:outline-primary"
        >
          {album.title}
        </Link>
      </h3>
      <p className="mt-1 truncate font-nepali text-sm text-muted-foreground">
        {album.authorName}
      </p>
    </article>
  );
}
