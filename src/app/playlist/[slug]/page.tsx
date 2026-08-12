import type { Metadata } from "next";

import { PlaylistDetailPageContent } from "@/features/playlist/playlist-detail-page";

export const metadata: Metadata = {
  title: "Playlist",
  description: "Listen to a literary playlist on SunneKatha.",
};

interface PlaylistPageProps {
  params: Promise<{ slug: string }>;
}

export default async function PlaylistPage({ params }: PlaylistPageProps) {
  const { slug } = await params;

  return <PlaylistDetailPageContent slug={slug} />;
}
