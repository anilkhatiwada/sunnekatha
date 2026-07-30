import type { Metadata } from "next";

import { TaxonomyDetailPage } from "@/features/catalog/taxonomy-detail-page";

export const metadata: Metadata = { title: "विधा" };

export default async function GenrePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <TaxonomyDetailPage kind="genre" slug={slug} />;
}
