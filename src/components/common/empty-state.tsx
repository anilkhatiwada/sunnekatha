import type { LucideIcon } from "lucide-react";
import { LibraryBig } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: LucideIcon;
  action?: ReactNode;
  compact?: boolean;
  className?: string;
}

export function EmptyState({
  title,
  description,
  icon: Icon = LibraryBig,
  action,
  compact = false,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "grid place-items-center rounded-xl border border-dashed border-border bg-surface/45 px-6 text-center",
        compact ? "min-h-36 py-7" : "min-h-64 py-12",
        className,
      )}
    >
      <div className="max-w-md">
        <div className="mx-auto grid size-12 place-items-center rounded-full border border-primary/20 bg-primary-muted/25 text-primary">
          <Icon aria-hidden="true" className="size-5" />
        </div>
        <h2 className="mt-4 font-literary text-xl font-semibold text-foreground">
          {title}
        </h2>
        <p className="mt-2 font-nepali text-sm leading-6 text-muted-foreground">
          {description}
        </p>
        {action ? <div className="mt-5">{action}</div> : null}
      </div>
    </div>
  );
}
