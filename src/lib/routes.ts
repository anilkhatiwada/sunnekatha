import {
  CircleUserRound,
  House,
  Library,
  ListMusic,
  Search,
  type LucideIcon,
} from "lucide-react";

export interface NavigationItem {
  href: string;
  label: string;
  icon: LucideIcon;
  requiresAuth?: boolean;
}

export const MAIN_NAVIGATION: NavigationItem[] = [
  {
    href: "/",
    label: "Home",
    icon: House,
  },
  {
    href: "/search",
    label: "Search",
    icon: Search,
  },
  {
    href: "/library",
    label: "Library",
    icon: Library,
    requiresAuth: true,
  },
  {
    href: "/playlists",
    label: "Playlists",
    icon: ListMusic,
  },
  {
    href: "/profile",
    label: "Profile",
    icon: CircleUserRound,
    requiresAuth: true,
  },
];

export function isNavigationItemActive(pathname: string, href: string) {
  if (href === "/") {
    return pathname === href;
  }

  return pathname === href || pathname.startsWith(`${href}/`);
}
