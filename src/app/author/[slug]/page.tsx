import type { Metadata } from "next";

import { AuthorDetailPageContent } from "@/features/author/author-detail-page";

export const metadata: Metadata = {
  title: "लेखक",
  description: "SunneKatha का नेपाली लेखक र उनीहरूका श्रव्य रचना।",
};

interface AuthorPageProps {
  params: Promise<{ slug: string }>;
}

export default async function AuthorPage({ params }: AuthorPageProps) {
  const { slug } = await params;

  return <AuthorDetailPageContent slug={slug} />;
}
