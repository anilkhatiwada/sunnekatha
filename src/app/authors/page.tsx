import type { Metadata } from "next";

import { AuthorsPageContent } from "@/features/authors/authors-page";

export const metadata: Metadata = {
  title: "Authors",
  description: "Discover Nepali authors and writers on SunneKatha.",
};

export default function AuthorsPage() {
  return <AuthorsPageContent />;
}
