"use client";

import { NavigationLink } from "@/components/layout/navigation-link";
import { MAIN_NAVIGATION } from "@/lib/routes";
import { useAuth } from "@/features/auth/auth-provider";

export function MobileNavigation() {
  const { user } = useAuth();
  const navigation = MAIN_NAVIGATION.filter((item) => !item.requiresAuth || user);
  return (
    <nav
      aria-label="Mobile navigation"
      className="fixed inset-x-0 bottom-0 z-50 border-t border-border/80 bg-surface/96 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl lg:hidden"
    >
      <ul className="mx-auto flex h-16 max-w-xl items-stretch px-1">
        {navigation.map((item) => (
          <li key={item.href} className="flex min-w-0 flex-1">
            <NavigationLink item={item} mobile />
          </li>
        ))}
      </ul>
    </nav>
  );
}
