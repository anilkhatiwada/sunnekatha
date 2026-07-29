import "@fontsource-variable/inter/wght.css";
import "@fontsource-variable/noto-sans-devanagari/wght.css";
import "@fontsource-variable/noto-serif-devanagari/wght.css";

import type { Metadata, Viewport } from "next";

import { AppShell } from "@/components/layout/app-shell";
import { AppProviders } from "@/components/providers/app-providers";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "SunneKatha",
    template: "%s · SunneKatha",
  },
  description:
    "नेपाली कथा, कविता र साहित्य सुन्ने शान्त र आत्मीय डिजिटल मञ्च।",
  applicationName: "SunneKatha",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "SunneKatha",
  },
  icons: {
    apple: "/icons/pwa-192.png",
  },
};

export const viewport: Viewport = {
  colorScheme: "dark",
  themeColor: "#0b0a09",
};

interface RootLayoutProps {
  children: React.ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="ne" data-scroll-behavior="smooth">
      <body>
        <AppProviders>
          <AppShell>{children}</AppShell>
        </AppProviders>
      </body>
    </html>
  );
}
