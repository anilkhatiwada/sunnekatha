import type { Metadata } from "next";

import { NarratorDetailPageContent } from "@/features/narrator/narrator-detail-page";

export const metadata: Metadata = {
  title: "Narrator",
  description: "Discover Nepali literature through SunneKatha narrators.",
};

interface NarratorPageProps {
  params: Promise<{ slug: string }>;
}

export default async function NarratorPage({ params }: NarratorPageProps) {
  const { slug } = await params;

  return <NarratorDetailPageContent slug={slug} />;
}
