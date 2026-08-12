import type { Metadata } from "next";

import { AuthorDetailPageContent } from "@/features/author/author-detail-page";

export const metadata: Metadata = {
  title: "Author",
  description: "Discover Nepali authors and their audio works on SunneKatha.",
};

interface AuthorPageProps {
  params: Promise<{ slug: string }>;
}

export default async function AuthorPage({ params }: AuthorPageProps) {
  const { slug } = await params;

  return <AuthorDetailPageContent slug={slug} />;
}
