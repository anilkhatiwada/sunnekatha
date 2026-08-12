import Image from "next/image";
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
      aria-label="SunneKatha Home"
      className={cn(
        "group inline-flex items-center gap-3 rounded-lg focus-visible:outline-2 focus-visible:outline-primary",
        className,
      )}
    >
      <span className="grid size-10 shrink-0 place-items-center overflow-hidden rounded-xl border border-primary/30 bg-surface-soft shadow-[0_0_24px_rgb(229_138_82_/_0.12)] transition-colors group-hover:border-primary/50">
        <Image
          src="/brand/sunnekatha-waveform.png"
          alt=""
          aria-hidden="true"
          width={40}
          height={40}
          className="h-auto w-9"
          priority
        />
      </span>
      {!compact && (
        <Image
          src="/brand/sunnekatha-wordmark.png"
          alt=""
          aria-hidden="true"
          width={520}
          height={158}
          className="h-auto w-[8.6rem] sm:w-[9.25rem]"
          priority
        />
      )}
    </Link>
  );
}
