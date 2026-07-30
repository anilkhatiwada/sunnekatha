import type { Metadata } from "next";

import { CatalogDetailPage } from "@/features/catalog/catalog-detail-page";

export const metadata: Metadata = { title: "एल्बम" };

export default async function AlbumPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <CatalogDetailPage kind="album" slug={slug} />;
}
