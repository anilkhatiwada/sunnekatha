import type { Metadata } from "next";

import { CatalogDetailPage } from "@/features/catalog/catalog-detail-page";

export const metadata: Metadata = { title: "साहित्यिक कृति" };

export default async function WorkPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <CatalogDetailPage kind="work" slug={slug} />;
}
