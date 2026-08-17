import Image from "next/image";
import Link from "next/link";

import { cn } from "@/lib/utils";

interface LogoProps {
  className?: string;
}

export function Logo({ className }: LogoProps) {
  return (
    <Link
      href="/"
      aria-label="SunneKatha Home"
      className={cn(
        "group inline-flex items-center gap-3 rounded-lg focus-visible:outline-2 focus-visible:outline-primary",
        className,
      )}
    >
      <Image
        src="/brand/sunnekatha-wordmark.png"
        alt=""
        aria-hidden="true"
        width={520}
        height={158}
        className="h-auto w-[9.5rem] sm:w-[10.25rem]"
        priority
      />
    </Link>
  );
}
