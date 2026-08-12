import type { Metadata } from "next";

import { PlaylistsPageContent } from "@/features/playlist/playlists-page";

export const metadata: Metadata = {
  title: "Playlist",
  description: "Editorial and personal audio collections.",
};

export default function PlaylistsPage() {
  return <PlaylistsPageContent />;
}
