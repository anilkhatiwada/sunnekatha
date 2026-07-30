import type { Metadata } from "next";

import { PlaylistsPageContent } from "@/features/playlist/playlists-page";

export const metadata: Metadata = {
  title: "प्लेलिस्ट",
  description: "सम्पादकीय र आफ्नै साहित्यिक श्रव्य सङ्ग्रहहरू।",
};

export default function PlaylistsPage() {
  return <PlaylistsPageContent />;
}
