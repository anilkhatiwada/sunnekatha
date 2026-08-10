import type { Metadata } from "next";

import { AuthorsPageContent } from "@/features/authors/authors-page";

export const metadata: Metadata = {
  title: "लेखकहरू",
  description: "SunneKatha मा उपलब्ध नेपाली लेखक र साहित्यकारहरू।",
};

export default function AuthorsPage() {
  return <AuthorsPageContent />;
}
