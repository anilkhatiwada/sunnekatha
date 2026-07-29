import type { Metadata } from "next";

import { TrackDetailPageContent } from "@/features/track/track-detail-page";

export const metadata: Metadata = {
  title: "रचना",
  description: "SunneKatha मा नेपाली श्रव्य साहित्य सुन्नुहोस्।",
};

interface TrackPageProps {
  params: Promise<{ slug: string }>;
}

export default async function TrackPage({ params }: TrackPageProps) {
  const { slug } = await params;

  return <TrackDetailPageContent slug={slug} />;
}
