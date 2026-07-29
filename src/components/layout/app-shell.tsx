import { AppHeader } from "@/components/layout/app-header";
import { DesktopSidebar } from "@/components/layout/desktop-sidebar";
import { MobileNavigation } from "@/components/layout/mobile-navigation";
import { PageContainer } from "@/components/layout/page-container";
import { PlayerSpace } from "@/components/player/player-space";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="min-h-dvh overflow-x-clip">
      <a
        href="#main-content"
        className="fixed top-2 left-2 z-[100] -translate-y-20 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-background transition-transform focus:translate-y-0"
      >
        मुख्य सामग्रीमा जानुहोस्
      </a>

      <DesktopSidebar />

      <div className="min-h-dvh pb-[calc(9rem+env(safe-area-inset-bottom))] lg:pl-64 lg:pb-[5.5rem]">
        <AppHeader />
        <main id="main-content" tabIndex={-1}>
          <PageContainer>{children}</PageContainer>
        </main>
      </div>

      <PlayerSpace />
      <MobileNavigation />
    </div>
  );
}
