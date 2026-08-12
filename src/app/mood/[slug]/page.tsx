import type { Metadata } from "next";

import { TaxonomyDetailPage } from "@/features/catalog/taxonomy-detail-page";

export const metadata: Metadata = { title: "Mood" };

export default async function MoodPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <TaxonomyDetailPage kind="mood" slug={slug} />;
}
