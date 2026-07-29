import type { Metadata } from "next";

import { NarratorDetailPageContent } from "@/features/narrator/narrator-detail-page";

export const metadata: Metadata = {
  title: "वाचक",
  description: "SunneKatha का वाचक र उनीहरूको स्वरमा उपलब्ध नेपाली साहित्य।",
};

interface NarratorPageProps {
  params: Promise<{ slug: string }>;
}

export default async function NarratorPage({ params }: NarratorPageProps) {
  const { slug } = await params;

  return <NarratorDetailPageContent slug={slug} />;
}
