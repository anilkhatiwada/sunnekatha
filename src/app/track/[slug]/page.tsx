import type { Metadata } from "next";

import { TrackDetailPageContent } from "@/features/track/track-detail-page";
import { buildTrackMetadata, getSocialTrack } from "@/lib/social-metadata";

interface TrackPageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({
  params,
}: TrackPageProps): Promise<Metadata> {
  const { slug } = await params;
  return buildTrackMetadata(slug, await getSocialTrack(slug));
}

export default async function TrackPage({ params }: TrackPageProps) {
  const { slug } = await params;

  return <TrackDetailPageContent slug={slug} />;
}
