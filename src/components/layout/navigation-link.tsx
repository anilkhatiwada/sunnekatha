"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import type { NavigationItem } from "@/lib/routes";
import { isNavigationItemActive } from "@/lib/routes";
import { cn } from "@/lib/utils";

interface NavigationLinkProps {
  item: NavigationItem;
  mobile?: boolean;
}

export function NavigationLink({
  item,
  mobile = false,
}: NavigationLinkProps) {
  const pathname = usePathname();
  const isActive = isNavigationItemActive(pathname, item.href);
  const Icon = item.icon;

  return (
    <Link
      href={item.href}
      aria-current={isActive ? "page" : undefined}
      className={cn(
        "group relative flex rounded-lg font-nepali transition-colors focus-visible:outline-2 focus-visible:outline-primary",
        mobile
          ? "min-w-0 flex-1 flex-col items-center justify-center gap-1 px-1 py-2 text-[0.68rem]"
          : "items-center gap-3 px-3 py-2.5 text-sm",
        isActive
          ? "bg-primary/12 text-primary"
          : "text-muted-foreground hover:bg-surface-soft hover:text-foreground",
      )}
    >
      <Icon
        aria-hidden="true"
        className={cn(
          "shrink-0 transition-transform group-hover:scale-105",
          mobile ? "size-5" : "size-[1.15rem]",
        )}
        strokeWidth={isActive ? 2.2 : 1.8}
      />
      <span className="truncate">{item.label}</span>
      {isActive && mobile && (
        <span
          aria-hidden="true"
          className="absolute inset-x-4 -top-px h-0.5 rounded-full bg-primary"
        />
      )}
    </Link>
  );
}
