import { AudioLines } from "lucide-react";
import Link from "next/link";

import { cn } from "@/lib/utils";

interface LogoProps {
  compact?: boolean;
  className?: string;
}

export function Logo({ compact = false, className }: LogoProps) {
  return (
    <Link
      href="/"
      aria-label="SunneKatha गृहपृष्ठ"
      className={cn(
        "group inline-flex items-center gap-3 rounded-lg focus-visible:outline-2 focus-visible:outline-primary",
        className,
      )}
    >
      <span className="grid size-10 shrink-0 place-items-center rounded-xl border border-primary/30 bg-primary/15 text-primary shadow-[0_0_24px_rgb(229_138_82_/_0.12)] transition-colors group-hover:bg-primary/20">
        <AudioLines aria-hidden="true" className="size-5" strokeWidth={1.8} />
      </span>
      {!compact && (
        <span className="min-w-0">
          <span className="block truncate text-lg leading-none font-semibold tracking-tight text-foreground">
            SunneKatha
          </span>
          <span className="mt-1 block truncate font-nepali text-[0.68rem] text-muted-foreground">
            सुन्ने कथा, सम्झिने शब्द
          </span>
        </span>
      )}
    </Link>
  );
}
