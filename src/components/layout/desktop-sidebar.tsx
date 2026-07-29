"use client";

import { BookOpenText } from "lucide-react";

import { Logo } from "@/components/layout/logo";
import { NavigationLink } from "@/components/layout/navigation-link";
import { MAIN_NAVIGATION } from "@/lib/routes";

export function DesktopSidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-border/80 bg-surface/94 px-4 py-5 backdrop-blur-xl lg:flex">
      <Logo className="px-2" />

      <nav aria-label="मुख्य नेभिगेसन" className="mt-10">
        <p className="px-3 text-[0.68rem] font-semibold tracking-[0.18em] text-muted-foreground uppercase">
          मेनु
        </p>
        <ul className="mt-3 space-y-1">
          {MAIN_NAVIGATION.map((item) => (
            <li key={item.href}>
              <NavigationLink item={item} />
            </li>
          ))}
        </ul>
      </nav>

      <div className="mt-auto mb-20 rounded-xl border border-border/80 bg-background/45 p-4">
        <BookOpenText
          aria-hidden="true"
          className="size-5 text-gold"
          strokeWidth={1.7}
        />
        <p className="mt-3 font-literary text-sm leading-6 text-foreground">
          शब्दबाट आवाजसम्मको आत्मीय यात्रा
        </p>
      </div>
    </aside>
  );
}
