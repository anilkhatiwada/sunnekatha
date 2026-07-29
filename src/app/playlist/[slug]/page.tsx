import type { Metadata } from "next";

import { PlaylistDetailPageContent } from "@/features/playlist/playlist-detail-page";

export const metadata: Metadata = {
  title: "प्लेलिस्ट",
  description: "SunneKatha को साहित्यिक प्लेलिस्ट सुन्नुहोस्।",
};

interface PlaylistPageProps {
  params: Promise<{ slug: string }>;
}

export default async function PlaylistPage({ params }: PlaylistPageProps) {
  const { slug } = await params;

  return <PlaylistDetailPageContent slug={slug} />;
}
