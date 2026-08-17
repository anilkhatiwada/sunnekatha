import { BookOpenText } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import type { ContentCategory } from "@/types";

interface CategoryCircleCardProps {
  category: ContentCategory;
}

export function CategoryCircleCard({ category }: CategoryCircleCardProps) {
  return (
    <Link
      href={`/explore?type=${encodeURIComponent(category.slug)}`}
      className="group flex min-w-0 flex-col items-center rounded-2xl px-1 py-2 text-center focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-primary"
    >
      <span className="relative grid size-32 shrink-0 place-items-center overflow-hidden rounded-full border border-border bg-surface-soft text-primary shadow-[0_18px_45px_rgb(0_0_0_/_0.28)] transition duration-300 group-hover:-translate-y-1 group-hover:border-primary/50 group-hover:shadow-[0_22px_55px_rgb(0_0_0_/_0.38)] sm:size-36 lg:size-40">
        {category.image ? (
          <Image
            src={category.image}
            alt=""
            fill
            sizes="(max-width: 639px) 128px, (max-width: 1023px) 144px, 160px"
            className="object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <BookOpenText aria-hidden="true" className="size-10" />
        )}
      </span>
      <span className="mt-4 line-clamp-2 text-base font-semibold leading-6 text-foreground group-hover:text-primary sm:text-lg">
        {category.nameEnglish || category.name}
      </span>
    </Link>
  );
}
