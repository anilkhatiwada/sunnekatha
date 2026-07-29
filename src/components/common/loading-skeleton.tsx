import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

export function LoadingSkeleton({
  className,
  ...props
}: ComponentProps<"div">) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "animate-pulse rounded-md bg-surface-soft motion-reduce:animate-none",
        className,
      )}
      {...props}
    />
  );
}
