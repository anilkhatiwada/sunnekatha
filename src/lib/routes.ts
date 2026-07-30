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
    label: "गृहपृष्ठ",
    icon: House,
  },
  {
    href: "/search",
    label: "खोज्नुहोस्",
    icon: Search,
  },
  {
    href: "/library",
    label: "लाइब्रेरी",
    icon: Library,
    requiresAuth: true,
  },
  {
    href: "/playlists",
    label: "प्लेलिस्ट",
    icon: ListMusic,
  },
  {
    href: "/profile",
    label: "प्रोफाइल",
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
